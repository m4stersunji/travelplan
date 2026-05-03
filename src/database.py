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
                service_type        TEXT,
                price_score         REAL,
                time_score          REAL,
                total_score         REAL
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
            CREATE TABLE IF NOT EXISTS alert_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type  TEXT NOT NULL,
                route       TEXT,
                message     TEXT,
                sent_at     DATETIME NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_scrape_runs_route_date ON scrape_runs(route, search_date, status);
            CREATE INDEX IF NOT EXISTS idx_flights_run ON flights(scrape_run_id);
            CREATE INDEX IF NOT EXISTS idx_flights_direct ON flights(is_direct, is_excluded_airline, price_thb);
            CREATE INDEX IF NOT EXISTS idx_alert_events_type_time ON alert_events(alert_type, sent_at);
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
                  cabin_baggage=None, checked_baggage=None, service_type=None,
                  price_score=None, time_score=None, total_score=None):
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO flights (scrape_run_id, airline, flight_number,
               departure_airport, departure_time, arrival_airport, arrival_time,
               duration_minutes, price_thb, aircraft_type, num_stops,
               is_direct, is_excluded_airline,
               best_booking_price, best_booking_source,
               cabin_baggage, checked_baggage, service_type,
               price_score, time_score, total_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (scrape_run_id, airline, flight_number,
             departure_airport, departure_time, arrival_airport, arrival_time,
             duration_minutes, price_thb, aircraft_type, num_stops,
             is_direct, is_excluded_airline,
             best_booking_price, best_booking_source,
             cabin_baggage, checked_baggage, service_type,
             price_score, time_score, total_score)
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
            SELECT MIN(COALESCE(f.best_booking_price, f.price_thb)) FROM flights f
            WHERE f.scrape_run_id = ? AND f.is_direct = 1 AND f.is_excluded_airline = 0
        """, (rows[1][0],)).fetchone()
        return row[0] if row and row[0] is not None else None


def get_average_price(db_path, route, search_date):
    with _connect(db_path) as conn:
        row = conn.execute("""
            SELECT AVG(best_price) FROM (
                SELECT MIN(COALESCE(f.best_booking_price, f.price_thb)) as best_price
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
            SELECT MIN(COALESCE(f.best_booking_price, f.price_thb))
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


def get_consecutive_failures(db_path, consecutive=3):
    """Return routes whose last `consecutive` runs all failed."""
    with _connect(db_path) as conn:
        rows = conn.execute("""
            WITH recent AS (
                SELECT route, status,
                       ROW_NUMBER() OVER (PARTITION BY route ORDER BY scraped_at DESC) AS rn
                FROM scrape_runs
            )
            SELECT route FROM recent
            WHERE rn <= ?
            GROUP BY route
            HAVING COUNT(*) = ? AND SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) = ?
        """, (consecutive, consecutive, consecutive)).fetchall()
        return [r[0] for r in rows]


def insert_alert_event(db_path, alert_type, route=None, message=None):
    """Records a fired alert. sent_at is stored as UTC ISO so it can be compared
    against SQLite datetime('now', ...) (which is also UTC) without a TZ skew.
    Other tables in this module store local time for human-readable display;
    only alert_events participates in time-arithmetic queries."""
    from datetime import timezone
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO alert_events (alert_type, route, message, sent_at) VALUES (?, ?, ?, ?)",
            (alert_type, route, message, datetime.now(timezone.utc).isoformat())
        )


def recently_alerted(db_path, alert_type, within_hours=6):
    """True if an alert of this type was sent within the past `within_hours`.

    sent_at is stored as datetime.isoformat() ('YYYY-MM-DDTHH:MM:SS.ffffff'),
    but datetime('now', ...) returns space-separated text. Wrap sent_at in
    datetime() so SQLite parses both as time values and compares numerically;
    a raw string compare treats 'T' (0x54) > ' ' (0x20) and falsely marks
    same-day entries as recent until UTC midnight.
    """
    with _connect(db_path) as conn:
        row = conn.execute("""
            SELECT 1 FROM alert_events
            WHERE alert_type = ?
              AND datetime(sent_at) >= datetime('now', ?)
            LIMIT 1
        """, (alert_type, f'-{within_hours} hours')).fetchone()
        return row is not None
