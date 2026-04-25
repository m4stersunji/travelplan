"""Tests for src/health.py — Phase 1 reliability features."""
import os
import sys
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from health import (
    with_retry,
    validate_flights,
    detect_failed_routes,
    check_line_quota,
    should_skip_for_quota,
    send_alert,
    run_heartbeat_check,
    EmptyResultsError,
    BlockedError,
    SanityCheckError,
)
from database import init_db, insert_scrape_run, insert_alert_event, recently_alerted


def make_temp_db():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    init_db(path)
    return path


# ---------- with_retry ----------

def test_with_retry_succeeds_first_try():
    @with_retry(retries=2, backoff=0)
    def ok():
        return "fine"
    assert ok() == "fine"


def test_with_retry_succeeds_after_one_failure():
    calls = {'n': 0}

    @with_retry(retries=2, backoff=0)
    def flaky():
        calls['n'] += 1
        if calls['n'] < 2:
            raise EmptyResultsError("nothing yet")
        return "ok"

    assert flaky() == "ok"
    assert calls['n'] == 2


def test_with_retry_exhausts_and_raises():
    calls = {'n': 0}

    @with_retry(retries=2, backoff=0)
    def always_fails():
        calls['n'] += 1
        raise BlockedError("captcha")

    with pytest.raises(BlockedError):
        always_fails()
    assert calls['n'] == 3  # 1 initial + 2 retries


def test_with_retry_does_not_catch_unrelated_exceptions():
    @with_retry(retries=2, backoff=0)
    def bug():
        raise ValueError("real bug, not transient")

    with pytest.raises(ValueError):
        bug()


# ---------- validate_flights ----------

def test_validate_flights_empty_raises():
    with pytest.raises(EmptyResultsError):
        validate_flights([])


def test_validate_flights_all_good_passes():
    flights = [
        {'price_thb': 5000, 'airline': 'AirAsia', 'departure_time': '08:00'},
        {'price_thb': 4000, 'airline': 'Thai Smile', 'departure_time': '10:00'},
    ]
    assert validate_flights(flights) == flights


def test_validate_flights_too_many_invalid_raises():
    # 3 of 4 are invalid (75% bad > 50% threshold)
    flights = [
        {'price_thb': 0, 'airline': 'X', 'departure_time': '08:00'},
        {'price_thb': 1000, 'airline': '', 'departure_time': '09:00'},
        {'price_thb': 1000, 'airline': 'Y', 'departure_time': ''},
        {'price_thb': 5000, 'airline': 'Z', 'departure_time': '12:00'},
    ]
    with pytest.raises(SanityCheckError):
        validate_flights(flights)


def test_validate_flights_just_over_threshold_passes():
    # 2 of 3 valid (66% >= 50%)
    flights = [
        {'price_thb': 0, 'airline': 'X', 'departure_time': '08:00'},
        {'price_thb': 1000, 'airline': 'Y', 'departure_time': '10:00'},
        {'price_thb': 2000, 'airline': 'Z', 'departure_time': '12:00'},
    ]
    assert validate_flights(flights) == flights


# ---------- detect_failed_routes ----------

def test_detect_failed_routes_returns_route_after_three_errors():
    db = make_temp_db()
    try:
        for _ in range(3):
            insert_scrape_run(db, route='BKK-DAD', search_date='2026-05-29', status='error')
        failed = detect_failed_routes(db, consecutive=3)
        assert 'BKK-DAD' in failed
    finally:
        os.unlink(db)


def test_detect_failed_routes_ignores_one_recent_success():
    db = make_temp_db()
    try:
        for _ in range(3):
            insert_scrape_run(db, route='BKK-DAD', search_date='2026-05-29', status='error')
        # one success is enough to break the streak
        insert_scrape_run(db, route='BKK-DAD', search_date='2026-05-29', status='success')
        failed = detect_failed_routes(db, consecutive=3)
        assert 'BKK-DAD' not in failed
    finally:
        os.unlink(db)


def test_detect_failed_routes_handles_multiple_routes():
    db = make_temp_db()
    try:
        for _ in range(3):
            insert_scrape_run(db, route='BKK-DAD', search_date='2026-05-29', status='error')
            insert_scrape_run(db, route='DAD-BKK', search_date='2026-06-01', status='success')
        failed = detect_failed_routes(db, consecutive=3)
        assert failed == ['BKK-DAD']
    finally:
        os.unlink(db)


# ---------- check_line_quota ----------

def test_check_line_quota_parses_responses():
    quota_resp = MagicMock()
    quota_resp.json.return_value = {'value': 500}
    used_resp = MagicMock()
    used_resp.json.return_value = {'totalUsage': 250}

    with patch('health.LINE_CHANNEL_ACCESS_TOKEN', 'fake_token'), \
         patch('health.requests.get', side_effect=[quota_resp, used_resp]):
        used, limit, pct = check_line_quota()
        assert used == 250
        assert limit == 500
        assert pct == 50.0


def test_check_line_quota_fail_open_on_exception():
    with patch('health.LINE_CHANNEL_ACCESS_TOKEN', 'fake_token'), \
         patch('health.requests.get', side_effect=ConnectionError("net down")):
        used, limit, pct = check_line_quota()
        assert pct == 0


def test_should_skip_for_quota_blocks_scheduled_at_high_pct():
    quota_resp = MagicMock()
    quota_resp.json.return_value = {'value': 500}
    used_resp = MagicMock()
    used_resp.json.return_value = {'totalUsage': 460}  # 92%

    with patch('health.LINE_CHANNEL_ACCESS_TOKEN', 'fake_token'), \
         patch('health.requests.get', side_effect=[quota_resp, used_resp]):
        assert should_skip_for_quota(is_price_alert=False) is True


def test_should_skip_for_quota_allows_price_alert_at_high_pct():
    # price alerts must always go through, even at high quota
    assert should_skip_for_quota(is_price_alert=True) is False


def test_should_skip_for_quota_allows_scheduled_at_low_pct():
    quota_resp = MagicMock()
    quota_resp.json.return_value = {'value': 500}
    used_resp = MagicMock()
    used_resp.json.return_value = {'totalUsage': 100}  # 20%

    with patch('health.LINE_CHANNEL_ACCESS_TOKEN', 'fake_token'), \
         patch('health.requests.get', side_effect=[quota_resp, used_resp]):
        assert should_skip_for_quota(is_price_alert=False) is False


# ---------- send_alert dedupe ----------

def test_send_alert_dedupes_within_window():
    db = make_temp_db()
    try:
        # First alert: succeeds (mock LINE send)
        with patch('notifier.send_line_notification', return_value=True):
            sent1 = send_alert(db, 'heartbeat', 'first message', dedupe_hours=6)
            assert sent1 is True

        # Second alert: should be deduped, LINE NOT called
        with patch('notifier.send_line_notification', return_value=True) as mock_send:
            sent2 = send_alert(db, 'heartbeat', 'second message', dedupe_hours=6)
            assert sent2 is False
            mock_send.assert_not_called()
    finally:
        os.unlink(db)


def test_send_alert_different_types_independent():
    db = make_temp_db()
    try:
        with patch('notifier.send_line_notification', return_value=True) as mock_send:
            sent1 = send_alert(db, 'heartbeat', 'msg', dedupe_hours=6)
            sent2 = send_alert(db, 'sanity', 'msg', dedupe_hours=6)
            assert sent1 is True
            assert sent2 is True
            assert mock_send.call_count == 2
    finally:
        os.unlink(db)


# ---------- run_heartbeat_check ----------

def test_run_heartbeat_check_alerts_on_three_failures():
    db = make_temp_db()
    try:
        for _ in range(3):
            insert_scrape_run(db, route='BKK-DAD', search_date='2026-05-29', status='error')

        with patch('notifier.send_line_notification', return_value=True) as mock_send:
            sent = run_heartbeat_check(db, consecutive=3)
            assert sent is True
            mock_send.assert_called_once()
            # Verify message mentions the failed route
            args = mock_send.call_args[0][0]
            assert 'BKK-DAD' in args
    finally:
        os.unlink(db)


def test_run_heartbeat_check_silent_when_healthy():
    db = make_temp_db()
    try:
        insert_scrape_run(db, route='BKK-DAD', search_date='2026-05-29', status='success')

        with patch('notifier.send_line_notification', return_value=True) as mock_send:
            sent = run_heartbeat_check(db, consecutive=3)
            assert sent is False
            mock_send.assert_not_called()
    finally:
        os.unlink(db)
