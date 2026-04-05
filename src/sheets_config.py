"""Read trip configuration from Google Sheets 'Config' tab.

Friends can add trips by editing the Config tab — no code needed.
Falls back to config.py SEARCH_ROUTES if Sheet config fails.
"""
import logging
import gspread
from datetime import datetime

from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_PATH

logger = logging.getLogger(__name__)

CONFIG_HEADERS = [
    'Trip Name', 'From', 'To', 'Go Date', 'Back Date',
    'Prefer Depart', 'Prefer Arrive', 'Active', 'Added By'
]

EXAMPLE_ROWS = [
    ['Danang', 'Bangkok', 'Danang', '2026-05-29', '2026-06-01', '12:00', '18:00', 'Yes', 'Owner'],
    ['Danang', 'Bangkok', 'Danang', '2026-05-30', '2026-06-02', '12:00', '18:00', 'Yes', 'Owner'],
    ['', '', '', '', '', '', '', '', ''],
    ['HOW TO ADD A TRIP:', '', '', '', '', '', '', '', ''],
    ['1. Add a new row above this line', '', '', '', '', '', '', '', ''],
    ['2. Trip Name = any name', '', '', '', '', '', '', '', ''],
    ['3. From/To = city name (Bangkok, Tokyo, Osaka, Danang, Seoul, Singapore...)', '', '', '', '', '', '', '', ''],
    ['4. Go Date/Back Date = YYYY-MM-DD', '', '', '', '', '', '', '', ''],
    ['5. Prefer Depart = best departure time for outbound (e.g., 12:00 = noon)', '', '', '', '', '', '', '', ''],
    ['6. Prefer Arrive = best arrival time for return (e.g., 18:00 = 6pm)', '', '', '', '', '', '', '', ''],
    ['7. Active = Yes or No', '', '', '', '', '', '', '', ''],
    ['8. Added By = your name', '', '', '', '', '', '', '', ''],
]


def init_config_sheet(spreadsheet):
    """Create the Config tab with headers and example data if it doesn't exist."""
    try:
        ws = spreadsheet.worksheet('Config')
        existing = ws.row_values(1)
        if not existing:
            ws.update('A1', [CONFIG_HEADERS] + EXAMPLE_ROWS)
            _format_config_sheet(ws)
        return ws
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title='Config', rows=50, cols=len(CONFIG_HEADERS))
        ws.update('A1', [CONFIG_HEADERS] + EXAMPLE_ROWS)
        _format_config_sheet(ws)
        return ws


def _format_config_sheet(ws):
    """Format the Config sheet to look nice."""
    # Bold headers with background
    ws.format('A1:G1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
        'textFormat': {'bold': True, 'foregroundColorStyle': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}},
    })
    # Set column widths hint via frozen rows
    ws.freeze(rows=1)


def load_routes_from_sheet():
    """Load trip config from Google Sheets Config tab.

    Returns (search_routes, valid_combos) or (None, None) if unavailable.
    """
    if not GOOGLE_SHEET_ID or not GOOGLE_CREDENTIALS_PATH:
        return None, None

    try:
        gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_PATH)
        sh = gc.open_by_key(GOOGLE_SHEET_ID)

        # Ensure Config tab exists
        ws = init_config_sheet(sh)

        # Read all rows
        rows = ws.get_all_records()

        search_routes = []
        valid_combos = []

        for row in rows:
            # Skip inactive, empty, or instruction rows
            active = str(row.get('Active', '')).strip().lower()
            if active not in ('yes', 'y', 'true', '1'):
                continue

            origin = str(row.get('From', '')).strip()
            destination = str(row.get('To', '')).strip()
            go_date = str(row.get('Go Date', '')).strip()
            back_date = str(row.get('Back Date', '')).strip()
            trip_name = str(row.get('Trip Name', '')).strip()
            prefer_depart = str(row.get('Prefer Depart', '12:00')).strip()
            prefer_arrive = str(row.get('Prefer Arrive', '18:00')).strip()

            if not origin or not destination or not go_date or not back_date:
                continue

            # Validate dates
            try:
                go_dt = datetime.strptime(go_date, '%Y-%m-%d')
                back_dt = datetime.strptime(back_date, '%Y-%m-%d')
            except ValueError:
                logger.warning(f"Invalid date format in Config: {go_date} / {back_date} — skipping")
                continue

            if back_dt <= go_dt:
                logger.warning(f"Back date must be after go date: {go_date} → {back_date} — skipping")
                continue

            # Build route code from first 3 chars of city name (simplified)
            origin_code = _city_to_code(origin)
            dest_code = _city_to_code(destination)
            route_code_out = f"{origin_code}-{dest_code}"
            route_code_back = f"{dest_code}-{origin_code}"

            go_label = go_dt.strftime('%d %b')
            back_label = back_dt.strftime('%d %b')

            # Parse preferred times to float hours
            depart_hour = _parse_time_pref(prefer_depart, 12.0)
            arrive_hour = _parse_time_pref(prefer_arrive, 18.0)

            # Outbound
            search_routes.append({
                "origin": origin,
                "destination": destination,
                "date": go_date,
                "label": f"{route_code_out}-{go_label.replace(' ', '')}",
                "route_code": route_code_out,
                "trip_name": trip_name,
                "ideal_hour": depart_hour,
                "score_mode": "departure",
            })

            # Return
            search_routes.append({
                "origin": destination,
                "destination": origin,
                "date": back_date,
                "label": f"{route_code_back}-{back_label.replace(' ', '')}",
                "route_code": route_code_back,
                "trip_name": trip_name,
                "ideal_hour": arrive_hour,
                "score_mode": "arrival",
            })

            # Valid combo
            valid_combos.append((go_date, back_date))

        if search_routes:
            # Deduplicate routes (same origin+destination+date)
            seen = set()
            unique_routes = []
            for r in search_routes:
                key = f"{r['origin']}|{r['destination']}|{r['date']}"
                if key not in seen:
                    seen.add(key)
                    unique_routes.append(r)

            logger.info(f"Loaded {len(unique_routes)} routes and {len(valid_combos)} combos from Config sheet")
            return unique_routes, valid_combos

        return None, None

    except Exception as e:
        logger.error(f"Failed to load config from Sheets: {e}")
        return None, None


CITY_CODES = {
    'bangkok': 'BKK',
    'danang': 'DAD',
    'da nang': 'DAD',
    'tokyo': 'TYO',
    'osaka': 'KIX',
    'seoul': 'ICN',
    'singapore': 'SIN',
    'hong kong': 'HKG',
    'taipei': 'TPE',
    'kuala lumpur': 'KUL',
    'ho chi minh': 'SGN',
    'hanoi': 'HAN',
    'bali': 'DPS',
    'phuket': 'HKT',
    'chiang mai': 'CNX',
}


def _parse_time_pref(time_str, default=12.0):
    """Parse '12:00' or '18:30' to float hours (12.0, 18.5)."""
    try:
        h, m = time_str.split(':')
        return int(h) + int(m) / 60.0
    except (ValueError, AttributeError):
        return default


def _city_to_code(city_name):
    """Convert city name to 3-letter code."""
    name_lower = city_name.lower().strip()
    for city, code in CITY_CODES.items():
        if city in name_lower:
            return code
    # Fallback: first 3 uppercase chars
    return city_name[:3].upper()
