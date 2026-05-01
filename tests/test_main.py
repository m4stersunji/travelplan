import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import patch
from main import process_route


def test_process_route_with_mock_scraper():
    mock_flights = [
        {
            'airline': 'Thai AirAsia', 'flight_number': '',
            'departure_airport': 'DMK', 'departure_time': '07:50',
            'arrival_airport': 'DAD', 'arrival_time': '09:30',
            'duration_minutes': 100, 'price_thb': 3370,
            'aircraft_type': 'A320', 'num_stops': 0,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        data_dir = tmpdir

        with patch('main.scrape_flights', return_value=mock_flights):
            from database import init_db
            init_db(db_path)

            result = process_route(
                origin='Bangkok', destination='Danang', date='2026-05-29',
                label='BKK-DAD-May29', route_code='BKK-DAD',
                db_path=db_path, data_dir=data_dir
            )

            assert result['success'] is True
            assert len(result['flights']) == 1
            assert result['route'] == 'BKK-DAD'


def test_process_route_scraper_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        data_dir = tmpdir

        with patch('main.scrape_flights', return_value=[]):
            from database import init_db
            init_db(db_path)

            result = process_route(
                origin='Bangkok', destination='Danang', date='2026-05-29',
                label='BKK-DAD-May29', route_code='BKK-DAD',
                db_path=db_path, data_dir=data_dir
            )

            assert result['success'] is False


def _stub_results():
    return [{
        'success': True,
        'flights': [],
        'route_code': 'BKK-KIX',
        'search_date': '2026-10-17',
        'date_label': '17 Oct',
        'score_mode': 'departure',
    }]


def test_should_send_when_no_prior_notification():
    """Fresh DB: scheduled-flex throttle empty → should send."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        from database import init_db
        init_db(db_path)

        from main import _should_send_notification
        should_send, is_alert = _should_send_notification(_stub_results(), [], db_path)
        assert should_send is True
        assert is_alert is False


def test_should_skip_if_recently_notified():
    """Scheduled flex sent within window → skip regardless of clock hour."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        from database import init_db, insert_alert_event
        init_db(db_path)
        insert_alert_event(db_path, 'scheduled_flex', message='prior')

        from main import _should_send_notification
        should_send, is_alert = _should_send_notification(_stub_results(), [], db_path)
        assert should_send is False
        assert is_alert is False


def test_should_send_after_window_elapsed():
    """Last scheduled flex older than NOTIFY_EVERY_HOURS → send again."""
    import sqlite3
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        from database import init_db
        init_db(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO alert_events (alert_type, sent_at) "
                "VALUES (?, datetime('now', '-12 hours'))",
                ('scheduled_flex',),
            )

        from main import _should_send_notification
        should_send, is_alert = _should_send_notification(_stub_results(), [], db_path)
        assert should_send is True
        assert is_alert is False
