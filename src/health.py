"""Reliability and self-healing for the flight tracker.

Owns: retry decorator, inline sanity checks, heartbeat detection, LINE quota tracker.
See docs/superpowers/specs/2026-04-25-phase-1-reliability-design.md
"""
import functools
import logging
import time

import requests

from config import LINE_CHANNEL_ACCESS_TOKEN
from database import get_consecutive_failures, insert_alert_event, recently_alerted

logger = logging.getLogger(__name__)


class EmptyResultsError(Exception):
    """Scraper returned 0 flights — likely transient or block."""


class BlockedError(Exception):
    """Google served CAPTCHA / consent / unusual-traffic page."""


class SanityCheckError(Exception):
    """Parsed flight data failed validation (>50% bad rows)."""


RETRYABLE_EXCEPTIONS = (EmptyResultsError, BlockedError, SanityCheckError)


def with_retry(retries=2, backoff=30):
    """Decorator: retries on transient/empty/block errors with linear backoff.

    Total attempts = 1 + retries. Logs each retry with reason.
    Also retries selenium TimeoutException / WebDriverException if available.
    """
    selenium_retryable = ()
    try:
        from selenium.common.exceptions import TimeoutException, WebDriverException
        selenium_retryable = (TimeoutException, WebDriverException)
    except ImportError:
        pass

    retryable = RETRYABLE_EXCEPTIONS + selenium_retryable + (ConnectionError, TimeoutError)

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(retries + 1):
                try:
                    return fn(*args, **kwargs)
                except retryable as exc:
                    last_exc = exc
                    if attempt < retries:
                        logger.warning(
                            f"{fn.__name__} attempt {attempt+1}/{retries+1} failed: "
                            f"{type(exc).__name__}: {exc}. Retrying in {backoff}s..."
                        )
                        time.sleep(backoff)
                    else:
                        logger.error(
                            f"{fn.__name__} failed after {retries+1} attempts: "
                            f"{type(exc).__name__}: {exc}"
                        )
            raise last_exc
        return wrapper
    return decorator


def validate_flights(flights):
    """Sanity check: at least 50% of rows must have valid price/airline/time.

    Raises SanityCheckError if Google's response shape has drifted.
    Returns the original list unchanged if valid.
    """
    if not flights:
        raise EmptyResultsError("0 flights parsed")

    valid = [
        f for f in flights
        if f.get('price_thb', 0) > 0
        and f.get('airline')
        and f.get('departure_time')
    ]
    ratio = len(valid) / len(flights)
    if ratio < 0.5:
        raise SanityCheckError(
            f"Only {len(valid)}/{len(flights)} flights passed validation "
            f"(price>0, airline, departure_time)"
        )
    return flights


def detect_failed_routes(db_path, consecutive=3):
    """Return list of routes whose last `consecutive` runs all failed."""
    return get_consecutive_failures(db_path, consecutive=consecutive)


def check_line_quota():
    """Returns (used, limit, pct). Fail-open: returns (0, 500, 0) on API error."""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        return 0, 500, 0
    headers = {'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
    try:
        q = requests.get('https://api.line.me/v2/bot/message/quota',
                         headers=headers, timeout=5).json()
        u = requests.get('https://api.line.me/v2/bot/message/quota/consumption',
                         headers=headers, timeout=5).json()
        limit = q.get('value') or 500
        used = u.get('totalUsage', 0)
        pct = (used / limit * 100) if limit else 0
        return used, limit, pct
    except Exception as exc:
        logger.warning(f"LINE quota check failed: {exc} — proceeding fail-open")
        return 0, 500, 0


def should_skip_for_quota(is_price_alert, threshold_pct=90):
    """True if scheduled (non-emergency) send should be skipped due to quota."""
    if is_price_alert:
        return False
    used, limit, pct = check_line_quota()
    if pct >= threshold_pct:
        logger.info(f"LINE quota at {pct:.0f}% ({used}/{limit}) — skipping scheduled send")
        return True
    return False


def send_alert(db_path, alert_type, message, dedupe_hours=6):
    """Send a plain-text LINE alert with dedupe.

    Skips if the same alert_type was sent within `dedupe_hours`.
    Records in alert_events on success.
    """
    if recently_alerted(db_path, alert_type, within_hours=dedupe_hours):
        logger.info(f"Skipping {alert_type} alert (sent within {dedupe_hours}h)")
        return False

    from notifier import send_line_notification
    sent = send_line_notification(message)
    if sent:
        insert_alert_event(db_path, alert_type, message=message)
        logger.info(f"Alert sent: {alert_type}")
        return True
    logger.error(f"Alert send failed: {alert_type}")
    return False


def run_heartbeat_check(db_path, consecutive=3):
    """Detect failed routes; send alert if any AND not recently alerted."""
    failed = detect_failed_routes(db_path, consecutive=consecutive)
    if not failed:
        return False
    msg = (
        f"⚠️ Scraper down: {', '.join(failed)}\n"
        f"{consecutive} consecutive failures. Check logs."
    )
    return send_alert(db_path, 'heartbeat', msg)
