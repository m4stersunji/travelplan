import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'flights.db')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_USER_ID = os.getenv('LINE_USER_ID', '')

# Google Sheets
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', os.path.join(PROJECT_ROOT, 'credentials.json'))

# Only store top N cheapest flights per route/date
TOP_N_FLIGHTS = 20

# Auto-stop: scraper won't run after this date (1 month from now or set manually)
# Format: YYYY-MM-DD or empty string to disable
SCRAPER_EXPIRY_DATE = os.getenv('SCRAPER_EXPIRY_DATE', '2026-05-05')

EXCLUDED_AIRLINES = [
    "Emirates", "Qatar Airways", "Etihad", "Oman Air",
    "Saudia", "Gulf Air", "flynas", "Air Arabia",
]

# Use city names to include all airports (BKK Suvarnabhumi + DMK Don Mueang)
SEARCH_ROUTES = [
    # Danang
    {"origin": "Bangkok", "destination": "Danang", "date": "2026-05-29", "label": "BKK-DAD-May29", "route_code": "BKK-DAD", "trip_name": "Danang", "score_mode": "departure"},
    {"origin": "Bangkok", "destination": "Danang", "date": "2026-05-30", "label": "BKK-DAD-May30", "route_code": "BKK-DAD", "trip_name": "Danang", "score_mode": "departure"},
    {"origin": "Danang", "destination": "Bangkok", "date": "2026-06-01", "label": "DAD-BKK-Jun01", "route_code": "DAD-BKK", "trip_name": "Danang", "score_mode": "arrival"},
    {"origin": "Danang", "destination": "Bangkok", "date": "2026-06-02", "label": "DAD-BKK-Jun02", "route_code": "DAD-BKK", "trip_name": "Danang", "score_mode": "arrival"},
    # Osaka
    {"origin": "Bangkok", "destination": "Osaka", "date": "2026-10-17", "label": "BKK-KIX-Oct17", "route_code": "BKK-KIX", "trip_name": "Osaka", "score_mode": "departure"},
    {"origin": "Tokyo", "destination": "Bangkok", "date": "2026-10-24", "label": "TYO-BKK-Oct24", "route_code": "TYO-BKK", "trip_name": "Osaka", "score_mode": "arrival"},
    {"origin": "Tokyo", "destination": "Bangkok", "date": "2026-10-25", "label": "TYO-BKK-Oct25", "route_code": "TYO-BKK", "trip_name": "Osaka", "score_mode": "arrival"},
]

VALID_COMBOS = [
    ("2026-05-29", "2026-06-01"),  # Danang A: 29 May → 1 Jun
    ("2026-05-30", "2026-06-02"),  # Danang B: 30 May → 2 Jun
    ("2026-10-17", "2026-10-24"),  # Osaka A: 17 Oct → 24 Oct
    ("2026-10-17", "2026-10-25"),  # Osaka B: 17 Oct → 25 Oct
]
