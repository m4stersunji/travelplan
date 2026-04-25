# Phase 1 — Reliability & Self-Healing

**Date:** 2026-04-25
**Status:** Approved, ready for implementation

## Goal

Make the flight tracker resilient when the user's PC is off and the system runs entirely from GitHub Actions. Detect failures, retry transients, and alert when something is genuinely broken.

## Scope

Five reliability features, all built into a single new module `src/health.py`:

1. Auto-retry on transient scraper errors
2. Inline sanity checks on parsed flight data
3. Heartbeat alerts on consecutive scrape failures
4. LINE quota tracking with soft-block on scheduled sends
5. (GitHub Actions cost — *out of scope*: public repo gives unlimited minutes)

## Non-Goals

- Schema regression as a separate cron job (covered by inline sanity checks)
- Hard-block on LINE quota (preserves emergency price alerts)
- Per-feature module split (single `health.py` is the right size)

## Architecture

### Module layout

```
src/health.py        [NEW] — retry, sanity, heartbeat, quota, alerts (~250 lines)
src/scraper.py       [edit] — wrap _scrape_route with @with_retry, call validate_flights
src/main.py          [edit] — call detect_failed_routes after run, check_line_quota before sends
src/database.py      [edit] — add alert_events table + helpers
tests/test_health.py [NEW] — unit + integration tests
```

### Data model

One new table for **alert dedupe** (one alert per condition per 6h window):

```sql
CREATE TABLE alert_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type  TEXT NOT NULL,    -- 'heartbeat' | 'sanity' | 'quota'
    route       TEXT,
    message     TEXT,
    sent_at     DATETIME NOT NULL
);
CREATE INDEX idx_alert_events_type_time ON alert_events(alert_type, sent_at);
```

No changes to `scrape_runs` or `flights` tables.

## Feature Designs

### 1. Auto-retry decorator

```python
@with_retry(retries=2, backoff=30)
def _scrape_route(origin, dest, date, ...):
    ...
```

**Triggers retry on:**
- `TimeoutException`, `ConnectionError`, `WebDriverException`
- `EmptyResultsError` raised when 0 flights parsed
- `BlockedError` raised when CAPTCHA / "unusual traffic" detected

**Behavior:**
- Wait 30s before each retry
- Rotate user-agent on retry (uses existing `USER_AGENTS` list in scraper.py)
- Total 3 attempts maximum (1 initial + 2 retries)
- Logs each retry attempt with reason

### 2. Inline sanity checks

After `_parse_flights` returns its list:

```python
def validate_flights(flights):
    valid = [f for f in flights
             if f.get('price_thb', 0) > 0
             and f.get('airline')
             and f.get('departure_time')]
    ratio = len(valid) / max(len(flights), 1)
    if ratio < 0.5:
        raise SanityCheckError(
            f"Only {len(valid)}/{len(flights)} flights passed validation "
            f"(price/airline/time)")
    return valid
```

If `SanityCheckError` raises, `@with_retry` catches it as a retry-worthy error. After all retries exhausted, scrape is marked `status='error'` and counts toward heartbeat detection.

### 3. Heartbeat detection

Called once at the end of `main()` after all routes scraped:

```python
failed_routes = detect_failed_routes(db_path, consecutive=3)
if failed_routes and not recently_alerted('heartbeat', within_hours=6):
    send_alert('heartbeat', message=f"⚠️ Scraper down: {', '.join(failed_routes)}\n"
                                    f"3 consecutive failures. Check logs.")
```

**SQL query for failed routes:**

```sql
WITH recent_runs AS (
    SELECT route, status,
           ROW_NUMBER() OVER (PARTITION BY route ORDER BY scraped_at DESC) AS rn
    FROM scrape_runs
)
SELECT route FROM recent_runs WHERE rn <= 3
GROUP BY route
HAVING COUNT(*) = 3 AND SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) = 3;
```

Alerts are plain text via `send_line_notification()` (not flex) — small payload, fewer chars consumed against quota.

### 4. LINE quota tracker

Called before each LINE send in `main.py`:

```python
def check_line_quota():
    """Returns (used, limit, pct). Caches for 1 hour to avoid extra API calls."""
    quota_resp = requests.get('https://api.line.me/v2/bot/message/quota',
                              headers={'Authorization': f'Bearer {TOKEN}'})
    used_resp = requests.get('https://api.line.me/v2/bot/message/quota/consumption',
                             headers={'Authorization': f'Bearer {TOKEN}'})
    limit = quota_resp.json().get('value', 500)  # 500 free tier default
    used = used_resp.json().get('totalUsage', 0)
    return used, limit, (used / limit * 100) if limit else 0
```

**Soft-block logic:**

```python
used, limit, pct = check_line_quota()
if pct >= 90 and not is_price_alert:
    logger.info(f"LINE quota at {pct:.0f}% ({used}/{limit}) — skipping scheduled send")
    return
# proceed with send
```

Quota usage also pushed to Google Sheets Overview tab so user can see it without inspecting logs.

### 5. Out of scope

GitHub Actions minute monitoring — public repo has unlimited minutes per GitHub docs. No tracking needed.

## Error handling

- Alert messages are **plain text** (cheaper than flex)
- Alert dedupe via `alert_events` table — query before inserting
- If alert send itself fails → log error and drop (no recursive retry)
- LINE quota check failures → log warning, allow the send (fail-open: don't block real alerts on a quota check error)

## Testing

`tests/test_health.py`:

- **Unit:** `with_retry` retries N times then raises, succeeds on 2nd attempt
- **Unit:** `validate_flights` accepts good data, rejects when <50% valid
- **Unit:** `check_line_quota` parses LINE API responses correctly (mocked)
- **Integration:** seed 3 failed scrape_runs in test DB, assert `detect_failed_routes` returns the route
- **Integration:** call `send_alert` twice in succession, second is suppressed by dedupe

All existing tests must still pass (currently 27).

## Rollout

Single commit/PR. No feature flag — additive behavior, doesn't change existing happy path. If retry adds latency, scrape duration may increase by ~30s in worst case (one retry × one route).

## Future work (not Phase 1)

- Anomaly detection on prices (sudden 10x changes)
- Per-route success rate dashboard
- Smart retry budget (cap total retries per run to avoid runaway latency)
