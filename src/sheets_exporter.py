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
        ('Dashboard', _update_dashboard),
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


def _get_eligible_flights(route_result):
    """Get direct, non-excluded flights with price > 0."""
    return [f for f in route_result.get('flights', [])
            if f.get('is_direct') and not f.get('is_excluded_airline') and f['price_thb'] > 0]


def _best_flight_price(flight):
    """Get cheapest available price for a flight."""
    bp = flight.get('best_booking_price')
    if bp is not None and bp > 0:
        return bp
    return flight['price_thb']


def _update_dashboard(sh, route_results):
    """Dashboard tab — formatted summary for easy sharing."""
    ws = _get_or_create_sheet(sh, 'Dashboard', [''])
    ws.clear()

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    outbound = [r for r in route_results if r['route'].startswith('BKK')]
    inbound = [r for r in route_results if r['route'].startswith('DAD')]

    rows = []

    # Title
    rows.append(['BKK ↔ DAD Flight Dashboard', '', '', '', '', f'Updated: {now}'])
    rows.append([])

    # === BEST ROUNDTRIP ===
    combo = _find_best_combo(outbound, inbound)
    if combo:
        rows.append(['BEST ROUNDTRIP', '', '', '', '', ''])
        rows.append([f'฿{combo["total"]:,}', '', f'{combo["out_date"]} + {combo["in_date"]}', '', '', ''])
        rows.append([])

    # === OUTBOUND ===
    rows.append(['OUTBOUND: Bangkok → Danang', '', '', '', '', ''])
    rows.append(['Date', 'Airline', 'Depart', 'Arrive', 'Price (airline)', 'Cheapest (3rd party)', 'Source', 'Baggage', 'Stops'])

    for r in outbound:
        flights = sorted(r.get('flights', []), key=lambda f: f['price_thb'])[:10]
        if flights:
            rows.append([r['date_label'], '---', '---', '---', '---', '---', '---', '---', '---'])
        for f in flights:
            bp = f.get('best_booking_price', '')
            src = f.get('best_booking_source', '')
            dep_apt = f.get('departure_airport', '')
            arr_apt = f.get('arrival_airport', '')
            dep = f"{f.get('departure_time', '')} ({dep_apt})" if dep_apt else f.get('departure_time', '')
            arr = f"{f.get('arrival_time', '')} ({arr_apt})" if arr_apt else f.get('arrival_time', '')
            bag = f.get('checked_baggage', '')
            stops = 'Direct' if f.get('is_direct') else f"{f.get('num_stops', '?')} stop"
            excluded = ' ⚠️' if f.get('is_excluded_airline') else ''

            rows.append([
                '',
                f"{f['airline']}{excluded}",
                dep,
                arr,
                f"฿{f['price_thb']:,}",
                f"฿{bp:,}" if bp else '',
                src,
                bag,
                stops,
            ])

    rows.append([])

    # === RETURN ===
    rows.append(['RETURN: Danang → Bangkok', '', '', '', '', ''])
    rows.append(['Date', 'Airline', 'Depart', 'Arrive', 'Price (airline)', 'Cheapest (3rd party)', 'Source', 'Baggage', 'Stops'])

    for r in inbound:
        flights = sorted(r.get('flights', []), key=lambda f: f['price_thb'])[:10]
        if flights:
            rows.append([r['date_label'], '---', '---', '---', '---', '---', '---', '---', '---'])
        for f in flights:
            bp = f.get('best_booking_price', '')
            src = f.get('best_booking_source', '')
            dep_apt = f.get('departure_airport', '')
            arr_apt = f.get('arrival_airport', '')
            dep = f"{f.get('departure_time', '')} ({dep_apt})" if dep_apt else f.get('departure_time', '')
            arr = f"{f.get('arrival_time', '')} ({arr_apt})" if arr_apt else f.get('arrival_time', '')
            bag = f.get('checked_baggage', '')
            stops = 'Direct' if f.get('is_direct') else f"{f.get('num_stops', '?')} stop"
            excluded = ' ⚠️' if f.get('is_excluded_airline') else ''

            rows.append([
                '',
                f"{f['airline']}{excluded}",
                dep,
                arr,
                f"฿{f['price_thb']:,}",
                f"฿{bp:,}" if bp else '',
                src,
                bag,
                stops,
            ])

    rows.append([])

    # === AIRCRAFT REFERENCE ===
    rows.append(['AIRCRAFT REFERENCE', '', '', '', '', ''])
    rows.append(['Aircraft', 'Size', 'Typical Seats', 'Pros', 'Cons'])
    aircraft_info = [
        ['A320', 'Narrow-body', '180', 'Common, reliable, modern avionics', 'Smaller overhead bins'],
        ['A321', 'Narrow-body', '220', 'More legroom variants, newer', 'Can feel crowded if high-density'],
        ['737-800', 'Narrow-body', '189', 'Workhorse, proven design', 'Older models can be noisy'],
        ['787', 'Wide-body', '250', 'Quiet, great air pressure, large windows', 'Rare on short routes'],
        ['777', 'Wide-body', '300-400', 'Very spacious, smooth ride', 'Overkill for short flights'],
        ['ATR 72', 'Turboprop', '70', 'Efficient for short hops', 'Noisy, slower, smaller'],
    ]
    rows.extend(aircraft_info)

    rows.append([])
    rows.append(['TIP: Create a chart from the "Price History" tab to see trends over time!'])

    # Write all at once
    ws.update('A1', rows)

    # Format title
    ws.format('A1', {'textFormat': {'bold': True, 'fontSize': 14}})

    # Format section headers
    section_rows = []
    for i, row in enumerate(rows):
        if row and isinstance(row[0], str) and row[0] in ['BEST ROUNDTRIP', 'OUTBOUND: Bangkok → Danang', 'RETURN: Danang → Bangkok', 'AIRCRAFT REFERENCE']:
            section_rows.append(i + 1)

    for row_num in section_rows:
        ws.format(f'A{row_num}:I{row_num}', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
            'textFormat': {'bold': True, 'foregroundColorStyle': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}},
        })

    # Format combo price big
    if combo:
        ws.format('A4', {'textFormat': {'bold': True, 'fontSize': 18, 'foregroundColorStyle': {'rgbColor': {'red': 0.1, 'green': 0.7, 'blue': 0.2}}}})
