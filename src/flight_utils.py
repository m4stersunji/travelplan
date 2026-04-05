"""Shared flight utility functions.

Used by notifier.py, sheets_exporter.py, and app.py.
Single source of truth for verdict, trend, pricing, and scoring logic.
"""
from datetime import datetime, date


def best_price(flight):
    """Get cheapest available price (3rd party or airline direct)."""
    bp = flight.get('best_booking_price')
    if bp is not None and bp > 0:
        return bp
    return flight.get('price_thb', 0)


def eligible_flights(flights):
    """Direct, non-excluded flights with price > 0."""
    return [f for f in flights
            if f.get('is_direct') and not f.get('is_excluded_airline') and f.get('price_thb', 0) > 0]


def get_trend(price_history):
    """Simple trend from recent price history."""
    if len(price_history) < 2:
        return "Not enough data"
    prices = [h['best_price'] for h in price_history if h.get('best_price')]
    if len(prices) < 2:
        return "Not enough data"
    newest = prices[0]
    oldest = prices[-1]
    if newest < oldest:
        return "Falling"
    elif newest > oldest:
        return "Rising"
    return "Stable"


def days_until(search_date):
    """Days from today until a date string (YYYY-MM-DD)."""
    try:
        dep = datetime.strptime(search_date, '%Y-%m-%d').date()
        return (dep - date.today()).days
    except (ValueError, TypeError):
        return None


def compute_verdict(current, avg, lowest, trend, days_left, scrape_count):
    """Compute buy/wait recommendation.

    Returns (emoji, verdict_text) tuple.
    """
    if scrape_count < 3:
        return "📊", "Collecting data..."

    if days_left is not None and days_left < 14:
        return "🔴", "BUY NOW — last 2 weeks"

    if lowest and current <= lowest * 1.05:
        if trend in ("Rising", "Stable"):
            return "🟢", "BUY — near lowest!"
        else:
            return "🟡", "GOOD — still dropping"

    if avg and current < avg:
        if trend == "Falling":
            return "🟡", "WAIT — below avg, dropping"
        else:
            return "🟢", "GOOD — below average"

    if avg and current >= avg:
        if trend == "Falling" and days_left and days_left > 21:
            return "🟡", "WAIT — trending down"
        elif trend == "Rising":
            return "🟠", "RISKY — above avg, rising"
        else:
            return "🟡", "WATCH — at average"

    return "📊", "Monitoring..."


def verdict_string(current, avg, lowest, trend, days_left, scrape_count):
    """Full verdict string with emoji."""
    emoji, text = compute_verdict(current, avg, lowest, trend, days_left, scrape_count)
    return f"{emoji} {text}"


def score_label(total_score):
    """Convert numeric score (0-20) to human label."""
    if total_score >= 16:
        return "Excellent"
    elif total_score >= 12:
        return "Good"
    elif total_score >= 8:
        return "Fair"
    else:
        return "Poor"


def find_best_combos(outbound, inbound, valid_combos):
    """Find cheapest roundtrip combos from valid pairings only."""
    out_by_date = {r['search_date']: r for r in outbound}
    in_by_date = {r['search_date']: r for r in inbound}

    combos = []
    for go_date, back_date in valid_combos:
        out_r = out_by_date.get(go_date)
        in_r = in_by_date.get(back_date)
        if not out_r or not in_r:
            continue

        out_direct = eligible_flights(out_r.get('flights', []))
        in_direct = eligible_flights(in_r.get('flights', []))
        if not out_direct or not in_direct:
            continue

        best_out = min(out_direct, key=best_price)
        best_in = min(in_direct, key=best_price)

        combos.append({
            'total': best_price(best_out) + best_price(best_in),
            'out_date': out_r['date_label'],
            'out_price': best_price(best_out),
            'in_date': in_r['date_label'],
            'in_price': best_price(best_in),
            'out_route': out_r,
            'in_route': in_r,
            'out_flight': best_out,
            'in_flight': best_in,
        })

    combos.sort(key=lambda c: c['total'])
    return combos


def find_best_scored_combo(outbound, inbound, valid_combos):
    """Find best roundtrip by combined score from valid pairings."""
    out_by_date = {r['search_date']: r for r in outbound}
    in_by_date = {r['search_date']: r for r in inbound}

    combos = []
    for go_date, back_date in valid_combos:
        out_r = out_by_date.get(go_date)
        in_r = in_by_date.get(back_date)
        if not out_r or not in_r:
            continue

        go_scored = [f for f in eligible_flights(out_r.get('flights', []))
                     if f.get('total_score')]
        back_scored = [f for f in eligible_flights(in_r.get('flights', []))
                       if f.get('total_score')]
        if not go_scored or not back_scored:
            continue

        best_go = max(go_scored, key=lambda f: f['total_score'])
        best_back = max(back_scored, key=lambda f: f['total_score'])

        combos.append({
            'go_flight': best_go,
            'back_flight': best_back,
            'go_route': out_r,
            'back_route': in_r,
            'total': best_price(best_go) + best_price(best_back),
            'combined_score': best_go['total_score'] + best_back['total_score'],
        })

    if not combos:
        return None

    combos.sort(key=lambda c: (-c['combined_score'], c['total']))
    return combos[0]


def group_by_trip(route_results):
    """Group route results by trip_name. Returns dict {trip_name: [results]}."""
    trips = {}
    for r in route_results:
        name = r.get('trip_name', 'Default')
        trips.setdefault(name, []).append(r)
    return trips
