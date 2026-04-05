import logging
import requests
from datetime import datetime

from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
from flight_utils import (
    best_price, eligible_flights, get_trend, days_until,
    verdict_string, score_label, find_best_combos, find_best_scored_combo,
    group_by_trip,
)

logger = logging.getLogger(__name__)

LINE_API_URL = "https://api.line.me/v2/bot/message/push"


def send_line_notification(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        logger.warning("LINE credentials not configured")
        return False
    try:
        resp = requests.post(LINE_API_URL, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        }, json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}, timeout=10)
        if resp.status_code == 200:
            logger.info("LINE text sent")
            return True
        logger.error(f"LINE error {resp.status_code}: {resp.text}")
        return False
    except requests.RequestException as e:
        logger.error(f"LINE failed: {e}")
        return False


def send_line_flex(flex_container):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        return False
    try:
        resp = requests.post(LINE_API_URL, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        }, json={"to": LINE_USER_ID, "messages": [{
            "type": "flex", "altText": "Flight Price Update", "contents": flex_container,
        }]}, timeout=10)
        if resp.status_code == 200:
            logger.info("LINE flex sent")
            return True
        logger.error(f"LINE flex error {resp.status_code}: {resp.text}")
        return False
    except requests.RequestException as e:
        logger.error(f"LINE flex failed: {e}")
        return False


# ─── Flex Message Builder ───────────────────────────────

def build_flex_message(route_results, valid_combos, top_n=5):
    """Build LINE Flex carousel. Supports multiple trips dynamically."""
    bubbles = []
    trips = group_by_trip(route_results)

    for trip_name, results in trips.items():
        outbound = [r for r in results if r.get('route_code', r['route'])[:3] == r['route'][:3]]
        inbound = [r for r in results if r not in outbound]

        # Detect direction from route codes
        all_codes = [r.get('route_code', r['route']) for r in results]
        outbound = []
        inbound = []
        for r in results:
            code = r.get('route_code', r['route'])
            # First route code seen is outbound direction
            if not outbound or code == outbound[0].get('route_code', outbound[0]['route']):
                outbound.append(r)
            else:
                inbound.append(r)

        # Summary bubble
        summary = _build_summary(trip_name, outbound, inbound, results, valid_combos)
        if summary:
            bubbles.append(summary)

        # Route bubbles
        for r in outbound:
            b = _build_route_bubble(r, "GO", "#1DB446", top_n)
            if b:
                bubbles.append(b)
        for r in inbound:
            b = _build_route_bubble(r, "BACK", "#0367D3", top_n)
            if b:
                bubbles.append(b)

    return {"type": "carousel", "contents": bubbles[:10]}  # LINE max 10 bubbles


def _build_summary(trip_name, outbound, inbound, all_results, valid_combos):
    """Summary card: best deal + verdict + where to book."""
    contents = []

    combo = find_best_scored_combo(outbound, inbound, valid_combos)
    if not combo:
        contents.append({"type": "text", "text": "No flights found", "size": "md"})
        return _wrap_bubble(trip_name, "#2C2C2C", contents)

    go = combo['go_flight']
    back = combo['back_flight']

    # Best deal price
    contents.append({"type": "text", "text": "BEST DEAL", "size": "xxs", "color": "#AAAAAA"})
    contents.append({"type": "text", "text": f"฿{combo['total']:,} roundtrip",
                     "size": "xxl", "weight": "bold", "color": "#1DB446"})

    # GO + BACK flights
    _add_flight_row(contents, "GO", combo['go_route']['date_label'], go)
    _add_flight_row(contents, "BACK", combo['back_route']['date_label'], back)

    contents.append({"type": "separator", "margin": "md"})

    # Verdict
    best_r = max(all_results, key=lambda r: r.get('scrape_count', 0))
    trend = get_trend(best_r.get('price_history', []))
    days = days_until(best_r.get('search_date', ''))
    v = verdict_string(
        best_price(go), best_r.get('avg_price'), best_r.get('lowest_ever'),
        trend, days, best_r.get('scrape_count', 0)
    )

    v_color = "#1DB446" if "BUY" in v or "GOOD" in v else "#FF8C00" if "WAIT" in v else "#E53935"
    contents.append({"type": "text", "text": v, "size": "sm", "weight": "bold",
                     "color": v_color, "margin": "md", "wrap": True})

    # Context
    avg = best_r.get('avg_price')
    lowest = best_r.get('lowest_ever')
    if avg and lowest:
        contents.append({"type": "text", "size": "xxs", "color": "#999999", "wrap": True,
                         "text": f"Avg ฿{avg:,} | Low ฿{lowest:,} | {trend}" + (f" | {days}d left" if days else "")})
    elif best_r.get('scrape_count', 0) < 3:
        contents.append({"type": "text", "size": "xxs", "color": "#999999",
                         "text": f"Check #{best_r.get('scrape_count', 0)} — need 3+ for advice"})

    # Where to book
    go_src = go.get('best_booking_source', '')
    back_src = back.get('best_booking_source', '')
    sources = set(filter(None, [go_src, back_src]))
    if sources:
        contents.append({"type": "separator", "margin": "md"})
        contents.append({"type": "text", "text": f"Book: {' | '.join(sources)}",
                         "size": "xs", "weight": "bold", "color": "#0367D3", "margin": "md"})

    # Timestamp
    contents.append({"type": "text", "size": "xxs", "color": "#CCCCCC", "margin": "md",
                     "text": datetime.now().strftime('%d %b %H:%M')})

    return _wrap_bubble(trip_name, "#2C2C2C", contents)


def _build_route_bubble(route_data, direction, color, top_n):
    """Route card with top flights sorted by score."""
    flights = sorted(route_data['flights'], key=lambda f: f.get('total_score', 0), reverse=True)[:top_n]
    if not flights:
        return None

    rows = []
    for f in flights:
        bp = f.get('best_booking_price')
        src = f.get('best_booking_source', '')
        if bp and bp < f['price_thb']:
            price_line = f"฿{bp:,} ({src})"
            price_color = "#1DB446"
        else:
            price_line = f"฿{f['price_thb']:,}"
            price_color = "#999999" if f.get('is_excluded_airline') else "#111111"

        score_int = round(f.get('total_score', 0))
        label = score_label(score_int)
        s_color = "#1DB446" if score_int >= 16 else "#FF8C00" if score_int >= 12 else "#999999"

        dep = f.get('departure_time', '?')
        arr = f.get('arrival_time', '?')
        airline = f['airline'][:18]
        excluded = " ⚠️" if f.get('is_excluded_airline') else ""
        stops = "" if f.get('is_direct') else f" {f['num_stops']}stop"
        bag = f.get('checked_baggage', '')
        bag_s = "✓bag" if 'checked' in bag.lower() else "no bag"

        rows.append({
            "type": "box", "layout": "vertical", "spacing": "xs", "paddingBottom": "md",
            "contents": [
                {"type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": price_line, "size": "md", "weight": "bold",
                     "color": price_color, "flex": 5},
                    {"type": "text", "text": f"{label}", "size": "xxs", "weight": "bold",
                     "color": s_color, "flex": 2, "align": "end"},
                ]},
                {"type": "text", "text": f"{airline}{excluded}", "size": "xs", "color": "#666666"},
                {"type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": f"{dep}→{arr}", "size": "xxs", "color": "#AAAAAA", "flex": 3},
                    {"type": "text", "text": f"{bag_s}{stops}", "size": "xxs", "color": "#AAAAAA",
                     "flex": 2, "align": "end"},
                ]},
            ]
        })

    body = []
    for i, row in enumerate(rows):
        if i > 0:
            body.append({"type": "separator", "margin": "sm"})
        body.append(row)

    return {
        "type": "bubble", "size": "kilo",
        "header": {"type": "box", "layout": "vertical", "backgroundColor": color,
                   "paddingAll": "md", "contents": [
                       {"type": "text", "text": direction, "color": "#FFFFFF", "size": "xs", "weight": "bold"},
                       {"type": "text", "text": route_data['date_label'], "color": "#FFFFFF",
                        "size": "xl", "weight": "bold"},
                   ]},
        "body": {"type": "box", "layout": "vertical", "spacing": "sm",
                 "paddingAll": "md", "contents": body},
    }


def _add_flight_row(contents, direction, date_label, f):
    price = best_price(f)
    src = f.get('best_booking_source', '')
    dep = f.get('departure_time', '?')
    arr = f.get('arrival_time', '?')
    score_int = round(f.get('total_score', 0))
    label = score_label(score_int)

    contents.append({
        "type": "box", "layout": "vertical", "margin": "md",
        "contents": [
            {"type": "box", "layout": "horizontal", "contents": [
                {"type": "text", "text": f"{direction} {date_label}",
                 "size": "xxs", "color": "#AAAAAA", "flex": 4},
                {"type": "text", "text": label, "size": "xxs", "weight": "bold",
                 "color": "#1DB446" if score_int >= 16 else "#FF8C00",
                 "flex": 2, "align": "end"},
            ]},
            {"type": "text", "text": f"฿{price:,} {f['airline'][:18]}",
             "size": "sm", "weight": "bold"},
            {"type": "text", "text": f"{dep}→{arr}" + (f" via {src}" if src else ""),
             "size": "xxs", "color": "#999999"},
        ]
    })


def _wrap_bubble(title, bg_color, contents):
    return {
        "type": "bubble", "size": "kilo",
        "header": {"type": "box", "layout": "vertical", "backgroundColor": bg_color,
                   "paddingAll": "md", "contents": [
                       {"type": "text", "text": title, "color": "#FFFFFF",
                        "size": "xl", "weight": "bold"},
                   ]},
        "body": {"type": "box", "layout": "vertical", "spacing": "sm",
                 "paddingAll": "md", "contents": contents},
    }


# ─── Text Fallback ──────────────────────────────────────

def format_combined_message(route_results, top_n=5):
    from config import VALID_COMBOS
    lines = [f"Flight Update {datetime.now().strftime('%d %b %H:%M')}", ""]

    trips = group_by_trip(route_results)
    for trip_name, results in trips.items():
        lines.append(f"=== {trip_name} ===")
        for r in results:
            lines.append(f"[{r['route']}] {r['date_label']}")
            for f in sorted(r['flights'], key=lambda f: f['price_thb'])[:top_n]:
                dep = f.get('departure_time', '?')
                arr = f.get('arrival_time', '?')
                lines.append(f"  ฿{f['price_thb']:,} {f['airline'][:18]} {dep}-{arr}")
            lines.append("")

    return "\n".join(lines)
