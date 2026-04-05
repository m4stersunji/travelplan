import logging
import gspread
from datetime import datetime, date

from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_PATH, SEARCH_ROUTES

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


def _eligible(flights):
    """Direct, non-excluded flights with price > 0."""
    return [f for f in flights if f.get('is_direct') and not f.get('is_excluded_airline') and f.get('price_thb', 0) > 0]


def _best_price(flight):
    """Cheapest price for a flight (3rd party or airline)."""
    bp = flight.get('best_booking_price')
    if bp is not None and bp > 0:
        return bp
    return flight['price_thb']


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def push_to_sheets(route_results):
    sh = get_sheets_client()
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


# ─── Overview ───────────────────────────────────────────

def _update_overview(sh, route_results):
    headers = ['Route', 'Date', 'Cheapest Airline', 'Airline Price', 'Best Source', 'Best Price', 'Last Check']
    ws = _get_or_create_sheet(sh, 'Overview', headers)

    rows = []
    now = _now()

    for r in route_results:
        direct = _eligible(r.get('flights', []))
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
    combo = _find_best_combo(outbound, inbound)
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
        'Cabin Bag', 'Checked Bag', 'Type'
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
            ])

    if rows:
        existing = ws.get_all_values()
        next_row = len(existing) + 1
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
        direct = _eligible(r.get('flights', []))
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
                direct = _eligible(r.get('flights', []))
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

def _update_dashboard(sh, route_results):
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
    combo = _find_best_combo(outbound, inbound)
    if combo:
        rows.append(['BEST ROUNDTRIP', '', '', '', '', '', '', ''])
        rows.append([combo['total'], '', f'{combo["out_date"]} + {combo["in_date"]}', '', '', '', '', ''])
        rows.append([])

    # === SHOULD YOU BUY? ===
    rows.append(['SHOULD YOU BUY?', '', '', '', '', '', '', ''])
    rows.append(['Route', 'Date', 'Current', 'Average', 'Lowest Ever', 'Trend', 'Days Left', 'Verdict'])

    for r in route_results:
        direct = _eligible(r.get('flights', []))
        if not direct:
            continue
        c = min(direct, key=lambda f: f['price_thb'])
        current = _best_price(c)
        avg = r.get('avg_price')
        lowest = r.get('lowest_ever')
        history = r.get('price_history', [])
        trend = _get_trend(history)
        days_left = _days_until(r.get('search_date', ''))
        verdict = _compute_verdict(current, avg, lowest, trend, days_left, r.get('scrape_count', 0))

        rows.append([
            r['route'],
            r['date_label'],
            current,
            avg if avg else 'N/A',
            lowest if lowest else 'N/A',
            trend,
            days_left if days_left else '?',
            verdict,
        ])

    rows.append([])

    # === FLIGHT TABLES ===
    for direction, label, routes in [
        ('OUTBOUND', 'Bangkok → Danang', outbound),
        ('RETURN', 'Danang → Bangkok', inbound),
    ]:
        rows.append([f'{direction}: {label}', '', '', '', '', '', '', ''])
        rows.append(['Date', 'Airline', 'Depart', 'Arrive', 'Airline Price', 'Best Price', 'Source', 'Baggage', 'Stops'])

        for r in routes:
            flights = sorted(r.get('flights', []), key=lambda f: f['price_thb'])[:10]
            if flights:
                rows.append([r['date_label'], '---', '---', '---', '---', '---', '---', '---', '---'])
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

                rows.append([
                    '',
                    f"{f['airline']}{excluded}",
                    dep, arr,
                    f['price_thb'],
                    bp if bp is not None else '',
                    src, bag, stops,
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


# ─── Buy Recommendation Logic ──────────────────────────

def _get_trend(price_history):
    if len(price_history) < 2:
        return "Not enough data"
    prices = [h['best_price'] for h in price_history if h.get('best_price')]
    if len(prices) < 2:
        return "Not enough data"
    newest = prices[0]
    oldest = prices[-1]
    if newest < oldest:
        return "↓ Falling"
    elif newest > oldest:
        return "↑ Rising"
    return "→ Stable"


def _days_until(search_date):
    try:
        dep = datetime.strptime(search_date, '%Y-%m-%d').date()
        return (dep - date.today()).days
    except (ValueError, TypeError):
        return None


def _compute_verdict(current, avg, lowest, trend, days_left, scrape_count):
    if scrape_count < 3:
        return "📊 Collecting data... (need more checks)"

    if days_left is not None and days_left < 14:
        return "🔴 BUY NOW — prices rise in final 2 weeks"

    if lowest and current <= lowest * 1.05:
        if 'Rising' in trend or 'Stable' in trend:
            return "🟢 BUY NOW — near lowest, not dropping"
        else:
            return "🟡 GOOD PRICE — near lowest, still falling"

    if avg and current < avg:
        if 'Falling' in trend:
            return "🟡 WAIT — below avg but still dropping"
        else:
            return "🟢 GOOD PRICE — below average"

    if avg and current >= avg:
        if 'Falling' in trend and days_left and days_left > 21:
            return "🟡 WAIT — above avg but trending down"
        elif 'Rising' in trend:
            return "🟠 RISKY — above avg and rising"
        else:
            return "🟡 WATCH — at average price"

    return "📊 Monitoring..."


# ─── Helpers ────────────────────────────────────────────

def _find_best_combo(outbound, inbound):
    combos = []
    for out_r in outbound:
        out_direct = _eligible(out_r.get('flights', []))
        if not out_direct:
            continue
        best_out = min(out_direct, key=_best_price)
        for in_r in inbound:
            in_direct = _eligible(in_r.get('flights', []))
            if not in_direct:
                continue
            best_in = min(in_direct, key=_best_price)
            combos.append({
                'total': _best_price(best_out) + _best_price(best_in),
                'out_date': out_r['date_label'],
                'in_date': in_r['date_label'],
            })
    if combos:
        return min(combos, key=lambda c: c['total'])
    return None
