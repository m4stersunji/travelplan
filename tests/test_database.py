import sys
import os
import sqlite3
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import init_db, insert_scrape_run, insert_flight, get_previous_best_price, get_lowest_ever_price, get_recent_flights


def make_temp_db():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    return path


def test_init_db_creates_tables():
    db_path = make_temp_db()
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert 'scrape_runs' in tables
        assert 'flights' in tables
        assert 'price_alerts' in tables
    finally:
        os.unlink(db_path)


def test_insert_scrape_run_returns_id():
    db_path = make_temp_db()
    try:
        init_db(db_path)
        run_id = insert_scrape_run(db_path, route='BKK-DAD', search_date='2026-05-29', status='success')
        assert run_id == 1
        run_id2 = insert_scrape_run(db_path, route='BKK-DAD', search_date='2026-05-29', status='success')
        assert run_id2 == 2
    finally:
        os.unlink(db_path)


def test_insert_flight_and_query():
    db_path = make_temp_db()
    try:
        init_db(db_path)
        run_id = insert_scrape_run(db_path, route='BKK-DAD', search_date='2026-05-29', status='success')
        insert_flight(db_path, scrape_run_id=run_id, airline='Thai AirAsia', flight_number='',
                      departure_airport='DMK', departure_time='07:50',
                      arrival_airport='DAD', arrival_time='09:30',
                      duration_minutes=100, price_thb=3370, aircraft_type='A320', num_stops=0,
                      is_direct=True, is_excluded_airline=False)
        flights = get_recent_flights(db_path, route='BKK-DAD', search_date='2026-05-29', limit=10)
        assert len(flights) == 1
        assert flights[0]['airline'] == 'Thai AirAsia'
        assert flights[0]['price_thb'] == 3370
    finally:
        os.unlink(db_path)


def test_get_previous_best_price_no_history():
    db_path = make_temp_db()
    try:
        init_db(db_path)
        price = get_previous_best_price(db_path, route='BKK-DAD', search_date='2026-05-29')
        assert price is None
    finally:
        os.unlink(db_path)


def test_recently_alerted_returns_false_for_expired_iso_T_entry():
    """Regression: insert_alert_event stores sent_at via datetime.isoformat() (with 'T'),
    but SQLite's datetime('now', '-Nh') uses a space separator. A naive string compare
    treats same-day 'T' entries as newer than space-separated thresholds (T > space in
    ASCII), so 8h-old entries falsely look 'within 6h' until UTC midnight rolls over.
    Reproduces the prod silence on 2026-05-02 after the elapsed-time gate shipped."""
    from datetime import datetime, timedelta, timezone
    from database import recently_alerted
    db_path = make_temp_db()
    try:
        init_db(db_path)
        eight_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat()
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO alert_events (alert_type, sent_at) VALUES (?, ?)",
                ('scheduled_flex', eight_hours_ago),
            )
        assert recently_alerted(db_path, 'scheduled_flex', within_hours=6) is False
    finally:
        os.unlink(db_path)


def test_get_lowest_ever_price():
    db_path = make_temp_db()
    try:
        init_db(db_path)
        run1 = insert_scrape_run(db_path, route='BKK-DAD', search_date='2026-05-29', status='success')
        insert_flight(db_path, scrape_run_id=run1, airline='AirAsia', flight_number='',
                      departure_airport='DMK', departure_time='07:50',
                      arrival_airport='DAD', arrival_time='09:30',
                      duration_minutes=100, price_thb=4000, aircraft_type='A320', num_stops=0,
                      is_direct=True, is_excluded_airline=False)
        run2 = insert_scrape_run(db_path, route='BKK-DAD', search_date='2026-05-29', status='success')
        insert_flight(db_path, scrape_run_id=run2, airline='AirAsia', flight_number='',
                      departure_airport='DMK', departure_time='07:50',
                      arrival_airport='DAD', arrival_time='09:30',
                      duration_minutes=100, price_thb=3500, aircraft_type='A320', num_stops=0,
                      is_direct=True, is_excluded_airline=False)
        lowest = get_lowest_ever_price(db_path, route='BKK-DAD', search_date='2026-05-29')
        assert lowest == 3500
    finally:
        os.unlink(db_path)
