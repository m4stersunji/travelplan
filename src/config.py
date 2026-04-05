import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'flights.db')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_USER_ID = os.getenv('LINE_USER_ID', '')

EXCLUDED_AIRLINES = [
    "Emirates", "Qatar Airways", "Etihad", "Oman Air",
    "Saudia", "Gulf Air", "flynas", "Air Arabia",
]

# Use city names to include all airports (BKK Suvarnabhumi + DMK Don Mueang)
SEARCH_ROUTES = [
    {"origin": "Bangkok", "destination": "Danang", "date": "2026-05-29", "label": "BKK-DAD-May29", "route_code": "BKK-DAD"},
    {"origin": "Bangkok", "destination": "Danang", "date": "2026-05-30", "label": "BKK-DAD-May30", "route_code": "BKK-DAD"},
    {"origin": "Danang", "destination": "Bangkok", "date": "2026-06-01", "label": "DAD-BKK-Jun01", "route_code": "DAD-BKK"},
    {"origin": "Danang", "destination": "Bangkok", "date": "2026-06-02", "label": "DAD-BKK-Jun02", "route_code": "DAD-BKK"},
]
