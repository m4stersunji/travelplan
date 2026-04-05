import sqlite3
from datetime import datetime


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path):
    with _connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                scraped_at  DATETIME NOT NULL,
                route       TEXT NOT NULL,
                search_date TEXT NOT NULL,
                status      TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS flights (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                scrape_run_id       INTEGER NOT NULL REFERENCES scrape_runs(id),
                airline             TEXT,
                flight_number       TEXT,
                departure_airport   TEXT,
                departure_time      TEXT,
                arrival_airport     TEXT,
                arrival_time        TEXT,
                duration_minutes    INTEGER,
                price_thb           INTEGER,
                aircraft_type       TEXT,
                num_stops           INTEGER,
                is_direct           BOOLEAN,
                is_excluded_airline BOOLEAN,
                best_booking_price  INTEGER,
                best_booking_source TEXT,
                cabin_baggage       TEXT,
                checked_baggage     TEXT,
                service_type        TEXT
            );
            CREATE TABLE IF NOT EXISTS price_alerts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                scrape_run_id   INTEGER NOT NULL REFERENCES scrape_runs(id),
                route           TEXT NOT NULL,
                search_date     TEXT NOT NULL,
                best_price_thb  INTEGER,
                prev_price_thb  INTEGER,
                is_lowest_ever  BOOLEAN,
                alerted_at      DATETIME
            );
        """)


def insert_scrape_run(db_path, route, search_date, status):
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO scrape_runs (scraped_at, route, search_date, status) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), route, search_date, status)
        )
        return cursor.lastrowid


def insert_flight(db_path, scrape_run_id, airline, flight_number,
                  departure_airport, departure_time, arrival_airport, arrival_time,
                  duration_minutes, price_thb, aircraft_type,
                  num_stops, is_direct, is_excluded_airline,
                  best_booking_price=None, best_booking_source=None,
                  cabin_baggage=None, checked_baggage=None, service_type=None):
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO flights (scrape_run_id, airline, flight_number,
               departure_airport, departure_time, arrival_airport, arrival_time,
               duration_minutes, price_thb, aircraft_type, num_stops,
               is_direct, is_excluded_airline,
               best_booking_price, best_booking_source,
               cabin_baggage, checked_baggage, service_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (scrape_run_id, airline, flight_number,
             departure_airport, departure_time, arrival_airport, arrival_time,
             duration_minutes, price_thb, aircraft_type, num_stops,
             is_direct, is_excluded_airline,
             best_booking_price, best_booking_source,
             cabin_baggage, checked_baggage, service_type)
        )


def get_previous_best_price(db_path, route, search_date):
    with _connect(db_path) as conn:
        rows = conn.execute("""
            SELECT id FROM scrape_runs
            WHERE route = ? AND search_date = ? AND status = 'success'
            ORDER BY scraped_at DESC LIMIT 2
        """, (route, search_date)).fetchall()
        if len(rows) < 2:
            return None
        row = conn.execute("""
            SELECT MIN(price_thb) FROM flights
            WHERE scrape_run_id = ? AND is_direct = 1 AND is_excluded_airline = 0
        """, (rows[1][0],)).fetchone()
        return row[0] if row and row[0] is not None else None


def get_average_price(db_path, route, search_date):
    with _connect(db_path) as conn:
        row = conn.execute("""
            SELECT AVG(best_price) FROM (
                SELECT MIN(f.price_thb) as best_price
                FROM flights f JOIN scrape_runs sr ON f.scrape_run_id = sr.id
                WHERE sr.route = ? AND sr.search_date = ? AND sr.status = 'success'
                  AND f.is_direct = 1 AND f.is_excluded_airline = 0
                GROUP BY sr.id
            )
        """, (route, search_date)).fetchone()
        return int(row[0]) if row and row[0] is not None else None


def get_lowest_ever_price(db_path, route, search_date):
    with _connect(db_path) as conn:
        row = conn.execute("""
            SELECT MIN(f.price_thb)
            FROM flights f JOIN scrape_runs sr ON f.scrape_run_id = sr.id
            WHERE sr.route = ? AND sr.search_date = ? AND sr.status = 'success'
              AND f.is_direct = 1 AND f.is_excluded_airline = 0
        """, (route, search_date)).fetchone()
        return row[0] if row and row[0] is not None else None


def get_recent_flights(db_path, route, search_date, limit=20):
    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT f.*, sr.scraped_at
            FROM flights f JOIN scrape_runs sr ON f.scrape_run_id = sr.id
            WHERE sr.route = ? AND sr.search_date = ? AND sr.status = 'success'
            ORDER BY sr.scraped_at DESC, f.price_thb ASC LIMIT ?
        """, (route, search_date, limit)).fetchall()
        return [dict(row) for row in rows]


def get_scrape_count(db_path, route, search_date):
    with _connect(db_path) as conn:
        row = conn.execute("""
            SELECT COUNT(*) FROM scrape_runs
            WHERE route = ? AND search_date = ? AND status = 'success'
        """, (route, search_date)).fetchone()
        return row[0]


def get_price_history(db_path, route, search_date, limit=10):
    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT sr.scraped_at, MIN(f.price_thb) as best_price
            FROM flights f JOIN scrape_runs sr ON f.scrape_run_id = sr.id
            WHERE sr.route = ? AND sr.search_date = ? AND sr.status = 'success'
              AND f.is_direct = 1 AND f.is_excluded_airline = 0
            GROUP BY sr.id ORDER BY sr.scraped_at DESC LIMIT ?
        """, (route, search_date, limit)).fetchall()
        return [dict(row) for row in rows]


def insert_price_alert(db_path, scrape_run_id, route, search_date,
                       best_price_thb, prev_price_thb, is_lowest_ever):
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO price_alerts (scrape_run_id, route, search_date,
               best_price_thb, prev_price_thb, is_lowest_ever, alerted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (scrape_run_id, route, search_date, best_price_thb,
             prev_price_thb, is_lowest_ever, datetime.now().isoformat())
        )
