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
    """Creates a headless Chrome Selenium WebDriver with standard options."""
    if not SELENIUM_AVAILABLE:
        raise RuntimeError("selenium is not installed")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
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
    driver = None
    try:
        driver = create_driver()
        driver.get(url)

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ved]"))
            )
        except TimeoutException:
            logger.warning("Timed out waiting for flight results to load; parsing what we have")

        page_source = driver.page_source
        return parse_flight_data(page_source)

    except TimeoutException as exc:
        logger.error("Page load timed out: %s", exc)
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


def parse_flight_data(page_source: str) -> list:
    """
    Parses flight data from HTML page source.
    Tries lxml/cssselect first, falls back to regex.
    Returns list of dicts with flight info keys.
    """
    if not page_source or not page_source.strip():
        return []

    if LXML_AVAILABLE:
        try:
            return _parse_with_lxml(page_source)
        except Exception as exc:
            logger.warning("lxml parsing failed (%s), falling back to regex", exc)

    return parse_flight_data_regex(page_source)


def _parse_with_lxml(page_source: str) -> list:
    """
    Attempts to parse flight data using lxml and cssselect.
    Google Flights renders heavily via JS, so this may return an empty list
    if the static HTML doesn't contain rendered flight cards.
    """
    tree = lxml_html.fromstring(page_source)

    # Google Flights flight result containers (class names can vary by version)
    flight_cards = (
        tree.cssselect("li.pIav2d")
        or tree.cssselect("div.yR1LTd")
        or tree.cssselect("[data-ved] li")
    )

    if not flight_cards:
        # Fall through to regex if no structured nodes found
        return parse_flight_data_regex(page_source)

    flights = []
    for card in flight_cards:
        text = card.text_content()

        # Extract price
        price_match = re.search(r'[฿\$]?([\d,]+)', text)
        price_thb = parse_price(price_match.group(0)) if price_match else 0

        # Extract times — first two HH:MM AM/PM occurrences
        times = re.findall(r'\d{1,2}:\d{2}\s*(?:AM|PM)', text, re.IGNORECASE)
        departure_time = normalize_time(times[0]) if len(times) > 0 else ""
        arrival_time = normalize_time(times[1]) if len(times) > 1 else ""

        # Duration
        dur_match = re.search(r'(\d+)\s*hr\s*(\d+)?\s*min?', text, re.IGNORECASE)
        duration_minutes = parse_duration(dur_match.group(0)) if dur_match else 0

        # Airline name — first text node or prominent span
        airline_nodes = card.cssselect(".sSHqwe") or card.cssselect(".h1fkLb")
        airline = airline_nodes[0].text_content().strip() if airline_nodes else ""

        # Flight number
        fn_match = re.search(r'[A-Z]{2}\s*\d{1,4}', text)
        flight_number = fn_match.group(0).replace(" ", "") if fn_match else ""

        # Stops
        stops_match = re.search(r'Nonstop|\d+\s*stop', text, re.IGNORECASE)
        num_stops = parse_stops(stops_match.group(0)) if stops_match else 0

        # Aircraft
        aircraft_type = extract_aircraft(text)

        flights.append({
            "airline": airline,
            "flight_number": flight_number,
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "duration_minutes": duration_minutes,
            "price_thb": price_thb,
            "aircraft_type": aircraft_type,
            "num_stops": num_stops,
        })

    return flights


def parse_flight_data_regex(page_source: str) -> list:
    """
    Regex fallback parser. Extracts prices matching ฿X,XXX and times matching HH:MM AM/PM.
    Returns a best-effort list of flight dicts.
    """
    if not page_source or not page_source.strip():
        return []

    prices = re.findall(r'฿[\d,]+', page_source)
    times = re.findall(r'\d{1,2}:\d{2}\s*(?:AM|PM)', page_source, re.IGNORECASE)

    flights = []
    for i, price_str in enumerate(prices):
        dep_idx = i * 2
        arr_idx = i * 2 + 1
        departure_time = normalize_time(times[dep_idx]) if dep_idx < len(times) else ""
        arrival_time = normalize_time(times[arr_idx]) if arr_idx < len(times) else ""

        flights.append({
            "airline": "",
            "flight_number": "",
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "duration_minutes": 0,
            "price_thb": parse_price(price_str),
            "aircraft_type": "",
            "num_stops": 0,
        })

    return flights


def classify_flight(
    flight: dict,
    excluded_airlines: list,
    pref_dep_start: str,
    pref_dep_end: str,
) -> dict:
    """
    Adds classification boolean flags to a flight dict:
      - is_direct: True if num_stops == 0
      - is_excluded_airline: True if airline contains any excluded airline name
      - is_preferred_time: True if departure_time is between pref_dep_start and pref_dep_end (inclusive)
    Returns the same dict (mutated) with new keys.
    """
    flight["is_direct"] = flight.get("num_stops", 1) == 0

    airline_name = flight.get("airline", "")
    flight["is_excluded_airline"] = any(
        excl.lower() in airline_name.lower()
        for excl in excluded_airlines
    )

    dep_time_str = flight.get("departure_time", "")
    try:
        dep_time = datetime.strptime(dep_time_str, "%H:%M").time()
        start_time = datetime.strptime(pref_dep_start, "%H:%M").time()
        end_time = datetime.strptime(pref_dep_end, "%H:%M").time()
        flight["is_preferred_time"] = start_time <= dep_time <= end_time
    except (ValueError, TypeError):
        flight["is_preferred_time"] = False

    return flight


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
