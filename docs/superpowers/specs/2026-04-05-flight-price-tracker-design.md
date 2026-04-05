# Flight Price Tracker — Design Spec

## Overview

A Python-based flight price tracker that scrapes Google Flights every 4 hours, stores results in SQLite, sends LINE notifications, and exports to CSV. Dashboard deferred to Phase 2.

## Phases

- **Phase 1 (now):** Scraper + SQLite + LINE notifications + CSV export
- **Phase 2 (later):** Flask web dashboard with charts, heatmaps, aircraft info

---

## Trips to Track

### Trip 1: Danang (build first)

| Route | Date Option 1 | Date Option 2 |
|-------|---------------|---------------|
| BKK → DAD | 29 May 2026 | 30 May 2026 |
| DAD → BKK | 1 Jun 2026 | 2 Jun 2026 |

### Trip 2: Osaka/Tokyo (add later)

| Route | Date |
|-------|------|
| BKK → KIX | 18 Oct 2026 |
| NRT or HND → BKK | 25 Oct 2026 |

---

## Architecture

```
System Cron (every 4 hrs)
       │
       ▼
Flight Scraper (Python + Selenium + Chrome headless)
       │
       ├──► SQLite DB (price history, flight details)
       ├──► CSV Export (per run)
       └──► LINE Messaging API (alert notification)
```

## Component Details

### 1. Flight Scraper

**Tech:** Python 3 + Selenium + Chrome headless on WSL2

**Per search, captures:**

| Field | Example |
|-------|---------|
| airline | Thai AirAsia |
| flight_number | FD636 |
| departure_time | 10:15 |
| arrival_time | 12:15 |
| duration_minutes | 120 |
| price_thb | 3250 |
| aircraft_type | A320 |
| num_stops | 0 |
| is_direct | true/false |
| is_excluded_airline | true/false |
| is_preferred_time | true/false |

**Search matrix (Danang):** 4 one-way searches per run (2 outbound dates x 2 return dates).

**Excluded airline flag:** Emirates, Qatar Airways, Etihad, Oman Air, Saudia, Gulf Air, flynas, Air Arabia. These are NOT removed — they are flagged with `is_excluded_airline = true` and shown separately in notifications.

**Preferred time flag:** Outbound BKK→DAD flights departing 09:00-12:00 are flagged `is_preferred_time = true` (targeting ~1pm arrival in Danang).

**Error handling:**
- Page load failure → log error, skip run, retry next cycle
- No results found → log it, no LINE notification sent
- CAPTCHA/block → log warning, skip run

### 2. Database (SQLite)

```sql
scrape_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scraped_at  DATETIME NOT NULL,
    route       TEXT NOT NULL,        -- 'BKK-DAD' or 'DAD-BKK'
    search_date TEXT NOT NULL,        -- '2026-05-29'
    status      TEXT NOT NULL         -- 'success' / 'error'
)

flights (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    scrape_run_id       INTEGER NOT NULL REFERENCES scrape_runs(id),
    airline             TEXT,
    flight_number       TEXT,
    departure_time      TEXT,
    arrival_time        TEXT,
    duration_minutes    INTEGER,
    price_thb           INTEGER,
    aircraft_type       TEXT,
    num_stops           INTEGER,
    is_direct           BOOLEAN,
    is_excluded_airline BOOLEAN,
    is_preferred_time   BOOLEAN
)

price_alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scrape_run_id   INTEGER NOT NULL REFERENCES scrape_runs(id),
    route           TEXT NOT NULL,
    search_date     TEXT NOT NULL,
    best_price_thb  INTEGER,
    prev_price_thb  INTEGER,
    is_lowest_ever  BOOLEAN,
    alerted_at      DATETIME
)
```

### 3. LINE Notification

**API:** LINE Messaging API (free tier — 200 messages/month)

**Setup required:** User needs to create a LINE Messaging API channel and get a Channel Access Token.

**Message format:**

```
✈️ Flight Price Update — BKK→DAD 29 May

🏆 Best Deal: Thai AirAsia | FD636
   ฿3,250 (▼ -350 from last check)
   ⭐ LOWEST EVER
   Depart 10:15 → Arrive 12:15
   Aircraft: A320

📊 Other Direct Flights:
   VietJet VZ962 | ฿3,800 (▲ +200) | 09:00→11:00 | A321
   Nok Air DD930 | ฿4,100 (— same) | 11:30→13:30 | 737-800

📌 With Stops / Excluded Airlines (FYI):
   Emirates EK374 | ฿2,900 (1 stop) | 08:00→16:30 | 777

🕐 Checked: 2026-04-05 14:00
📈 Tracking since: 2026-04-01 (45 checks)
```

**Logic:**
- Lead with cheapest direct, non-excluded airline
- Show price change (▲▼—) and lowest-ever flag per flight
- Group: direct flights first, then stops/excluded as FYI
- Include check timestamp and tracking history count

### 4. CSV Export

- One CSV file per route: `data/BKK-DAD-2026-05-29.csv`, etc.
- Appended after each scrape run
- Contains all columns from `flights` table + `scraped_at`

---

## Project Structure

```
travelplan/
├── src/
│   ├── scraper.py          # Selenium Google Flights scraper
│   ├── database.py         # SQLite setup, queries, inserts
│   ├── notifier.py         # LINE Messaging API integration
│   ├── exporter.py         # CSV export logic
│   ├── main.py             # Orchestrator: scrape → store → notify → export
│   └── config.py           # Routes, dates, thresholds, LINE token
├── data/                   # CSV exports + SQLite DB file
├── logs/                   # Scraper logs
├── requirements.txt        # selenium, requests, etc.
├── setup_cron.sh           # Installs cron job
└── docs/
    └── superpowers/specs/  # This spec
```

---

## Cron Setup

```bash
# Every 4 hours
0 */4 * * * cd /home/m4stersun/travelplan && /usr/bin/python3 src/main.py >> logs/scraper.log 2>&1
```

---

## Dependencies

- Python 3.10+
- selenium
- requests (for LINE API)
- sqlite3 (stdlib)
- Chrome + chromedriver (headless)

All free. No paid APIs.

---

## Phase 2 (deferred): Web Dashboard

- Flask + Chart.js
- Price trend charts, airline comparison table
- Calendar heatmap for cheapest dates
- Aircraft info panel (size, pros/cons)
- Sortable/filterable flight table
- Price alert history log
- Served on `localhost:5000`

---

## Open Items

- LINE Messaging API channel setup (user needs to create this)
- Exact Google Flights URL structure may change — scraper needs to handle gracefully
- Chrome/chromedriver installation on WSL2
