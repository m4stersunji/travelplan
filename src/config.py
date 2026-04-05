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

PREFERRED_DEPARTURE_START = "09:00"
PREFERRED_DEPARTURE_END = "12:00"

SEARCH_ROUTES = [
    {"origin": "BKK", "destination": "DAD", "date": "2026-05-29", "label": "BKK-DAD-May29"},
    {"origin": "BKK", "destination": "DAD", "date": "2026-05-30", "label": "BKK-DAD-May30"},
    {"origin": "DAD", "destination": "BKK", "date": "2026-06-01", "label": "DAD-BKK-Jun01"},
    {"origin": "DAD", "destination": "BKK", "date": "2026-06-02", "label": "DAD-BKK-Jun02"},
]
