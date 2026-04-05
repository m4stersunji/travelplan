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
    """
    bubbles = []

    # Group by direction
    outbound = [r for r in route_results if r['route'].startswith('BKK')]
    inbound = [r for r in route_results if r['route'].startswith('DAD')]

    # Build outbound bubbles
    for r in outbound:
        bubble = _build_route_bubble(r, "OUTBOUND", "#1DB446", top_n)
        if bubble:
            bubbles.append(bubble)

    # Build inbound bubbles
    for r in inbound:
        bubble = _build_route_bubble(r, "RETURN", "#0367D3", top_n)
        if bubble:
            bubbles.append(bubble)

    # Build summary bubble
    summary = _build_summary_bubble(outbound, inbound, route_results)
    if summary:
        bubbles.append(summary)

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

        flight_rows.append({
            "type": "box", "layout": "vertical", "spacing": "xs",
            "paddingBottom": "md",
            "contents": [
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": price_line, "size": "md", "weight": "bold",
                         "color": price_color, "flex": 5},
                        {"type": "text", "text": f"{airline}{excluded}",
                         "size": "xs", "color": "#666666", "flex": 4, "align": "end"},
                    ]
                },
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
    """Build a summary bubble with best combos and history."""
    contents = []

    # Best roundtrip combos
    combos = _find_best_combos(outbound, inbound)
    if combos:
        contents.append({"type": "text", "text": "BEST ROUNDTRIP", "size": "xs",
                         "weight": "bold", "color": "#1DB446"})
        for combo in combos[:3]:
            contents.append({
                "type": "text", "size": "sm", "weight": "bold",
                "text": f"฿{combo['total']:,}",
            })
            contents.append({
                "type": "text", "size": "xxs", "color": "#999999",
                "text": f"  {combo['out_date']} ฿{combo['out_price']:,} + {combo['in_date']} ฿{combo['in_price']:,}",
            })
        contents.append({"type": "separator", "margin": "md"})

    # History
    contents.append({"type": "text", "text": "HISTORY", "size": "xs",
                     "weight": "bold", "color": "#0367D3", "margin": "md"})
    for r in all_results:
        if r['lowest_ever'] is not None:
            trend = _get_trend(r.get('price_history', []))
            trend_text = f" {trend}" if trend else ""
            contents.append({
                "type": "text", "size": "xxs", "color": "#666666",
                "text": f"{r['date_label']}: lowest ฿{r['lowest_ever']:,}{trend_text} ({r['scrape_count']} checks)",
            })

    # Timestamp
    contents.append({"type": "separator", "margin": "md"})
    contents.append({
        "type": "text", "size": "xxs", "color": "#AAAAAA", "margin": "md",
        "text": f"Checked: {datetime.now().strftime('%d %b %H:%M')}",
    })

    return {
        "type": "bubble", "size": "kilo",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#555555", "paddingAll": "md",
            "contents": [
                {"type": "text", "text": "SUMMARY", "color": "#FFFFFF",
                 "size": "xs", "weight": "bold"},
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
