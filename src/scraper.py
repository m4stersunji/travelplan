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

        # Wait for flight results to render
        import time
        time.sleep(8)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='Thai baht']"))
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
        })

    logger.info(f"Parsed {len(flights)} unique flights from aria-labels")
    return flights


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
