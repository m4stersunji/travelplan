import logging
import gspread
from datetime import datetime

from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_PATH

logger = logging.getLogger(__name__)


def get_sheets_client():
    """Connect to Google Sheets."""
    if not GOOGLE_SHEET_ID or not GOOGLE_CREDENTIALS_PATH:
        logger.warning("Google Sheets not configured — skipping")
        return None, None
    try:
        gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_PATH)
        sh = gc.open_by_key(GOOGLE_SHEET_ID)
        return gc, sh
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        return None, None


def _get_or_create_sheet(spreadsheet, title, headers):
    """Get or create a worksheet with headers."""
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
    # Set headers if row 1 is empty
    existing = ws.row_values(1)
    if not existing:
        ws.update('A1', [headers])
        ws.format('A1:Z1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})
    return ws


def push_to_sheets(route_results):
    """Push flight data to Google Sheets.

    Creates/updates these sheets:
    - Overview: best prices summary
    - All Flights: full sortable table
    - Price History: trend data for charts
    - Heatmap: cheapest price per date
    """
    gc, sh = get_sheets_client()
    if not sh:
        return False

    success = True
    for name, fn in [
        ('Overview', _update_overview),
        ('All Flights', _update_all_flights),
        ('Price History', _update_price_history),
        ('Heatmap', _update_heatmap),
    ]:
        try:
            fn(sh, route_results)
            logger.info(f"Sheets: {name} updated")
        except Exception as e:
            logger.error(f"Sheets: {name} failed: {e}")
            success = False

    return success


def _update_overview(sh, route_results):
    """Overview sheet — summary of best prices and combos."""
    headers = ['Route', 'Date', 'Cheapest Airline', 'Airline Price', 'Best 3rd Party', 'Best Price', 'Best Source', 'Last Check']
    ws = _get_or_create_sheet(sh, 'Overview', headers)

    rows = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    for r in route_results:
        if not r.get('flights'):
            continue

        # Find cheapest direct non-excluded
        direct = [f for f in r['flights'] if f.get('is_direct') and not f.get('is_excluded_airline') and f['price_thb'] > 0]
        if not direct:
            continue

        cheapest = min(direct, key=lambda f: f['price_thb'])
        best_bp = cheapest.get('best_booking_price', '')
        best_src = cheapest.get('best_booking_source', '')

        rows.append([
            r['route'],
            r['date_label'],
            cheapest['airline'],
            cheapest['price_thb'],
            best_src,
            best_bp if best_bp is not None else cheapest['price_thb'],
            best_src if best_src else 'Airline direct',
            now,
        ])

    # Add best combo row
    outbound = [r for r in route_results if r['route'].startswith('BKK')]
    inbound = [r for r in route_results if r['route'].startswith('DAD')]
    combo = _find_best_combo(outbound, inbound)
    if combo:
        rows.append([])
        rows.append(['BEST ROUNDTRIP', '', '', '', '', combo['total'], f"{combo['out_date']} + {combo['in_date']}", now])

    # Clear and rewrite (overview is always current snapshot)
    ws.clear()
    ws.update('A1', [headers] + rows)
    ws.format('A1:H1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})


def _update_all_flights(sh, route_results):
    """All Flights sheet — full table, appended each run."""
    headers = [
        'Checked At', 'Route', 'Date', 'Airline', 'Departure Airport', 'Departure Time',
        'Arrival Airport', 'Arrival Time', 'Duration (min)', 'Airline Price (THB)',
        'Best Booking Price', 'Best Booking Source', 'Aircraft', 'Stops',
        'Direct?', 'Excluded?', 'Cabin Baggage', 'Checked Baggage', 'Service Type'
    ]
    ws = _get_or_create_sheet(sh, 'All Flights', headers)

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    rows = []

    for r in route_results:
        flights = sorted(r.get('flights', []), key=lambda f: f['price_thb'])
        for f in flights:
            rows.append([
                now,
                r['route'],
                r['date_label'],
                f.get('airline', ''),
                f.get('departure_airport', ''),
                f.get('departure_time', ''),
                f.get('arrival_airport', ''),
                f.get('arrival_time', ''),
                f.get('duration_minutes', ''),
                f.get('price_thb', ''),
                f.get('best_booking_price', ''),
                f.get('best_booking_source', ''),
                f.get('aircraft_type', ''),
                f.get('num_stops', ''),
                'Yes' if f.get('is_direct') else 'No',
                'Yes' if f.get('is_excluded_airline') else 'No',
                f.get('cabin_baggage', ''),
                f.get('checked_baggage', ''),
                f.get('service_type', ''),
            ])

    if rows:
        # Append after existing data
        existing = ws.get_all_values()
        next_row = len(existing) + 1
        ws.update(f'A{next_row}', rows)


def _update_price_history(sh, route_results):
    """Price History sheet — one row per check with best prices per route. Chart-friendly."""
    headers = ['Checked At']
    for r in route_results:
        label = f"{r['route']} {r['date_label']}"
        headers.append(f"{label} (Airline)")
        headers.append(f"{label} (Best 3rd)")

    ws = _get_or_create_sheet(sh, 'Price History', headers)

    # Validate headers match (routes may have changed)
    existing_headers = ws.row_values(1)
    if existing_headers and existing_headers != headers:
        logger.warning("Price History headers changed — updating row 1")
        ws.update('A1', [headers])

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    row = [now]

    for r in route_results:
        direct = [f for f in r.get('flights', []) if f.get('is_direct') and not f.get('is_excluded_airline') and f['price_thb'] > 0]
        if direct:
            cheapest = min(direct, key=lambda f: f['price_thb'])
            row.append(cheapest['price_thb'])
            row.append(cheapest.get('best_booking_price', cheapest['price_thb']))
        else:
            row.append('')
            row.append('')

    existing = ws.get_all_values()
    next_row = len(existing) + 1
    ws.update(f'A{next_row}', [row])


def _update_heatmap(sh, route_results):
    """Heatmap sheet — cheapest price per route/date combo. Updates in place."""
    headers = ['Route', 'Date', 'Cheapest (Airline)', 'Cheapest (Any Source)', 'Airline', 'Source', 'Last Updated']
    ws = _get_or_create_sheet(sh, 'Heatmap', headers)

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    rows = []

    for r in route_results:
        direct = [f for f in r.get('flights', []) if f.get('is_direct') and not f.get('is_excluded_airline') and f['price_thb'] > 0]
        if not direct:
            continue
        cheapest = min(direct, key=lambda f: f['price_thb'])
        best_bp = cheapest.get('best_booking_price', cheapest['price_thb'])
        best_src = cheapest.get('best_booking_source', 'Airline direct')

        rows.append([
            r['route'],
            r['date_label'],
            cheapest['price_thb'],
            best_bp if best_bp is not None else cheapest['price_thb'],
            cheapest['airline'],
            best_src,
            now,
        ])

    # Overwrite heatmap (always current)
    ws.clear()
    ws.update('A1', [headers] + rows)
    ws.format('A1:G1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})


def _find_best_combo(outbound, inbound):
    """Find cheapest roundtrip."""
    combos = []
    for out_r in outbound:
        out_direct = [f for f in out_r.get('flights', []) if f.get('is_direct') and not f.get('is_excluded_airline') and f['price_thb'] > 0]
        if not out_direct:
            continue
        best_out = min(out_direct, key=lambda f: f.get('best_booking_price', f['price_thb']) or f['price_thb'])

        for in_r in inbound:
            in_direct = [f for f in in_r.get('flights', []) if f.get('is_direct') and not f.get('is_excluded_airline') and f['price_thb'] > 0]
            if not in_direct:
                continue
            best_in = min(in_direct, key=lambda f: f.get('best_booking_price', f['price_thb']) or f['price_thb'])

            out_p = best_out.get('best_booking_price') or best_out['price_thb']
            in_p = best_in.get('best_booking_price') or best_in['price_thb']
            combos.append({
                'total': out_p + in_p,
                'out_date': out_r['date_label'],
                'in_date': in_r['date_label'],
            })

    if combos:
        return min(combos, key=lambda c: c['total'])
    return None
