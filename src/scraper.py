import re
import logging
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from lxml import html as lxml_html
    import cssselect
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

logger = logging.getLogger(__name__)


def build_google_flights_url(origin: str, destination: str, date: str) -> str:
    """Returns a Google Flights URL for the given origin, destination, and date."""
    return (
        f"https://www.google.com/travel/flights"
        f"?q=Flights+from+{origin}+to+{destination}+on+{date}+oneway"
        f"&curr=THB&hl=en"
    )


def create_driver():
    """Creates a headless Chrome Selenium WebDriver with anti-detection."""
    if not SELENIUM_AVAILABLE:
        raise RuntimeError("selenium is not installed")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    # Anti-detection: prevent Google from detecting headless/bot
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.7680.177 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    # Remove navigator.webdriver flag
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = {runtime: {}};
        """
    })
    driver.set_page_load_timeout(30)
    return driver


def scrape_flights(origin: str, destination: str, date: str) -> list:
    """
    Uses Selenium to load Google Flights and scrape flight data.
    Returns a list of flight dicts, or an empty list on failure.
    """
    if not SELENIUM_AVAILABLE:
        logger.error("selenium is not available")
        return []

    url = build_google_flights_url(origin, destination, date)
    import time

    # Retry up to 2 times if page fails to render
    for attempt in range(2):
        driver = None
        try:
            driver = create_driver()
            driver.get(url)
            time.sleep(8)

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Thai baht']"))
                )
            except TimeoutException:
                logger.warning("Timed out waiting for flight results")

            # Parse initial flights (ungrouped — typically 6-10 per airline)
            page_source = driver.page_source
            flights = parse_flight_data(page_source)

            if not flights and attempt < 1:
                logger.warning(f"No flights found (attempt {attempt + 1}), retrying...")
                driver.quit()
                time.sleep(3)
                continue

            # Get booking options for ALL flights
            if flights:
                _enrich_all_bookings(driver, flights)

            return flights

        except TimeoutException as exc:
            logger.error("Page load timed out: %s", exc)
            if attempt < 1:
                continue
            return []
        except WebDriverException as exc:
            logger.error("WebDriver error: %s", exc)
            return []
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass

    return []


def parse_flight_data(page_source: str) -> list:
    """
    Parses flight data from Google Flights HTML page source.
    Uses aria-label attributes which contain structured flight info like:
    'From 5335 Thai baht. Nonstop flight with Vietnam Airlines. Leaves ... at 6:05 PM ...
     arrives at ... 7:45 PM ... Total duration 1 hr 40 min.'
    Returns list of dicts with flight info keys.
    """
    if not page_source or not page_source.strip():
        return []

    # Extract flight details from aria-label attributes
    pattern = r'aria-label="From ([\d,]+) Thai baht\. ([^"]+)"'
    matches = re.findall(pattern, page_source)

    if not matches:
        logger.warning("No aria-label flight data found")
        return []

    flights = []
    seen = set()

    for price_str, details in matches:
        # Deduplicate — same flight appears multiple times in the HTML
        key = f"{price_str}|{details[:80]}"
        if key in seen:
            continue
        seen.add(key)

        price_thb = parse_price(price_str)

        # Extract stops: "Nonstop flight" or "1 stop flight"
        stops_match = re.match(r'(Nonstop|\d+\s*stop)\s*flight', details, re.IGNORECASE)
        num_stops = parse_stops(stops_match.group(1)) if stops_match else 0

        # Extract airline: "with Vietnam Airlines" or "with Cathay Pacific and Hong Kong Express"
        airline_match = re.search(r'with\s+(.+?)\.?\s*Leaves', details)
        airline = airline_match.group(1).strip() if airline_match else ''

        # Extract departure airport: "Leaves Don Mueang International Airport at" or "Leaves Suvarnabhumi Airport at"
        dep_airport_match = re.search(r'Leaves\s+(.+?)\s+at\s+\d', details)
        departure_airport = _short_airport(dep_airport_match.group(1)) if dep_airport_match else ''

        # Extract departure time: "at 6:05 PM on"
        dep_match = re.search(r'Leaves\s+.+?\s+at\s+(\d{1,2}:\d{2}\s*[AP]M)\s+on', details)
        departure_time = normalize_time(dep_match.group(1)) if dep_match else ''

        # Extract arrival airport: "arrives at Danang International Airport at"
        arr_airport_match = re.search(r'arrives\s+at\s+(.+?)\s+at\s+\d', details)
        arrival_airport = _short_airport(arr_airport_match.group(1)) if arr_airport_match else ''

        # Extract arrival time: "arrives at ... at 7:45 PM on"
        arr_match = re.search(r'arrives\s+at\s+.+?\s+at\s+(\d{1,2}:\d{2}\s*[AP]M)\s+on', details)
        arrival_time = normalize_time(arr_match.group(1)) if arr_match else ''

        # Extract duration: "Total duration 1 hr 40 min"
        dur_match = re.search(r'Total duration\s+(.+?)\.', details)
        duration_minutes = parse_duration(dur_match.group(1)) if dur_match else 0

        # Extract aircraft type if present in the details
        aircraft_type = extract_aircraft(details)

        cabin, checked, svc_type = get_baggage_info(airline)

        flights.append({
            "airline": airline,
            "flight_number": '',
            "departure_airport": departure_airport,
            "departure_time": departure_time,
            "arrival_airport": arrival_airport,
            "arrival_time": arrival_time,
            "duration_minutes": duration_minutes,
            "price_thb": price_thb,
            "aircraft_type": aircraft_type,
            "num_stops": num_stops,
            "cabin_baggage": cabin,
            "checked_baggage": checked,
            "service_type": svc_type,
        })

    logger.info(f"Parsed {len(flights)} unique flights from aria-labels")
    return flights


def _enrich_all_bookings(driver, flights):
    """Get 3rd party booking prices for ALL flights.
    Reloads page between clicks since DOM doesn't recover after toggling.
    """
    import time

    url = driver.current_url
    checked = 0

    for flight in flights:
        price = flight['price_thb']
        dep_time_12h = _to_12h(flight.get('departure_time', ''))
        if not dep_time_12h:
            continue

        try:
            # Reload page fresh for each flight
            if checked > 0:
                driver.get(url)
                time.sleep(5)
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Thai baht']"))
                    )
                except TimeoutException:
                    continue

            js = f'''
            var links = document.querySelectorAll('[role="link"][aria-label*="{price} Thai baht"]');
            for (var l of links) {{
                if (l.getAttribute('aria-label').includes('{dep_time_12h}')) {{
                    l.click();
                    return true;
                }}
            }}
            return false;
            '''
            clicked_ok = driver.execute_script(js)
            if not clicked_ok:
                continue

            time.sleep(2.5)

            # Expand "more booking options"
            try:
                more = driver.find_elements(By.XPATH, '//*[contains(text(), "more booking options")]')
                for btn in more:
                    driver.execute_script('arguments[0].click();', btn)
                    time.sleep(1)
            except Exception:
                pass

            body_text = driver.find_element(By.TAG_NAME, 'body').text
            bookings = _parse_booking_text(body_text)

            if bookings:
                cheapest = min(bookings, key=lambda x: x[1])
                flight['booking_options'] = bookings
                flight['best_booking_price'] = cheapest[1]
                flight['best_booking_source'] = cheapest[0]
                checked += 1

        except Exception as e:
            logger.debug(f"Booking check failed for {flight.get('airline')}: {e}")

    logger.info(f"Booking data: {checked}/{len(flights)} flights enriched")


def _get_booking_data(driver, flights):
    """Get 3rd party booking prices for ALL flights.
    Called BEFORE expanding groups (cleaner DOM = more booking sources).
    Returns dict keyed by 'airline|price' with booking fields.
    """
    import time
    result = {}

    # Check all flights, sorted by price (cheapest first)
    to_check = sorted(flights, key=lambda f: f['price_thb'])

    for flight in to_check:
        price = flight['price_thb']
        dep_time_12h = _to_12h(flight.get('departure_time', ''))
        if not dep_time_12h:
            continue

        # Skip if we already have data for same airline+price
        key = f"{flight['airline']}|{price}"
        if key in result:
            continue

        try:
            js = f'''
            var links = document.querySelectorAll('[role="link"][aria-label*="{price} Thai baht"]');
            for (var l of links) {{
                if (l.getAttribute('aria-label').includes('{dep_time_12h}')) {{
                    l.click();
                    return true;
                }}
            }}
            return false;
            '''
            clicked = driver.execute_script(js)
            if not clicked:
                continue

            time.sleep(2)

            # Expand "more booking options"
            try:
                more = driver.find_elements(By.XPATH, '//*[contains(text(), "more booking options")]')
                for btn in more:
                    driver.execute_script('arguments[0].click();', btn)
                    time.sleep(1)
            except Exception:
                pass

            body_text = driver.find_element(By.TAG_NAME, 'body').text
            bookings = _parse_booking_text(body_text)

            if bookings:
                cheapest = min(bookings, key=lambda x: x[1])
                key = f"{flight['airline']}|{price}"
                result[key] = {
                    'booking_options': bookings,
                    'best_booking_price': cheapest[1],
                    'best_booking_source': cheapest[0],
                }
                logger.info(f"Booking: {flight['airline']} ฿{price:,} → best ฿{cheapest[1]:,} via {cheapest[0]} ({len(bookings)} sources)")

            # Close panel
            driver.execute_script(js)
            time.sleep(1)

        except Exception as e:
            logger.debug(f"Booking check failed for {flight.get('airline')}: {e}")

    return result


def _enrich_booking_options(driver, flights):
    """Click top direct flights to get 3rd party booking prices.
    Enriches flight dicts with 'booking_options' and 'best_booking_price'.
    """
    import time

    # Sort by price, get top 3 direct non-excluded flights to check
    direct = [f for f in flights if f.get('num_stops', 1) == 0]
    direct.sort(key=lambda f: f['price_thb'])
    to_check = direct[:3]

    for flight in to_check:
        price = flight['price_thb']
        dep_time_12h = _to_12h(flight.get('departure_time', ''))
        if not dep_time_12h:
            continue

        try:
            # Find and click the flight link using JS
            js = f'''
            var links = document.querySelectorAll('[role="link"][aria-label*="{price} Thai baht"]');
            for (var l of links) {{
                var label = l.getAttribute('aria-label') || '';
                if (label.includes('{dep_time_12h}')) {{
                    l.click();
                    return true;
                }}
            }}
            return false;
            '''
            clicked = driver.execute_script(js)
            if not clicked:
                continue

            time.sleep(3)

            # Expand "more booking options" if available
            try:
                more = driver.find_elements(By.XPATH, '//*[contains(text(), "more booking options")]')
                for btn in more:
                    driver.execute_script('arguments[0].click();', btn)
                    time.sleep(1.5)
            except Exception:
                pass

            # Extract booking options from visible text
            body_text = driver.find_element(By.TAG_NAME, 'body').text
            bookings = _parse_booking_text(body_text)

            if bookings:
                flight['booking_options'] = bookings
                cheapest = min(bookings, key=lambda x: x[1])
                flight['best_booking_price'] = cheapest[1]
                flight['best_booking_source'] = cheapest[0]
                logger.info(f"Booking: {flight['airline']} ฿{price:,} → best ฿{cheapest[1]:,} via {cheapest[0]}")

            # Toggle close by clicking same element again
            driver.execute_script(js)
            time.sleep(1)

        except Exception as e:
            logger.debug(f"Booking check failed for {flight.get('airline')}: {e}")
            continue


def _parse_booking_text(body_text):
    """Parse 'Book with X / THB Y' pairs from page text."""
    lines = body_text.split('\n')
    bookings = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('Book with ') or line.startswith('Book on '):
            source = line.replace('Book with ', '').replace('Book on ', '').replace('Airline', '').strip()
            for j in range(i + 1, min(i + 5, len(lines))):
                nxt = lines[j].strip()
                if nxt.startswith('Includes'):
                    continue
                pm = re.match(r'THB ([\d,]+)', nxt)
                if pm:
                    bookings.append((source, int(pm.group(1).replace(',', ''))))
                    break
        i += 1
    return bookings


def _to_12h(time_24h):
    """Convert '07:50' to '7:50 AM' for matching Google Flights labels."""
    if not time_24h:
        return ''
    try:
        h, m = time_24h.split(':')
        h = int(h)
        period = 'AM' if h < 12 else 'PM'
        if h == 0:
            h = 12
        elif h > 12:
            h -= 12
        return f'{h}:{m} {period}'
    except (ValueError, AttributeError):
        return ''


def _expand_flight_groups(driver):
    """Click to expand grouped flights on Google Flights.
    Google groups flights by airline — clicking expands to show all departure times.
    """
    import time
    try:
        # Find expandable flight rows and click them
        expandable = driver.find_elements(
            By.CSS_SELECTOR,
            '[aria-label*="Thai baht"][role="button"], [aria-expanded="false"][aria-label*="flight"]'
        )
        for el in expandable[:10]:  # Limit to avoid infinite clicking
            try:
                el.click()
                time.sleep(0.5)
            except Exception:
                continue
        time.sleep(2)
    except Exception as e:
        logger.debug(f"Expand groups failed (non-fatal): {e}")


# Airline baggage info: (cabin_kg, checked_kg, note)
AIRLINE_BAGGAGE = {
    "thai airasia": ("7kg carry-on", "No checked bag", "Budget"),
    "airasia": ("7kg carry-on", "No checked bag", "Budget"),
    "vietjet": ("7kg carry-on", "No checked bag", "Budget"),
    "vietnam airlines": ("10kg carry-on", "23kg checked", "Full service"),
    "emirates": ("7kg carry-on", "30kg checked", "Full service"),
    "cathay pacific": ("7kg carry-on", "25kg checked", "Full service"),
    "malaysia airlines": ("7kg carry-on", "25kg checked", "Full service"),
    "philippine airlines": ("7kg carry-on", "25kg checked", "Full service"),
    "batik air": ("7kg carry-on", "20kg checked", "Full service"),
    "thai": ("7kg carry-on", "30kg checked", "Full service"),
    "bangkok airways": ("7kg carry-on", "20kg checked", "Full service"),
    "china airlines": ("7kg carry-on", "23kg checked", "Full service"),
    "eva air": ("7kg carry-on", "23kg checked", "Full service"),
    "jeju air": ("10kg carry-on", "No checked bag", "Budget"),
}


def get_baggage_info(airline_name):
    """Look up baggage allowance for an airline. Returns (cabin, checked, type)."""
    name_lower = airline_name.lower().strip()
    # Try exact match first, then partial
    for key, info in AIRLINE_BAGGAGE.items():
        if key in name_lower:
            return info
    return ("7kg carry-on", "Check airline", "Unknown")


def classify_flight(flight, excluded_airlines):
    """
    Adds classification flags to a flight dict:
      - is_direct: True if num_stops == 0
      - is_excluded_airline: True if airline contains any excluded airline name
    Returns the same dict (mutated) with new keys.
    """
    flight["is_direct"] = flight.get("num_stops", 1) == 0

    airline_name = flight.get("airline", "")
    flight["is_excluded_airline"] = any(
        excl.lower() in airline_name.lower()
        for excl in excluded_airlines
    )

    return flight


AIRPORT_SHORT = {
    "Suvarnabhumi Airport": "BKK",
    "Don Mueang International Airport": "DMK",
    "Danang International Airport": "DAD",
    "Da Nang International Airport": "DAD",
}


def _short_airport(full_name):
    """Convert full airport name to short code."""
    for name, code in AIRPORT_SHORT.items():
        if name.lower() in full_name.lower():
            return code
    # Fallback: take first 3 chars
    return full_name[:3] if full_name else ''


def normalize_time(time_str: str) -> str:
    """
    Converts "10:15 AM" or "2:30 PM" to "HH:MM" 24-hour format.
    Returns empty string for empty/invalid input.
    """
    if not time_str or not time_str.strip():
        return ""

    time_str = time_str.strip()
    for fmt in ("%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(time_str.upper(), fmt).strftime("%H:%M")
        except ValueError:
            continue

    # Already 24h format or unrecognised — return as-is if it looks like HH:MM
    if re.match(r'^\d{1,2}:\d{2}$', time_str):
        return time_str

    return ""


def parse_duration(text: str) -> int:
    """
    Parses "2 hr 15 min" (or similar) into total integer minutes.
    Examples: "2 hr 15 min" -> 135, "1 hr" -> 60, "45 min" -> 45.
    """
    if not text:
        return 0

    hours = 0
    minutes = 0

    hr_match = re.search(r'(\d+)\s*hr', text, re.IGNORECASE)
    min_match = re.search(r'(\d+)\s*min', text, re.IGNORECASE)

    if hr_match:
        hours = int(hr_match.group(1))
    if min_match:
        minutes = int(min_match.group(1))

    return hours * 60 + minutes


def parse_price(text: str) -> int:
    """
    Parses "฿3,250" or "3,250" into an integer.
    Strips all non-digit characters.
    """
    if not text:
        return 0
    digits = re.sub(r'[^\d]', '', str(text))
    return int(digits) if digits else 0


def parse_stops(text: str) -> int:
    """
    Parses stop descriptions into an integer count.
    "Nonstop" -> 0, "1 stop" -> 1, "2 stops" -> 2, etc.
    """
    if not text:
        return 0
    text_lower = text.lower().strip()
    if "nonstop" in text_lower:
        return 0
    match = re.search(r'(\d+)', text_lower)
    return int(match.group(1)) if match else 0


def extract_aircraft(text: str) -> str:
    """
    Extracts aircraft type from text using regex.
    Recognises: A320, 737-800, 787, ATR 72, CRJ-900, E190, etc.
    Returns empty string if none found.
    """
    if not text:
        return ""

    patterns = [
        r'\bATR\s*\d+\b',
        r'\bCRJ[-\s]?\d+\b',
        r'\bE\d{3}\b',
        r'\b7[3478]\d[-\s]?\d{3,4}\b',
        r'\b7[3478]\d\b',
        r'\bA\d{3}(?:neo|XLR|[-\s]?\d{3})?\b',
        r'\b787\b',
        r'\b777\b',
        r'\b767\b',
        r'\b757\b',
        r'\b747\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return ""


def score_flights(flights, route_direction='outbound', ideal_hour=None, score_mode=None):
    """Score flights by price (0-10) and time preference (0-10).

    Args:
        flights: list of flight dicts
        route_direction: 'outbound' or 'return' (fallback if no score_mode)
        ideal_hour: preferred time as float (e.g., 12.0 = noon), from Config sheet
        score_mode: 'departure' or 'arrival' — which time to score

    Returns flights with 'price_score', 'time_score', 'total_score' added.
    """
    if not flights:
        return flights

    # Defaults
    if ideal_hour is None:
        ideal_hour = 12.0 if route_direction == 'outbound' else 18.0
    if score_mode is None:
        score_mode = 'departure' if route_direction == 'outbound' else 'arrival'

    # Price score: cheapest gets 10, most expensive gets 0
    prices = [f['price_thb'] for f in flights if f['price_thb'] > 0]
    if not prices:
        return flights
    min_p = min(prices)
    max_p = max(prices)
    price_range = max_p - min_p if max_p > min_p else 1

    for f in flights:
        # Price score
        if f['price_thb'] > 0:
            actual_price = f.get('best_booking_price') or f['price_thb']
            f['price_score'] = round(10 * (1 - (actual_price - min_p) / price_range), 1)
            f['price_score'] = max(0, min(10, f['price_score']))
        else:
            f['price_score'] = 0

        # Time score
        f['time_score'] = _calc_time_score(f, score_mode, ideal_hour)

        # Total score
        f['total_score'] = round(f['price_score'] + f['time_score'], 1)

    return flights


def _calc_time_score(flight, score_mode, ideal_hour):
    """Calculate time preference score (0-10) using bell curve.

    score_mode: 'departure' scores departure_time, 'arrival' scores arrival_time
    ideal_hour: target time as float (12.0 = noon, 18.0 = 6pm)
    """
    import math

    time_str = flight.get('departure_time', '') if score_mode == 'departure' else flight.get('arrival_time', '')

    if not time_str:
        return 0

    try:
        h, m = time_str.split(':')
        hour = int(h) + int(m) / 60.0
    except (ValueError, AttributeError):
        return 0

    # Bell curve: ±3 hours from ideal still gets decent score
    diff = abs(hour - ideal_hour)
    sigma = 3.0
    score = 10 * math.exp(-(diff ** 2) / (2 * sigma ** 2))
    return round(score, 1)

    return ""
