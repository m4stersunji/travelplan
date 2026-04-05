# Flight Price Tracker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python flight price tracker that scrapes Google Flights every 4 hours, stores results in SQLite, sends LINE notifications, and exports CSV — starting with BKK↔DAD (Danang) routes.

**Architecture:** Selenium scrapes Google Flights headless, stores results in SQLite via a database module, triggers LINE Messaging API alerts via a notifier module, and exports CSV. A main orchestrator ties them together, run by system cron every 4 hours.

**Tech Stack:** Python 3.12, Selenium, Chrome headless, SQLite3, requests (LINE API), cron

---

## File Structure

```
travelplan/
├── src/
│   ├── config.py           # All configuration: routes, dates, airline lists, LINE token
│   ├── database.py         # SQLite schema setup, inserts, queries
│   ├── scraper.py          # Selenium Google Flights scraper
│   ├── notifier.py         # LINE Messaging API push message
│   ├── exporter.py         # CSV export from DB
│   └── main.py             # Orchestrator: scrape → store → compare → notify → export
├── tests/
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_scraper.py
│   ├── test_notifier.py
│   ├── test_exporter.py
│   └── test_main.py
├── data/                   # SQLite DB + CSV exports (gitignored)
├── logs/                   # Scraper logs (gitignored)
├── requirements.txt
├── setup_cron.sh
├── .gitignore
└── .env                    # LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (gitignored)
```

---

## Task 0: Environment Setup

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env`

- [ ] **Step 1: Initialize git repo**

```bash
cd /home/m4stersun/travelplan
git init
```

- [ ] **Step 2: Create requirements.txt**

```
selenium==4.27.1
requests==2.32.3
python-dotenv==1.0.1
```

- [ ] **Step 3: Create .gitignore**

```
data/
logs/
.env
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: Create .env template**

```
LINE_CHANNEL_ACCESS_TOKEN=your_token_here
LINE_USER_ID=your_user_id_here
```

- [ ] **Step 5: Create directories**

```bash
mkdir -p src tests data logs
```

- [ ] **Step 6: Install Chrome headless + chromedriver on WSL2**

```bash
# Install Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable
```

- [ ] **Step 7: Install Python dependencies**

```bash
pip3 install -r requirements.txt
```

- [ ] **Step 8: Verify Chrome works headless**

```bash
google-chrome --headless --no-sandbox --disable-gpu --dump-dom https://www.google.com 2>/dev/null | head -5
```

Expected: HTML output from google.com

- [ ] **Step 9: Commit**

```bash
git add requirements.txt .gitignore
git commit -m "chore: initial project setup with dependencies and gitignore"
```

---

## Task 1: Configuration Module

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import (
    SEARCH_ROUTES,
    EXCLUDED_AIRLINES,
    PREFERRED_DEPARTURE_START,
    PREFERRED_DEPARTURE_END,
    DB_PATH,
    DATA_DIR,
    LOG_DIR,
)


def test_search_routes_has_danang_trip():
    routes = SEARCH_ROUTES
    assert len(routes) >= 4  # 2 outbound dates x 2 return dates
    origins = {r["origin"] for r in routes}
    destinations = {r["destination"] for r in routes}
    assert "BKK" in origins
    assert "DAD" in destinations or "DAD" in origins


def test_excluded_airlines_contains_middle_east_carriers():
    assert "Emirates" in EXCLUDED_AIRLINES
    assert "Qatar Airways" in EXCLUDED_AIRLINES
    assert "Etihad" in EXCLUDED_AIRLINES
    assert "Oman Air" in EXCLUDED_AIRLINES
    assert "Saudia" in EXCLUDED_AIRLINES
    assert "Gulf Air" in EXCLUDED_AIRLINES
    assert "flynas" in EXCLUDED_AIRLINES
    assert "Air Arabia" in EXCLUDED_AIRLINES


def test_preferred_departure_window():
    assert PREFERRED_DEPARTURE_START == "09:00"
    assert PREFERRED_DEPARTURE_END == "12:00"


def test_paths_are_absolute():
    assert os.path.isabs(DB_PATH)
    assert os.path.isabs(DATA_DIR)
    assert os.path.isabs(LOG_DIR)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Write the implementation**

```python
# src/config.py
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'flights.db')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')

# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_USER_ID = os.getenv('LINE_USER_ID', '')

# Middle Eastern airlines to flag (not remove)
EXCLUDED_AIRLINES = [
    "Emirates",
    "Qatar Airways",
    "Etihad",
    "Oman Air",
    "Saudia",
    "Gulf Air",
    "flynas",
    "Air Arabia",
]

# Preferred departure window for BKK→DAD (targeting ~1pm arrival)
PREFERRED_DEPARTURE_START = "09:00"
PREFERRED_DEPARTURE_END = "12:00"

# Search routes — each is one Google Flights search
SEARCH_ROUTES = [
    # Danang Trip — Outbound options
    {"origin": "BKK", "destination": "DAD", "date": "2026-05-29", "label": "BKK-DAD-May29"},
    {"origin": "BKK", "destination": "DAD", "date": "2026-05-30", "label": "BKK-DAD-May30"},
    # Danang Trip — Return options
    {"origin": "DAD", "destination": "BKK", "date": "2026-06-01", "label": "DAD-BKK-Jun01"},
    {"origin": "DAD", "destination": "BKK", "date": "2026-06-02", "label": "DAD-BKK-Jun02"},
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_config.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add config module with routes, airline flags, and paths"
```

---

## Task 2: Database Module

**Files:**
- Create: `src/database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_database.py
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
        insert_flight(db_path, scrape_run_id=run_id, airline='Thai AirAsia', flight_number='FD636',
                      departure_time='10:15', arrival_time='12:15', duration_minutes=120,
                      price_thb=3250, aircraft_type='A320', num_stops=0,
                      is_direct=True, is_excluded_airline=False, is_preferred_time=True)
        flights = get_recent_flights(db_path, route='BKK-DAD', search_date='2026-05-29', limit=10)
        assert len(flights) == 1
        assert flights[0]['airline'] == 'Thai AirAsia'
        assert flights[0]['price_thb'] == 3250
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


def test_get_lowest_ever_price():
    db_path = make_temp_db()
    try:
        init_db(db_path)
        # Run 1: price 4000
        run1 = insert_scrape_run(db_path, route='BKK-DAD', search_date='2026-05-29', status='success')
        insert_flight(db_path, scrape_run_id=run1, airline='AirAsia', flight_number='FD1',
                      departure_time='10:00', arrival_time='12:00', duration_minutes=120,
                      price_thb=4000, aircraft_type='A320', num_stops=0,
                      is_direct=True, is_excluded_airline=False, is_preferred_time=True)
        # Run 2: price 3500
        run2 = insert_scrape_run(db_path, route='BKK-DAD', search_date='2026-05-29', status='success')
        insert_flight(db_path, scrape_run_id=run2, airline='AirAsia', flight_number='FD1',
                      departure_time='10:00', arrival_time='12:00', duration_minutes=120,
                      price_thb=3500, aircraft_type='A320', num_stops=0,
                      is_direct=True, is_excluded_airline=False, is_preferred_time=True)
        lowest = get_lowest_ever_price(db_path, route='BKK-DAD', search_date='2026-05-29')
        assert lowest == 3500
    finally:
        os.unlink(db_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'database'`

- [ ] **Step 3: Write the implementation**

```python
# src/database.py
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
    """Get the best price from the most recent completed scrape (excluding current)."""
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
    """Get the lowest price ever recorded for direct, non-excluded flights."""
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
    """Get flights from the most recent scrape run for a route+date."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT f.*, sr.scraped_at
        FROM flights f
        JOIN scrape_runs sr ON f.scrape_run_id = sr.id
        WHERE sr.route = ? AND sr.search_date = ?  AND sr.status = 'success'
        ORDER BY sr.scraped_at DESC, f.price_thb ASC
        LIMIT ?
    """, (route, search_date, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_scrape_count(db_path, route, search_date):
    """Get total number of successful scrapes for a route+date."""
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_database.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat: add database module with SQLite schema, inserts, and queries"
```

---

## Task 3: Google Flights Scraper

**Files:**
- Create: `src/scraper.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scraper.py
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scraper import build_google_flights_url, parse_flight_data, classify_flight
from config import EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END


def test_build_google_flights_url():
    url = build_google_flights_url(origin='BKK', destination='DAD', date='2026-05-29')
    assert 'google.com/travel/flights' in url
    assert 'BKK' in url
    assert 'DAD' in url


def test_classify_flight_direct_preferred():
    flight = {
        'airline': 'Thai AirAsia',
        'num_stops': 0,
        'departure_time': '10:15',
    }
    classified = classify_flight(flight, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END)
    assert classified['is_direct'] is True
    assert classified['is_excluded_airline'] is False
    assert classified['is_preferred_time'] is True


def test_classify_flight_excluded_airline():
    flight = {
        'airline': 'Emirates',
        'num_stops': 1,
        'departure_time': '08:00',
    }
    classified = classify_flight(flight, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END)
    assert classified['is_direct'] is False
    assert classified['is_excluded_airline'] is True
    assert classified['is_preferred_time'] is False


def test_classify_flight_outside_preferred_time():
    flight = {
        'airline': 'VietJet',
        'num_stops': 0,
        'departure_time': '15:30',
    }
    classified = classify_flight(flight, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END)
    assert classified['is_direct'] is True
    assert classified['is_excluded_airline'] is False
    assert classified['is_preferred_time'] is False


def test_parse_flight_data_returns_list():
    # parse_flight_data takes raw HTML/page source and returns list of dicts
    # With empty input, should return empty list
    result = parse_flight_data("")
    assert isinstance(result, list)
    assert len(result) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_scraper.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scraper'`

- [ ] **Step 3: Write the implementation**

```python
# src/scraper.py
import logging
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)


def build_google_flights_url(origin, destination, date):
    """Build a Google Flights search URL for a one-way flight."""
    # Google Flights URL format for one-way search
    return (
        f"https://www.google.com/travel/flights?q=Flights"
        f"+from+{origin}+to+{destination}+on+{date}+oneway"
        f"&curr=THB&hl=en"
    )


def create_driver():
    """Create a headless Chrome Selenium driver."""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--lang=en-US')
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


def scrape_flights(origin, destination, date):
    """Scrape Google Flights for a one-way route on a given date.

    Returns a list of flight dicts or empty list on failure.
    """
    url = build_google_flights_url(origin, destination, date)
    logger.info(f"Scraping: {url}")

    driver = None
    try:
        driver = create_driver()
        driver.get(url)

        # Wait for flight results to load
        time.sleep(5)  # Initial wait for page load

        # Try to find flight result elements
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-role="flight"],.gws-flights-results__result-item,li.pIav2d'))
            )
        except TimeoutException:
            logger.warning("Timeout waiting for flight results — trying to parse whatever loaded")

        page_source = driver.page_source
        flights = parse_flight_data(page_source)
        logger.info(f"Found {len(flights)} flights for {origin}->{destination} on {date}")
        return flights

    except WebDriverException as e:
        logger.error(f"Browser error scraping {origin}->{destination} {date}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error scraping {origin}->{destination} {date}: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def parse_flight_data(page_source):
    """Parse flight data from Google Flights page source.

    Returns a list of dicts with keys: airline, flight_number, departure_time,
    arrival_time, duration_minutes, price_thb, aircraft_type, num_stops.
    """
    if not page_source:
        return []

    flights = []

    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from lxml import html

        tree = html.fromstring(page_source)

        # Google Flights uses various selectors — try common patterns
        # Flight result list items
        result_items = tree.cssselect('li.pIav2d') or tree.cssselect('[data-role="flight"]')

        for item in result_items:
            try:
                flight = {}

                # Airline name — typically in a span or div with specific classes
                airline_els = item.cssselect('.sSHqwe.tPgKwe.ogfYpf, .Ir0Voe .sSHqwe')
                flight['airline'] = airline_els[0].text_content().strip() if airline_els else 'Unknown'

                # Times — departure and arrival
                time_els = item.cssselect('[aria-label*="Departure"], [aria-label*="Arrival"], .mv1WYe span')
                times = [el.text_content().strip() for el in time_els if re.match(r'\d{1,2}:\d{2}', el.text_content().strip())]
                flight['departure_time'] = times[0] if len(times) > 0 else ''
                flight['arrival_time'] = times[1] if len(times) > 1 else ''

                # Duration
                duration_els = item.cssselect('.gvkrdb, .Ak5kof')
                duration_text = duration_els[0].text_content().strip() if duration_els else ''
                flight['duration_minutes'] = parse_duration(duration_text)

                # Price
                price_els = item.cssselect('[data-price], .YMlIz span, .U3gSDe')
                price_text = price_els[0].text_content().strip() if price_els else '0'
                flight['price_thb'] = parse_price(price_text)

                # Stops
                stop_els = item.cssselect('.EfT7Ae span, .ogfYpf')
                stop_text = ' '.join(el.text_content() for el in stop_els)
                flight['num_stops'] = parse_stops(stop_text)

                # Aircraft type — sometimes in expanded details
                aircraft_els = item.cssselect('.U3gSDe, [data-aircraft]')
                flight['aircraft_type'] = extract_aircraft(
                    ' '.join(el.text_content() for el in aircraft_els)
                )

                # Flight number
                fn_els = item.cssselect('.Xsgmwe, [data-flightnumber]')
                flight['flight_number'] = fn_els[0].text_content().strip() if fn_els else ''

                if flight['price_thb'] > 0:
                    flights.append(flight)

            except Exception as e:
                logger.debug(f"Failed to parse a flight item: {e}")
                continue

    except ImportError:
        logger.warning("lxml not available, attempting regex fallback")
        flights = parse_flight_data_regex(page_source)
    except Exception as e:
        logger.warning(f"HTML parsing failed, trying regex fallback: {e}")
        flights = parse_flight_data_regex(page_source)

    return flights


def parse_flight_data_regex(page_source):
    """Regex fallback parser for when lxml is not available."""
    flights = []
    # Price pattern: ฿X,XXX or THB X,XXX
    prices = re.findall(r'[฿][\s]*([\d,]+)', page_source)
    times = re.findall(r'(\d{1,2}:\d{2}\s*[AP]M)', page_source, re.IGNORECASE)

    # Basic extraction — pair up what we can find
    for i, price in enumerate(prices):
        flight = {
            'airline': 'Unknown',
            'flight_number': '',
            'departure_time': times[i * 2] if i * 2 < len(times) else '',
            'arrival_time': times[i * 2 + 1] if i * 2 + 1 < len(times) else '',
            'duration_minutes': 0,
            'price_thb': parse_price(price),
            'aircraft_type': '',
            'num_stops': 0,
        }
        if flight['price_thb'] > 0:
            flights.append(flight)

    return flights


def classify_flight(flight, excluded_airlines, pref_dep_start, pref_dep_end):
    """Add classification flags to a flight dict.

    Adds: is_direct, is_excluded_airline, is_preferred_time.
    Returns the same dict with new keys added.
    """
    flight['is_direct'] = flight.get('num_stops', 0) == 0

    airline = flight.get('airline', '')
    flight['is_excluded_airline'] = any(
        excluded.lower() in airline.lower() for excluded in excluded_airlines
    )

    dep_time = flight.get('departure_time', '')
    # Normalize time to HH:MM for comparison
    dep_normalized = normalize_time(dep_time)
    flight['is_preferred_time'] = (
        pref_dep_start <= dep_normalized <= pref_dep_end
        if dep_normalized else False
    )

    return flight


def normalize_time(time_str):
    """Convert time string to HH:MM 24h format."""
    if not time_str:
        return ''

    # Handle "10:15 AM" / "2:30 PM" format
    match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)?', time_str, re.IGNORECASE)
    if not match:
        return time_str

    hours, minutes = int(match.group(1)), match.group(2)
    period = match.group(3)

    if period:
        if period.upper() == 'PM' and hours != 12:
            hours += 12
        elif period.upper() == 'AM' and hours == 12:
            hours = 0

    return f"{hours:02d}:{minutes}"


def parse_duration(text):
    """Parse duration text like '2 hr 15 min' into minutes."""
    if not text:
        return 0
    hours = re.search(r'(\d+)\s*h', text)
    minutes = re.search(r'(\d+)\s*m', text)
    total = 0
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
    return total


def parse_price(text):
    """Parse price text like '฿3,250' or '3,250' into integer."""
    if not text:
        return 0
    digits = re.sub(r'[^\d]', '', text)
    return int(digits) if digits else 0


def parse_stops(text):
    """Parse stop count from text like 'Nonstop', '1 stop', '2 stops'."""
    if not text:
        return 0
    text_lower = text.lower()
    if 'nonstop' in text_lower or 'direct' in text_lower:
        return 0
    match = re.search(r'(\d+)\s*stop', text_lower)
    return int(match.group(1)) if match else 0


def extract_aircraft(text):
    """Extract aircraft type from text if present."""
    if not text:
        return ''
    patterns = [
        r'(A\d{3}(?:-\d{3})?)',          # Airbus: A320, A321-200
        r'(7[0-9]{2}(?:-\d{1,4})?)',      # Boeing: 737, 737-800, 787
        r'(ATR\s*\d{2})',                  # ATR 72
        r'(CRJ[\s-]?\d{3})',              # CRJ-900
        r'(E\d{3})',                       # Embraer E190
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return ''
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_scraper.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/scraper.py tests/test_scraper.py
git commit -m "feat: add Google Flights scraper with Selenium and flight classification"
```

---

## Task 4: LINE Notifier

**Files:**
- Create: `src/notifier.py`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_notifier.py
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from notifier import format_price_change, format_notification_message


def test_format_price_change_decrease():
    result = format_price_change(3250, 3600)
    assert '▼' in result
    assert '350' in result


def test_format_price_change_increase():
    result = format_price_change(3800, 3600)
    assert '▲' in result
    assert '200' in result


def test_format_price_change_same():
    result = format_price_change(3600, 3600)
    assert '—' in result


def test_format_price_change_no_previous():
    result = format_price_change(3600, None)
    assert 'NEW' in result


def test_format_notification_message():
    flights = [
        {
            'airline': 'Thai AirAsia', 'flight_number': 'FD636',
            'departure_time': '10:15', 'arrival_time': '12:15',
            'price_thb': 3250, 'aircraft_type': 'A320', 'num_stops': 0,
            'is_direct': True, 'is_excluded_airline': False, 'is_preferred_time': True,
        },
        {
            'airline': 'Emirates', 'flight_number': 'EK374',
            'departure_time': '08:00', 'arrival_time': '16:30',
            'price_thb': 2900, 'aircraft_type': '777', 'num_stops': 1,
            'is_direct': False, 'is_excluded_airline': True, 'is_preferred_time': False,
        },
    ]
    msg = format_notification_message(
        route='BKK→DAD', search_date='29 May',
        flights=flights, prev_best_price=3600,
        lowest_ever=3250, scrape_count=10
    )
    assert 'Thai AirAsia' in msg
    assert 'FD636' in msg
    assert '3,250' in msg
    assert 'Emirates' in msg
    assert 'LOWEST EVER' in msg or '⭐' in msg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_notifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'notifier'`

- [ ] **Step 3: Write the implementation**

```python
# src/notifier.py
import logging
import requests

from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

logger = logging.getLogger(__name__)

LINE_API_URL = "https://api.line.me/v2/bot/message/push"


def send_line_notification(message):
    """Send a push message via LINE Messaging API."""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        logger.warning("LINE credentials not configured — skipping notification")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {"type": "text", "text": message}
        ],
    }

    try:
        resp = requests.post(LINE_API_URL, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("LINE notification sent successfully")
            return True
        else:
            logger.error(f"LINE API error {resp.status_code}: {resp.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"Failed to send LINE notification: {e}")
        return False


def format_price_change(current_price, previous_price):
    """Format price change indicator."""
    if previous_price is None:
        return "🆕 NEW"
    diff = current_price - previous_price
    if diff < 0:
        return f"▼ -{abs(diff):,}"
    elif diff > 0:
        return f"▲ +{diff:,}"
    else:
        return "— same"


def format_notification_message(route, search_date, flights, prev_best_price,
                                lowest_ever, scrape_count):
    """Format the full LINE notification message.

    Flights should already be sorted by price ascending.
    """
    if not flights:
        return f"✈️ {route} {search_date}\n\n❌ No flights found this check."

    # Separate direct non-excluded vs others
    direct_flights = [f for f in flights if f['is_direct'] and not f['is_excluded_airline']]
    other_flights = [f for f in flights if not f['is_direct'] or f['is_excluded_airline']]

    # Sort each group by price
    direct_flights.sort(key=lambda f: f['price_thb'])
    other_flights.sort(key=lambda f: f['price_thb'])

    lines = [f"✈️ Flight Price Update — {route} {search_date}", ""]

    # Best deal (cheapest direct non-excluded)
    if direct_flights:
        best = direct_flights[0]
        change = format_price_change(best['price_thb'], prev_best_price)
        is_lowest = best['price_thb'] <= lowest_ever if lowest_ever else True

        lines.append(f"🏆 Best Deal: {best['airline']} | {best['flight_number']}")
        lines.append(f"   ฿{best['price_thb']:,} ({change})")
        if is_lowest:
            lines.append("   ⭐ LOWEST EVER")
        lines.append(f"   Depart {best['departure_time']} → Arrive {best['arrival_time']}")
        lines.append(f"   Aircraft: {best['aircraft_type'] or 'N/A'}")
        lines.append("")

        # Other direct flights
        if len(direct_flights) > 1:
            lines.append("📊 Other Direct Flights:")
            for f in direct_flights[1:]:
                change = format_price_change(f['price_thb'], prev_best_price)
                pref = " ⏰" if f['is_preferred_time'] else ""
                lines.append(
                    f"   {f['airline']} {f['flight_number']} | "
                    f"฿{f['price_thb']:,} ({change}) | "
                    f"{f['departure_time']}→{f['arrival_time']} | "
                    f"{f['aircraft_type'] or 'N/A'}{pref}"
                )
            lines.append("")

    # Others (with stops or excluded airlines)
    if other_flights:
        lines.append("📌 With Stops / Excluded Airlines (FYI):")
        for f in other_flights:
            stop_info = f"({f['num_stops']} stop)" if f['num_stops'] > 0 else "(direct)"
            lines.append(
                f"   {f['airline']} {f['flight_number']} | "
                f"฿{f['price_thb']:,} {stop_info} | "
                f"{f['departure_time']}→{f['arrival_time']} | "
                f"{f['aircraft_type'] or 'N/A'}"
            )
        lines.append("")

    from datetime import datetime
    lines.append(f"🕐 Checked: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"📈 Tracking: {scrape_count} checks so far")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_notifier.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/notifier.py tests/test_notifier.py
git commit -m "feat: add LINE notifier with message formatting and push API"
```

---

## Task 5: CSV Exporter

**Files:**
- Create: `src/exporter.py`
- Create: `tests/test_exporter.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_exporter.py
import sys
import os
import csv
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from exporter import export_flights_to_csv


def test_export_creates_csv_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        flights = [
            {
                'airline': 'Thai AirAsia', 'flight_number': 'FD636',
                'departure_time': '10:15', 'arrival_time': '12:15',
                'duration_minutes': 120, 'price_thb': 3250,
                'aircraft_type': 'A320', 'num_stops': 0,
                'is_direct': True, 'is_excluded_airline': False,
                'is_preferred_time': True, 'scraped_at': '2026-04-05T14:00:00',
            },
        ]
        filepath = export_flights_to_csv(tmpdir, 'BKK-DAD', '2026-05-29', flights)
        assert os.path.exists(filepath)
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['airline'] == 'Thai AirAsia'
        assert rows[0]['price_thb'] == '3250'


def test_export_appends_to_existing_csv():
    with tempfile.TemporaryDirectory() as tmpdir:
        flights1 = [
            {
                'airline': 'AirAsia', 'flight_number': 'FD1',
                'departure_time': '10:00', 'arrival_time': '12:00',
                'duration_minutes': 120, 'price_thb': 4000,
                'aircraft_type': 'A320', 'num_stops': 0,
                'is_direct': True, 'is_excluded_airline': False,
                'is_preferred_time': True, 'scraped_at': '2026-04-05T10:00:00',
            },
        ]
        flights2 = [
            {
                'airline': 'VietJet', 'flight_number': 'VZ1',
                'departure_time': '09:00', 'arrival_time': '11:00',
                'duration_minutes': 120, 'price_thb': 3500,
                'aircraft_type': 'A321', 'num_stops': 0,
                'is_direct': True, 'is_excluded_airline': False,
                'is_preferred_time': True, 'scraped_at': '2026-04-05T14:00:00',
            },
        ]
        export_flights_to_csv(tmpdir, 'BKK-DAD', '2026-05-29', flights1)
        filepath = export_flights_to_csv(tmpdir, 'BKK-DAD', '2026-05-29', flights2)
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_exporter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'exporter'`

- [ ] **Step 3: Write the implementation**

```python
# src/exporter.py
import csv
import os
import logging

logger = logging.getLogger(__name__)

CSV_FIELDS = [
    'scraped_at', 'airline', 'flight_number', 'departure_time', 'arrival_time',
    'duration_minutes', 'price_thb', 'aircraft_type', 'num_stops',
    'is_direct', 'is_excluded_airline', 'is_preferred_time',
]


def export_flights_to_csv(data_dir, route, search_date, flights):
    """Append flight data to a CSV file for the given route and date.

    File: {data_dir}/{route}-{search_date}.csv
    Creates the file with headers if it doesn't exist, appends otherwise.
    Returns the file path.
    """
    filename = f"{route}-{search_date}.csv"
    filepath = os.path.join(data_dir, filename)

    file_exists = os.path.exists(filepath)

    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        for flight in flights:
            writer.writerow(flight)

    logger.info(f"Exported {len(flights)} flights to {filepath}")
    return filepath
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_exporter.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/exporter.py tests/test_exporter.py
git commit -m "feat: add CSV exporter with append support"
```

---

## Task 6: Main Orchestrator

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_main.py
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import patch, MagicMock
from main import process_route


def test_process_route_with_mock_scraper():
    """Test the orchestration flow with mocked scraper."""
    mock_flights = [
        {
            'airline': 'Thai AirAsia', 'flight_number': 'FD636',
            'departure_time': '10:15', 'arrival_time': '12:15',
            'duration_minutes': 120, 'price_thb': 3250,
            'aircraft_type': 'A320', 'num_stops': 0,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        data_dir = tmpdir

        with patch('main.scrape_flights', return_value=mock_flights), \
             patch('main.send_line_notification', return_value=True) as mock_notify:

            from database import init_db
            init_db(db_path)

            result = process_route(
                origin='BKK', destination='DAD', date='2026-05-29',
                label='BKK-DAD-May29', db_path=db_path, data_dir=data_dir
            )

            assert result is True
            mock_notify.assert_called_once()


def test_process_route_scraper_fails():
    """Test orchestration handles scraper failure gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        data_dir = tmpdir

        with patch('main.scrape_flights', return_value=[]):
            from database import init_db
            init_db(db_path)

            result = process_route(
                origin='BKK', destination='DAD', date='2026-05-29',
                label='BKK-DAD-May29', db_path=db_path, data_dir=data_dir
            )

            assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Write the implementation**

```python
# src/main.py
import logging
import os
import sys
from datetime import datetime

from config import SEARCH_ROUTES, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END, DB_PATH, DATA_DIR, LOG_DIR
from database import init_db, insert_scrape_run, insert_flight, get_previous_best_price, get_lowest_ever_price, get_scrape_count, insert_price_alert, get_recent_flights
from scraper import scrape_flights, classify_flight
from notifier import send_line_notification, format_notification_message
from exporter import export_flights_to_csv

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging to file and stdout."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"scraper_{datetime.now().strftime('%Y%m%d')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ]
    )


def process_route(origin, destination, date, label, db_path, data_dir):
    """Process a single route: scrape → classify → store → notify → export.

    Returns True if flights were found and processed, False otherwise.
    """
    route = f"{origin}-{destination}"

    # Scrape
    raw_flights = scrape_flights(origin, destination, date)

    if not raw_flights:
        logger.warning(f"No flights found for {route} on {date}")
        insert_scrape_run(db_path, route=route, search_date=date, status='error')
        return False

    # Classify each flight
    flights = []
    for f in raw_flights:
        classified = classify_flight(f, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END)
        flights.append(classified)

    # Store in DB
    run_id = insert_scrape_run(db_path, route=route, search_date=date, status='success')
    for f in flights:
        insert_flight(
            db_path, scrape_run_id=run_id,
            airline=f.get('airline', ''), flight_number=f.get('flight_number', ''),
            departure_time=f.get('departure_time', ''), arrival_time=f.get('arrival_time', ''),
            duration_minutes=f.get('duration_minutes', 0), price_thb=f.get('price_thb', 0),
            aircraft_type=f.get('aircraft_type', ''), num_stops=f.get('num_stops', 0),
            is_direct=f.get('is_direct', False),
            is_excluded_airline=f.get('is_excluded_airline', False),
            is_preferred_time=f.get('is_preferred_time', False),
        )

    # Compare prices
    prev_best = get_previous_best_price(db_path, route, date)
    lowest_ever = get_lowest_ever_price(db_path, route, date)
    scrape_count = get_scrape_count(db_path, route, date)

    # Check if current best is lowest ever
    direct_prices = [f['price_thb'] for f in flights if f['is_direct'] and not f['is_excluded_airline'] and f['price_thb'] > 0]
    current_best = min(direct_prices) if direct_prices else None
    is_lowest = current_best is not None and (lowest_ever is None or current_best <= lowest_ever)

    # Store alert record
    insert_price_alert(db_path, run_id, route, date, current_best, prev_best, is_lowest)

    # Format readable date
    date_label = datetime.strptime(date, '%Y-%m-%d').strftime('%d %b')

    # Send LINE notification
    route_display = f"{origin}→{destination}"
    message = format_notification_message(
        route=route_display, search_date=date_label,
        flights=flights, prev_best_price=prev_best,
        lowest_ever=lowest_ever, scrape_count=scrape_count,
    )
    send_line_notification(message)

    # Export CSV
    os.makedirs(data_dir, exist_ok=True)
    scraped_at = datetime.now().isoformat()
    flights_with_timestamp = [{**f, 'scraped_at': scraped_at} for f in flights]
    export_flights_to_csv(data_dir, route, date, flights_with_timestamp)

    logger.info(f"✅ {route} {date}: {len(flights)} flights, best ฿{current_best:,}" if current_best else f"✅ {route} {date}: {len(flights)} flights (no direct non-excluded)")
    return True


def main():
    """Run the full scrape cycle for all configured routes."""
    setup_logging()
    logger.info("=" * 60)
    logger.info(f"Starting flight price check at {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # Ensure DB exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    init_db(DB_PATH)

    results = []
    for route in SEARCH_ROUTES:
        success = process_route(
            origin=route['origin'],
            destination=route['destination'],
            date=route['date'],
            label=route['label'],
            db_path=DB_PATH,
            data_dir=DATA_DIR,
        )
        results.append((route['label'], success))

    # Summary
    logger.info("=" * 60)
    for label, success in results:
        status = "✅" if success else "❌"
        logger.info(f"  {status} {label}")
    logger.info("=" * 60)
    logger.info("Done.")


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/m4stersun/travelplan && python3 -m pytest tests/test_main.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add main orchestrator — scrape, store, notify, export pipeline"
```

---

## Task 7: Cron Setup Script

**Files:**
- Create: `setup_cron.sh`

- [ ] **Step 1: Write the cron setup script**

```bash
#!/bin/bash
# setup_cron.sh — Install cron job to run flight scraper every 4 hours

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3)"
MAIN="${SCRIPT_DIR}/src/main.py"
LOG_DIR="${SCRIPT_DIR}/logs"

mkdir -p "$LOG_DIR"

CRON_CMD="0 */4 * * * cd ${SCRIPT_DIR} && ${PYTHON} ${MAIN} >> ${LOG_DIR}/cron.log 2>&1"

# Check if cron job already exists
(crontab -l 2>/dev/null | grep -F "$MAIN") && {
    echo "Cron job already exists. Skipping."
    exit 0
}

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ Cron job installed: every 4 hours"
echo "   $CRON_CMD"
echo ""
echo "To verify: crontab -l"
echo "To remove: crontab -e (and delete the line)"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x setup_cron.sh
```

- [ ] **Step 3: Test it (dry run — read the output)**

```bash
cd /home/m4stersun/travelplan && bash setup_cron.sh
```

Expected: "✅ Cron job installed: every 4 hours"

- [ ] **Step 4: Verify cron is installed**

```bash
crontab -l
```

Expected: shows the cron line with `src/main.py`

- [ ] **Step 5: Commit**

```bash
git add setup_cron.sh
git commit -m "feat: add cron setup script for 4-hour flight price checks"
```

---

## Task 8: LINE Messaging API Setup Guide + Integration Test

**Files:**
- Create: `docs/LINE_SETUP.md`

- [ ] **Step 1: Write the LINE setup guide**

```markdown
# LINE Messaging API Setup

## Step 1: Create a LINE Developers Account
1. Go to https://developers.line.biz/
2. Log in with your LINE account
3. Create a new Provider (e.g., "Flight Tracker")

## Step 2: Create a Messaging API Channel
1. Under your provider, click "Create a Messaging API channel"
2. Fill in: Channel name = "Flight Price Tracker", Description, Category = "Utility"
3. Agree to terms and create

## Step 3: Get Your Channel Access Token
1. Go to the "Messaging API" tab
2. Under "Channel access token", click "Issue"
3. Copy the long-lived token

## Step 4: Get Your User ID
1. Go to the "Basic settings" tab
2. Copy "Your user ID" (starts with U...)

## Step 5: Configure .env
```
LINE_CHANNEL_ACCESS_TOKEN=<paste your token>
LINE_USER_ID=<paste your user ID>
```

## Step 6: Add the Bot as Friend
1. In the "Messaging API" tab, find the QR code
2. Scan it with LINE to add the bot as a friend
3. The bot can now send you push messages

## Step 7: Test
```bash
cd /home/m4stersun/travelplan
python3 -c "
from src.notifier import send_line_notification
result = send_line_notification('🧪 Test message from Flight Tracker!')
print('Success!' if result else 'Failed — check your .env')
"
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/LINE_SETUP.md
git commit -m "docs: add LINE Messaging API setup guide"
```

---

## Task 9: End-to-End Manual Test

- [ ] **Step 1: Ensure .env has LINE credentials**

```bash
cat /home/m4stersun/travelplan/.env
```

Verify `LINE_CHANNEL_ACCESS_TOKEN` and `LINE_USER_ID` are set (not placeholder values).

- [ ] **Step 2: Run a single scrape manually**

```bash
cd /home/m4stersun/travelplan && python3 src/main.py
```

Expected output:
- Logs showing 4 route scrapes
- "LINE notification sent successfully" (if credentials set)
- CSV files created in `data/`
- SQLite DB created at `data/flights.db`

- [ ] **Step 3: Verify CSV output**

```bash
head -5 data/BKK-DAD-2026-05-29.csv
```

Expected: CSV header row + flight data rows

- [ ] **Step 4: Verify SQLite data**

```bash
sqlite3 data/flights.db "SELECT COUNT(*) FROM flights; SELECT COUNT(*) FROM scrape_runs;"
```

Expected: Non-zero counts

- [ ] **Step 5: Verify LINE notification received**

Check your LINE app — you should have received a formatted flight price message.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: end-to-end verification complete — flight tracker operational"
```

---

## Execution Notes

- **Task 0** must complete first (environment setup)
- **Tasks 1-5** can be executed in parallel (independent modules)
- **Task 6** depends on Tasks 1-5 (orchestrates all modules)
- **Task 7** depends on Task 6 (cron runs main.py)
- **Task 8** can run in parallel with Tasks 1-7 (just docs)
- **Task 9** depends on all previous tasks
