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
    'Trip Name', 'From', 'To', 'Return From', 'Go Date', 'Back Date',
    'Prefer Depart', 'Prefer Arrive', 'Active', 'Added By', 'Status'
]

EXAMPLE_ROWS = [
    ['Danang', 'Bangkok', 'Danang', '', '2026-05-29', '2026-06-01', '12:00', '18:00', 'Yes', 'Owner', ''],
    ['Danang', 'Bangkok', 'Danang', '', '2026-05-30', '2026-06-02', '12:00', '18:00', 'Yes', 'Owner', ''],
    ['Osaka', 'Bangkok', 'Osaka', 'Tokyo', '2026-10-17', '2026-10-24', '10:00', '18:00', 'Yes', 'Owner', ''],
    ['Osaka', 'Bangkok', 'Osaka', 'Tokyo', '2026-10-17', '2026-10-25', '10:00', '18:00', 'Yes', 'Owner', ''],
    ['', '', '', '', '', '', '', '', '', '', ''],
    ['HOW TO ADD A TRIP:', '', '', '', '', '', '', '', '', '', ''],
    ['1. Trip Name = any name', '', '', '', '', '', '', '', '', '', ''],
    ['2. From/To = outbound cities', '', '', '', '', '', '', '', '', '', ''],
    ['3. Return From = leave blank if same as To, or set different city', '', '', '', '', '', '', '', '', '', ''],
    ['4. Go Date/Back Date = YYYY-MM-DD', '', '', '', '', '', '', '', '', '', ''],
    ['5. Prefer Depart/Arrive = time (10:00, 12:00, 18:00)', '', '', '', '', '', '', '', '', '', ''],
    ['6. Active = Yes or No', '', '', '', '', '', '', '', '', '', ''],
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
        statuses = []  # (row_idx, status) for writeback

        for row_num, row in enumerate(rows, start=2):  # +2: header + 0-index
            # Skip inactive, empty, or instruction rows
            active = str(row.get('Active', '')).strip().lower()
            if active not in ('yes', 'y', 'true', '1'):
                continue

            origin = str(row.get('From', '')).strip()
            destination = str(row.get('To', '')).strip()
            return_from = str(row.get('Return From', '')).strip()
            go_date = str(row.get('Go Date', '')).strip()
            back_date = str(row.get('Back Date', '')).strip()
            trip_name = str(row.get('Trip Name', '')).strip()
            prefer_depart = str(row.get('Prefer Depart', '12:00')).strip()
            prefer_arrive = str(row.get('Prefer Arrive', '18:00')).strip()

            # Return city: use "Return From" if set, otherwise same as "To"
            return_origin = return_from if return_from else destination

            if not origin or not destination or not go_date or not back_date:
                continue

            # Validate dates
            try:
                go_dt = datetime.strptime(go_date, '%Y-%m-%d')
                back_dt = datetime.strptime(back_date, '%Y-%m-%d')
            except ValueError:
                logger.warning(f"Invalid date format: {go_date} / {back_date}")
                statuses.append((row_num, f"Error: invalid date format"))
                continue

            if back_dt <= go_dt:
                logger.warning(f"Back date before go date: {go_date} → {back_date}")
                statuses.append((row_num, f"Error: return before departure"))
                continue

            # Build route code from first 3 chars of city name (simplified)
            origin_code = _city_to_code(origin)
            dest_code = _city_to_code(destination)
            return_code = _city_to_code(return_origin)
            route_code_out = f"{origin_code}-{dest_code}"
            route_code_back = f"{return_code}-{origin_code}"

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

            # Return (may be from different city, e.g., Tokyo instead of Osaka)
            search_routes.append({
                "origin": return_origin,
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

            # Mark as tracking
            now_str = datetime.now().strftime('%d %b %H:%M')
            statuses.append((row_num, f"Tracking (last: {now_str})"))

        if search_routes:
            # Deduplicate routes (same origin+destination+date)
            seen = set()
            unique_routes = []
            for r in search_routes:
                key = f"{r['origin']}|{r['destination']}|{r['date']}"
                if key not in seen:
                    seen.add(key)
                    unique_routes.append(r)

            # Write status back to Config tab
            if statuses:
                write_config_status(statuses)

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


def write_config_status(statuses):
    """Write status back to Config tab. statuses = list of (row_index, status_text)."""
    if not GOOGLE_SHEET_ID or not GOOGLE_CREDENTIALS_PATH:
        return
    try:
        gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_PATH)
        sh = gc.open_by_key(GOOGLE_SHEET_ID)
        ws = sh.worksheet('Config')
        # Status is column K (11) now with "Return From" added
        if ws.col_count < 11:
            ws.resize(cols=11)
        for row_idx, status_text in statuses:
            ws.update_acell(f'K{row_idx}', status_text)
        logger.info(f"Config status updated for {len(statuses)} trips")
    except Exception as e:
        logger.error(f"Failed to write config status: {e}")


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
