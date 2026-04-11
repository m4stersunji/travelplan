import logging
import gspread
from datetime import datetime, date

from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_PATH
from flight_utils import best_price, eligible_flights, get_trend, days_until, verdict_string, score_label, find_best_combos

logger = logging.getLogger(__name__)


def get_sheets_client():
    if not GOOGLE_SHEET_ID or not GOOGLE_CREDENTIALS_PATH:
        logger.warning("Google Sheets not configured — skipping")
        return None
    try:
        gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_PATH)
        return gc.open_by_key(GOOGLE_SHEET_ID)
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        return None


def _get_or_create_sheet(spreadsheet, title, headers):
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=2000, cols=len(headers))
    existing = ws.row_values(1)
    if not existing:
        ws.update('A1', [headers])
        ws.format('A1:Z1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})
    return ws


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def push_to_sheets(route_results, valid_combos=None):
    sh = get_sheets_client()
    if not sh:
        return False

    success = True
    for name, fn in [
        ('Overview', lambda sh, rr: _update_overview(sh, rr, valid_combos or [])),
        ('All Flights', _update_all_flights),
        ('Price History', _update_price_history),
        ('Heatmap', _update_heatmap),
        ('Dashboard', lambda sh, rr: _update_dashboard(sh, rr, valid_combos or [])),
    ]:
        try:
            fn(sh, route_results)
            logger.info(f"Sheets: {name} updated")
        except Exception as e:
            logger.error(f"Sheets: {name} failed: {e}")
            success = False
    return success


# ─── Overview ───────────────────────────────────────────

def _update_overview(sh, route_results, valid_combos):
    headers = ['Route', 'Date', 'Cheapest Airline', 'Airline Price', 'Best Source', 'Best Price', 'Last Check']
    ws = _get_or_create_sheet(sh, 'Overview', headers)

    rows = []
    now = _now()

    for r in route_results:
        direct = eligible_flights(r.get('flights', []))
        if not direct:
            continue
        c = min(direct, key=lambda f: f['price_thb'])
        bp = c.get('best_booking_price')
        src = c.get('best_booking_source', '')

        rows.append([
            r['route'], r['date_label'], c['airline'], c['price_thb'],
            src if src else 'Airline direct',
            bp if bp is not None else c['price_thb'],
            now,
        ])

    outbound = [r for r in route_results if r['route'].startswith('BKK')]
    inbound = [r for r in route_results if r['route'].startswith('DAD')]
    combo = _find_best_combo(outbound, inbound, valid_combos)
    if combo:
        rows.append([])
        rows.append(['BEST ROUNDTRIP', '', '', '', f"{combo['out_date']} + {combo['in_date']}", combo['total'], now])

    ws.clear()
    ws.update('A1', [headers] + rows)
    ws.format('A1:G1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})


# ─── All Flights ────────────────────────────────────────

def _update_all_flights(sh, route_results):
    headers = [
        'Checked At', 'Route', 'Date', 'Airline', 'Flight#',
        'From', 'Depart', 'To', 'Arrive', 'Duration (min)',
        'Airline Price', 'Best 3rd Price', 'Best Source',
        'Aircraft', 'Stops', 'Direct', 'Excluded',
        'Cabin Bag', 'Checked Bag', 'Type',
        'Price Score', 'Time Score', 'Total Score'
    ]
    ws = _get_or_create_sheet(sh, 'All Flights', headers)
    now = _now()

    rows = []
    for r in route_results:
        for f in sorted(r.get('flights', []), key=lambda f: f['price_thb']):
            rows.append([
                now,
                r['route'],
                r['date_label'],
                f.get('airline', ''),
                f.get('flight_number', ''),
                f.get('departure_airport', ''),
                f.get('departure_time', ''),
                f.get('arrival_airport', ''),
                f.get('arrival_time', ''),
                f.get('duration_minutes') or None,
                f.get('price_thb') or None,
                f.get('best_booking_price') or None,
                f.get('best_booking_source', ''),
                f.get('aircraft_type', ''),
                f.get('num_stops') or 0,
                f.get('is_direct', False),
                f.get('is_excluded_airline', False),
                f.get('cabin_baggage', ''),
                f.get('checked_baggage', ''),
                f.get('service_type', ''),
                f.get('price_score', ''),
                f.get('time_score', ''),
                f.get('total_score', ''),
            ])

    if rows:
        existing = ws.get_all_values()
        next_row = len(existing) + 1
        # Auto-expand if near row limit
        if next_row + len(rows) > ws.row_count:
            ws.add_rows(len(rows) + 500)
        ws.update(f'A{next_row}', rows)


# ─── Price History ──────────────────────────────────────

def _update_price_history(sh, route_results):
    headers = ['Checked At']
    for r in route_results:
        label = f"{r['route']} {r['date_label']}"
        headers.append(f"{label} (Airline)")
        headers.append(f"{label} (Best)")

    ws = _get_or_create_sheet(sh, 'Price History', headers)

    # Validate headers
    existing_headers = ws.row_values(1)
    if existing_headers and existing_headers != headers:
        logger.warning("Price History headers changed — updating row 1")
        ws.update('A1', [headers])

    now = _now()
    row = [now]

    for r in route_results:
        direct = eligible_flights(r.get('flights', []))
        if direct:
            c = min(direct, key=lambda f: f['price_thb'])
            row.append(c['price_thb'])
            bp = c.get('best_booking_price')
            row.append(bp if bp is not None else c['price_thb'])
        else:
            row.append(None)
            row.append(None)

    existing = ws.get_all_values()
    next_row = len(existing) + 1
    ws.update(f'A{next_row}', [row])


# ─── Heatmap (matrix layout) ───────────────────────────

def _update_heatmap(sh, route_results):
    headers = ['', 'BKK→DAD (Airline)', 'BKK→DAD (Best)', 'DAD→BKK (Airline)', 'DAD→BKK (Best)']
    ws = _get_or_create_sheet(sh, 'Heatmap', headers)

    outbound = {r['date_label']: r for r in route_results if r['route'].startswith('BKK')}
    inbound = {r['date_label']: r for r in route_results if r['route'].startswith('DAD')}
    all_dates = sorted(set(list(outbound.keys()) + list(inbound.keys())))

    rows = []
    for d in all_dates:
        row = [d]
        for group in [outbound, inbound]:
            r = group.get(d)
            if r:
                direct = eligible_flights(r.get('flights', []))
                if direct:
                    c = min(direct, key=lambda f: f['price_thb'])
                    row.append(c['price_thb'])
                    bp = c.get('best_booking_price')
                    row.append(bp if bp is not None else c['price_thb'])
                else:
                    row.extend([None, None])
            else:
                row.extend([None, None])
        rows.append(row)

    ws.clear()
    ws.update('A1', [headers] + rows)
    ws.format('A1:E1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})


# ─── Dashboard ──────────────────────────────────────────

def _update_dashboard(sh, route_results, valid_combos):
    ws = _get_or_create_sheet(sh, 'Dashboard', [''])
    ws.clear()

    now = _now()
    outbound = [r for r in route_results if r['route'].startswith('BKK')]
    inbound = [r for r in route_results if r['route'].startswith('DAD')]

    rows = []

    # Title
    rows.append(['BKK ↔ DAD Flight Dashboard', '', '', '', '', '', '', f'Updated: {now}'])
    rows.append([])

    # === BEST ROUNDTRIP ===
    combo = _find_best_combo(outbound, inbound, valid_combos)
    if combo:
        rows.append(['BEST ROUNDTRIP', '', '', '', '', '', '', ''])
        rows.append([combo['total'], '', f'{combo["out_date"]} + {combo["in_date"]}', '', '', '', '', ''])
        rows.append([])

    # === SHOULD YOU BUY? ===
    rows.append(['SHOULD YOU BUY?', '', '', '', '', '', '', ''])
    rows.append(['Route', 'Date', 'Current', 'Average', 'Lowest Ever', 'Trend', 'Days Left', 'Verdict'])

    for r in route_results:
        direct = eligible_flights(r.get('flights', []))
        if not direct:
            continue
        c = min(direct, key=lambda f: f['price_thb'])
        current = best_price(c)
        avg = r.get('avg_price')
        lowest = r.get('lowest_ever')
        history = r.get('price_history', [])
        trend = get_trend(history)
        dl = days_until(r.get('search_date', ''))
        verdict = verdict_string(current, avg, lowest, trend, dl, r.get('scrape_count', 0))

        rows.append([
            r['route'],
            r['date_label'],
            current,
            avg if avg else 'N/A',
            lowest if lowest else 'N/A',
            trend,
            dl if dl else '?',
            verdict,
        ])

    rows.append([])

    # === FLIGHT TABLES ===
    for direction, label, routes in [
        ('OUTBOUND', 'Bangkok → Danang', outbound),
        ('RETURN', 'Danang → Bangkok', inbound),
    ]:
        rows.append([f'{direction}: {label}', '', '', '', '', '', '', ''])
        rows.append(['Date', 'Airline', 'Depart', 'Arrive', 'Airline Price', 'Best Price', 'Source', 'Baggage', 'Stops', 'Score'])

        for r in routes:
            flights = sorted(r.get('flights', []), key=lambda f: f['price_thb'])[:10]
            if flights:
                rows.append([r['date_label'], '---', '---', '---', '---', '---', '---', '---', '---', '---'])
            for f in flights:
                bp = f.get('best_booking_price')
                src = f.get('best_booking_source', '')
                dep_apt = f.get('departure_airport', '')
                arr_apt = f.get('arrival_airport', '')
                dep = f"{f.get('departure_time', '')} ({dep_apt})" if dep_apt else f.get('departure_time', '')
                arr = f"{f.get('arrival_time', '')} ({arr_apt})" if arr_apt else f.get('arrival_time', '')
                bag = f.get('checked_baggage', '')
                stops = 'Direct' if f.get('is_direct') else f"{f.get('num_stops', '?')} stop"
                excluded = ' ⚠️' if f.get('is_excluded_airline') else ''

                score = f.get('total_score', '')
                score_str = f"{score}/20" if score != '' else ''
                rows.append([
                    '',
                    f"{f['airline']}{excluded}",
                    dep, arr,
                    f['price_thb'],
                    bp if bp is not None else '',
                    src, bag, stops, score_str,
                ])
        rows.append([])

    # === AIRCRAFT REFERENCE ===
    rows.append(['AIRCRAFT REFERENCE', '', '', '', '', '', '', ''])
    rows.append(['Aircraft', 'Size', 'Typical Seats', 'Pros', 'Cons'])
    rows.extend([
        ['A320', 'Narrow-body', '180', 'Common, reliable', 'Smaller overhead bins'],
        ['A321', 'Narrow-body', '220', 'More legroom variants', 'Can feel crowded'],
        ['737-800', 'Narrow-body', '189', 'Proven design', 'Older models noisy'],
        ['787', 'Wide-body', '250', 'Quiet, great windows', 'Rare on short routes'],
        ['777', 'Wide-body', '300-400', 'Very spacious', 'Overkill for short flights'],
        ['ATR 72', 'Turboprop', '70', 'Efficient short hops', 'Noisy, slower'],
    ])

    # Write
    ws.update('A1', rows)

    # Format title
    ws.format('A1', {'textFormat': {'bold': True, 'fontSize': 14}})

    # Format section headers
    section_labels = ['BEST ROUNDTRIP', 'SHOULD YOU BUY?', 'OUTBOUND: Bangkok → Danang', 'RETURN: Danang → Bangkok', 'AIRCRAFT REFERENCE']
    for i, row in enumerate(rows):
        if row and isinstance(row[0], str) and row[0] in section_labels:
            ws.format(f'A{i+1}:I{i+1}', {
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
                'textFormat': {'bold': True, 'foregroundColorStyle': {'rgbColor': {'red': 1, 'green': 1, 'blue': 1}}},
            })

    # Format combo price
    if combo:
        ws.format('A4', {'textFormat': {'bold': True, 'fontSize': 18, 'foregroundColorStyle': {'rgbColor': {'red': 0.1, 'green': 0.7, 'blue': 0.2}}}})


def _find_best_combo(outbound, inbound, valid_combos):
    combos = find_best_combos(outbound, inbound, valid_combos)
    return combos[0] if combos else None
