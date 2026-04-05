import logging
import json
import requests
from datetime import datetime

from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

logger = logging.getLogger(__name__)

LINE_API_URL = "https://api.line.me/v2/bot/message/push"


def send_line_notification(message):
    """Send a text push message via LINE."""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        logger.warning("LINE credentials not configured — skipping notification")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}],
    }

    try:
        resp = requests.post(LINE_API_URL, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("LINE notification sent successfully")
            return True
        else:
            logger.error(f"LINE API error {resp.status_code}: {resp.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"Failed to send LINE notification: {e}")
        return False


def send_line_flex(flex_container):
    """Send a Flex Message via LINE."""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        logger.warning("LINE credentials not configured — skipping notification")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{
            "type": "flex",
            "altText": "Flight Price Update",
            "contents": flex_container,
        }],
    }

    try:
        resp = requests.post(LINE_API_URL, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("LINE flex message sent successfully")
            return True
        else:
            logger.error(f"LINE API error {resp.status_code}: {resp.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"Failed to send LINE flex: {e}")
        return False


def format_price_change(current_price, previous_price):
    if previous_price is None:
        return "NEW"
    diff = current_price - previous_price
    if diff < 0:
        return f"▼{abs(diff):,}"
    elif diff > 0:
        return f"▲{diff:,}"
    else:
        return "="


def build_flex_message(route_results, top_n=5):
    """Build a LINE Flex Message carousel with flight data.

    Returns a Flex carousel container dict.
    Card order: Summary (with buy advice) → Outbound routes → Return routes
    """
    bubbles = []

    outbound = [r for r in route_results if r['route'].startswith('BKK')]
    inbound = [r for r in route_results if r['route'].startswith('DAD')]

    # Summary + buy recommendation FIRST
    summary = _build_summary_bubble(outbound, inbound, route_results)
    if summary:
        bubbles.append(summary)

    # Route bubbles
    for r in outbound:
        bubble = _build_route_bubble(r, "GO", "#1DB446", top_n)
        if bubble:
            bubbles.append(bubble)
    for r in inbound:
        bubble = _build_route_bubble(r, "BACK", "#0367D3", top_n)
        if bubble:
            bubbles.append(bubble)

    return {"type": "carousel", "contents": bubbles}


def _build_route_bubble(route_data, direction, color, top_n):
    """Build a single bubble for one route/date."""
    flights = sorted(route_data['flights'], key=lambda f: f['price_thb'])[:top_n]
    if not flights:
        return None

    # Flight rows
    flight_rows = []
    for f in flights:
        price = f"฿{f['price_thb']:,}"
        airline = f['airline'][:20]
        dep = f.get('departure_time', '?')
        arr = f.get('arrival_time', '?')
        dep_apt = f.get('departure_airport', '')
        arr_apt = f.get('arrival_airport', '')
        time_str = f"{dep}({dep_apt})→{arr}({arr_apt})" if dep_apt else f"{dep}→{arr}"

        stops = "" if f.get('is_direct') else f" | {f['num_stops']}stop"
        excluded = " ⚠️" if f.get('is_excluded_airline') else ""
        cabin = f.get('cabin_baggage', '7kg')
        checked = f.get('checked_baggage', '?')
        # Show "7kg/23kg" or "7kg/no bag"
        checked_short = checked.replace(' checked', '').replace('No checked bag', 'no bag')
        cabin_short = cabin.replace(' carry-on', '')
        bag_short = f"{cabin_short}/{checked_short}"

        # Show cheapest price (3rd party or airline direct)
        best_bp = f.get('best_booking_price')
        best_src = f.get('best_booking_source', '')
        if best_bp and best_bp < f['price_thb']:
            price_line = f"฿{best_bp:,} ({best_src})"
            price_color = "#1DB446"  # Green for cheaper 3rd party
        else:
            price_line = price
            price_color = "#999999" if f.get('is_excluded_airline') else "#111111"

        # Score
        total_score = f.get('total_score', 0)
        score_int = round(total_score) if total_score else 0
        score_color = "#1DB446" if score_int >= 15 else "#FF8C00" if score_int >= 10 else "#999999"
        score_str = f"★{score_int}" if score_int else ""

        flight_rows.append({
            "type": "box", "layout": "vertical", "spacing": "xs",
            "paddingBottom": "md",
            "contents": [
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": price_line, "size": "md", "weight": "bold",
                         "color": price_color, "flex": 5},
                        {"type": "text", "text": score_str, "size": "sm", "weight": "bold",
                         "color": score_color, "flex": 1, "align": "end"},
                    ]
                },
                {
                    "type": "text", "text": f"{airline}{excluded}",
                    "size": "xs", "color": "#666666"},
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": time_str,
                         "size": "xxs", "color": "#AAAAAA", "flex": 5},
                        {"type": "text", "text": f"{bag_short}{stops}",
                         "size": "xxs", "color": "#AAAAAA", "flex": 3, "align": "end"},
                    ]
                },
            ]
        })

    # Add separator between flights
    body_contents = []
    for i, row in enumerate(flight_rows):
        if i > 0:
            body_contents.append({"type": "separator", "margin": "sm"})
        body_contents.append(row)

    return {
        "type": "bubble", "size": "kilo",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": color,
            "paddingAll": "md",
            "contents": [
                {"type": "text", "text": direction, "color": "#FFFFFF",
                 "size": "xs", "weight": "bold"},
                {"type": "text", "text": route_data['date_label'],
                 "color": "#FFFFFF", "size": "xl", "weight": "bold"},
            ]
        },
        "body": {
            "type": "box", "layout": "vertical",
            "spacing": "sm", "paddingAll": "md",
            "contents": body_contents,
        },
    }


def _build_summary_bubble(outbound, inbound, all_results):
    """Summary card: best deal + should you book now?

    Designed to answer in 5 seconds: "Should I open Agoda and book?"
    """
    contents = []

    # Find the best roundtrip COMBO (not independent picks)
    best_combo = _find_best_scored_combo(outbound, inbound)

    if not best_combo:
        contents.append({"type": "text", "text": "No flights found", "size": "md"})
        return _wrap_summary_bubble(contents)

    go_flight = best_combo['go_flight']
    back_flight = best_combo['back_flight']
    total = best_combo['total']
    go_route = best_combo['go_route']
    back_route = best_combo['back_route']

    # --- BEST DEAL ---
    contents.append({"type": "text", "text": "BEST DEAL NOW", "size": "xxs", "color": "#AAAAAA"})
    contents.append({"type": "text", "text": f"฿{total:,} roundtrip",
                     "size": "xxl", "weight": "bold", "color": "#1DB446"})

    _add_flight_row(contents, "GO", go_route['date_label'], go_flight)
    _add_flight_row(contents, "BACK", back_route['date_label'], back_flight)

    contents.append({"type": "separator", "margin": "md"})

    # --- VERDICT ---
    best_route = max(all_results, key=lambda r: r.get('scrape_count', 0))
    scrape_count = best_route.get('scrape_count', 0)
    avg = best_route.get('avg_price')
    lowest = best_route.get('lowest_ever')
    trend = _get_trend(best_route.get('price_history', []))
    days = _days_until(best_route.get('search_date', ''))
    current = _best_price(go_flight)

    verdict = _compute_verdict(current, avg, lowest, trend, days, scrape_count)
    verdict_color = "#1DB446" if "BUY" in verdict or "GOOD" in verdict else "#FF8C00" if "WAIT" in verdict else "#E53935"

    contents.append({
        "type": "text", "text": verdict, "size": "sm", "weight": "bold",
        "color": verdict_color, "margin": "md", "wrap": True,
    })

    # Price context line
    if avg and lowest:
        contents.append({
            "type": "text", "size": "xxs", "color": "#999999", "wrap": True,
            "text": f"Avg ฿{avg:,} | Low ฿{lowest:,} | {trend}" + (f" | {days}d left" if days else ""),
        })
    elif scrape_count < 3:
        contents.append({
            "type": "text", "size": "xxs", "color": "#999999",
            "text": f"Check #{scrape_count} — need 3+ for advice",
        })

    # --- WHERE TO BOOK ---
    go_src = go_flight.get('best_booking_source', '')
    back_src = back_flight.get('best_booking_source', '')
    if go_src or back_src:
        src = go_src or back_src
        if src:
            contents.append({"type": "separator", "margin": "md"})
            contents.append({
                "type": "text", "text": f"Book on: {src}", "size": "xs",
                "weight": "bold", "color": "#0367D3", "margin": "md",
            })

    # Timestamp
    contents.append({
        "type": "text", "size": "xxs", "color": "#CCCCCC", "margin": "md",
        "text": datetime.now().strftime('%d %b %H:%M'),
    })

    return _wrap_summary_bubble(contents)


def _find_best_scored_combo(outbound, inbound):
    """Find the best roundtrip combo by combined score.

    Picks the highest total_score GO + highest total_score BACK,
    but as a valid roundtrip pair (go_date < back_date).
    """
    combos = []

    for out_r in outbound:
        go_candidates = [f for f in out_r.get('flights', [])
                         if f.get('total_score') and f.get('is_direct') and not f.get('is_excluded_airline')]
        if not go_candidates:
            continue
        best_go = max(go_candidates, key=lambda f: f['total_score'])

        for in_r in inbound:
            # Ensure return is after departure
            if in_r.get('search_date', '') <= out_r.get('search_date', ''):
                continue

            back_candidates = [f for f in in_r.get('flights', [])
                               if f.get('total_score') and f.get('is_direct') and not f.get('is_excluded_airline')]
            if not back_candidates:
                continue
            best_back = max(back_candidates, key=lambda f: f['total_score'])

            go_price = _best_price(best_go)
            back_price = _best_price(best_back)
            combined_score = best_go['total_score'] + best_back['total_score']

            combos.append({
                'go_flight': best_go,
                'back_flight': best_back,
                'go_route': out_r,
                'back_route': in_r,
                'total': go_price + back_price,
                'combined_score': combined_score,
            })

    if not combos:
        return None

    # Sort by combined score (highest first), break ties by cheapest price
    combos.sort(key=lambda c: (-c['combined_score'], c['total']))
    return combos[0]


def _add_flight_row(contents, direction, date_label, f):
    """Add a compact flight row to the summary."""
    price = _best_price(f)
    src = f.get('best_booking_source', '')
    dep = f.get('departure_time', '?')
    arr = f.get('arrival_time', '?')
    dep_apt = f.get('departure_airport', '')
    arr_apt = f.get('arrival_airport', '')
    bag = f.get('checked_baggage', '')
    bag_short = "✓bag" if 'checked' in bag.lower() else "no bag"
    score_int = round(f.get('total_score', 0))

    contents.append({
        "type": "box", "layout": "vertical", "margin": "md",
        "contents": [
            {"type": "box", "layout": "horizontal", "contents": [
                {"type": "text", "text": f"{direction} {date_label}",
                 "size": "xxs", "color": "#AAAAAA", "flex": 4},
                {"type": "text", "text": f"★{score_int}",
                 "size": "xs", "weight": "bold",
                 "color": "#1DB446" if score_int >= 15 else "#FF8C00",
                 "flex": 1, "align": "end"},
            ]},
            {"type": "text", "text": f"฿{price:,} {f['airline'][:18]}",
             "size": "sm", "weight": "bold"},
            {"type": "text",
             "text": f"{dep}({dep_apt})→{arr}({arr_apt}) | {bag_short}",
             "size": "xxs", "color": "#999999"},
        ]
    })


def _wrap_summary_bubble(contents):
    return {
        "type": "bubble", "size": "kilo",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#2C2C2C", "paddingAll": "md",
            "contents": [
                {"type": "text", "text": "BKK ↔ DAD",
                 "color": "#FFFFFF", "size": "xl", "weight": "bold"},
            ]
        },
        "body": {
            "type": "box", "layout": "vertical",
            "spacing": "sm", "paddingAll": "md",
            "contents": contents,
        },
    }


def _best_price(flight):
    """Get the cheapest price for a flight (booking or listed)."""
    bp = flight.get('best_booking_price')
    if bp and bp < flight['price_thb']:
        return bp
    return flight['price_thb']


def _find_best_combos(outbound, inbound):
    """Find cheapest roundtrip combinations (direct, non-excluded only)."""
    combos = []
    for out_r in outbound:
        out_direct = [f for f in out_r['flights'] if f.get('is_direct') and not f.get('is_excluded_airline') and f['price_thb'] > 0]
        if not out_direct:
            continue
        best_out = min(out_direct, key=_best_price)

        for in_r in inbound:
            in_direct = [f for f in in_r['flights'] if f.get('is_direct') and not f.get('is_excluded_airline') and f['price_thb'] > 0]
            if not in_direct:
                continue
            best_in = min(in_direct, key=_best_price)

            out_p = _best_price(best_out)
            in_p = _best_price(best_in)
            combos.append({
                'total': out_p + in_p,
                'out_date': out_r['date_label'],
                'out_price': out_p,
                'in_date': in_r['date_label'],
                'in_price': in_p,
            })

    combos.sort(key=lambda c: c['total'])
    return combos


def _days_until(search_date):
    try:
        from datetime import date
        dep = datetime.strptime(search_date, '%Y-%m-%d').date()
        return (dep - date.today()).days
    except (ValueError, TypeError):
        return None


def _compute_verdict(current, avg, lowest, trend, days_left, scrape_count):
    if scrape_count < 3:
        return "📊 Collecting data..."
    if days_left is not None and days_left < 14:
        return "🔴 BUY NOW — last 2 weeks"
    if lowest and current <= lowest * 1.05:
        if 'Rising' in trend or 'Stable' in trend or 'stable' in trend:
            return "🟢 BUY — near lowest!"
        else:
            return "🟡 GOOD — still dropping"
    if avg and current < avg:
        if 'Falling' in trend or 'down' in trend:
            return "🟡 WAIT — below avg, dropping"
        else:
            return "🟢 GOOD — below average"
    if avg and current >= avg:
        if ('Falling' in trend or 'down' in trend) and days_left and days_left > 21:
            return "🟡 WAIT — trending down"
        elif 'Rising' in trend or 'up' in trend:
            return "🟠 RISKY — above avg, rising"
        else:
            return "🟡 WATCH — at average"
    return "📊 Monitoring..."


def _get_trend(price_history):
    """Simple trend from recent price history."""
    if len(price_history) < 2:
        return ""
    prices = [h['best_price'] for h in price_history if h['best_price'] is not None]
    if len(prices) < 2:
        return ""
    newest = prices[0]
    oldest = prices[-1]
    if newest < oldest:
        return "↓down"
    elif newest > oldest:
        return "↑up"
    else:
        return "→stable"


# Keep text format as fallback
def format_combined_message(route_results, top_n=5):
    """Plain text fallback (used if Flex fails)."""
    lines = [f"BKK-DAD Price Update {datetime.now().strftime('%d %b %H:%M')}", ""]

    outbound = [r for r in route_results if r['route'].startswith('BKK')]
    inbound = [r for r in route_results if r['route'].startswith('DAD')]

    for direction, routes in [("GO", outbound), ("BACK", inbound)]:
        for r in routes:
            lines.append(f"[{direction}] {r['date_label']}")
            flights = sorted(r['flights'], key=lambda f: f['price_thb'])[:top_n]
            for f in flights:
                dep = f.get('departure_time', '?')
                arr = f.get('arrival_time', '?')
                stops = "" if f.get('is_direct') else f" {f['num_stops']}stop"
                lines.append(f"  ฿{f['price_thb']:,} {f['airline'][:18]}{stops} {dep}-{arr}")
            lines.append("")

    combos = _find_best_combos(outbound, inbound)
    if combos:
        lines.append("BEST COMBO")
        for c in combos[:2]:
            lines.append(f"  ฿{c['total']:,} = {c['out_date']} + {c['in_date']}")

    return "\n".join(lines)
