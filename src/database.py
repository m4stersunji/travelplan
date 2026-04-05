import sqlite3
from datetime import datetime


def init_db(db_path):
    conn = sqlite3.connect(db_path)
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
            departure_time      TEXT,
            arrival_time        TEXT,
            duration_minutes    INTEGER,
            price_thb           INTEGER,
            aircraft_type       TEXT,
            num_stops           INTEGER,
            is_direct           BOOLEAN,
            is_excluded_airline BOOLEAN,
            is_preferred_time   BOOLEAN
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
    conn.close()


def insert_scrape_run(db_path, route, search_date, status):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "INSERT INTO scrape_runs (scraped_at, route, search_date, status) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), route, search_date, status)
    )
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return run_id


def insert_flight(db_path, scrape_run_id, airline, flight_number, departure_time,
                  arrival_time, duration_minutes, price_thb, aircraft_type,
                  num_stops, is_direct, is_excluded_airline, is_preferred_time):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO flights (scrape_run_id, airline, flight_number, departure_time,
           arrival_time, duration_minutes, price_thb, aircraft_type, num_stops,
           is_direct, is_excluded_airline, is_preferred_time)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (scrape_run_id, airline, flight_number, departure_time, arrival_time,
         duration_minutes, price_thb, aircraft_type, num_stops,
         is_direct, is_excluded_airline, is_preferred_time)
    )
    conn.commit()
    conn.close()


def get_previous_best_price(db_path, route, search_date):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT MIN(f.price_thb) as best_price
        FROM flights f
        JOIN scrape_runs sr ON f.scrape_run_id = sr.id
        WHERE sr.route = ? AND sr.search_date = ? AND sr.status = 'success'
          AND f.is_direct = 1 AND f.is_excluded_airline = 0
        ORDER BY sr.scraped_at DESC
        LIMIT 1
    """, (route, search_date)).fetchone()
    conn.close()
    if row and row['best_price'] is not None:
        return row['best_price']
    return None


def get_lowest_ever_price(db_path, route, search_date):
    conn = sqlite3.connect(db_path)
    row = conn.execute("""
        SELECT MIN(f.price_thb) as lowest
        FROM flights f
        JOIN scrape_runs sr ON f.scrape_run_id = sr.id
        WHERE sr.route = ? AND sr.search_date = ? AND sr.status = 'success'
          AND f.is_direct = 1 AND f.is_excluded_airline = 0
    """, (route, search_date)).fetchone()
    conn.close()
    if row and row[0] is not None:
        return row[0]
    return None


def get_recent_flights(db_path, route, search_date, limit=20):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT f.*, sr.scraped_at
        FROM flights f
        JOIN scrape_runs sr ON f.scrape_run_id = sr.id
        WHERE sr.route = ? AND sr.search_date = ? AND sr.status = 'success'
        ORDER BY sr.scraped_at DESC, f.price_thb ASC
        LIMIT ?
    """, (route, search_date, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_scrape_count(db_path, route, search_date):
    conn = sqlite3.connect(db_path)
    row = conn.execute("""
        SELECT COUNT(*) FROM scrape_runs
        WHERE route = ? AND search_date = ? AND status = 'success'
    """, (route, search_date)).fetchone()
    conn.close()
    return row[0]


def insert_price_alert(db_path, scrape_run_id, route, search_date,
                       best_price_thb, prev_price_thb, is_lowest_ever):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO price_alerts (scrape_run_id, route, search_date,
           best_price_thb, prev_price_thb, is_lowest_ever, alerted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (scrape_run_id, route, search_date, best_price_thb,
         prev_price_thb, is_lowest_ever, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
