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
        # Use score_mode to detect direction (set by sheets_config)
        outbound = [r for r in results if r.get('score_mode') == 'departure']
        inbound = [r for r in results if r.get('score_mode') == 'arrival']

        # Fallback: if score_mode not set, use route_code
        if not outbound and not inbound:
            codes = list(set(r.get('route_code', '') for r in results))
            if len(codes) >= 2:
                outbound = [r for r in results if r.get('route_code') == codes[0]]
                inbound = [r for r in results if r.get('route_code') != codes[0]]
            else:
                outbound = results
                inbound = []

        # Summary bubble
        summary = _build_summary(trip_name, outbound, inbound, results, valid_combos)
        if summary:
            bubbles.append(summary)

        # Route bubbles with trip name in header
        for r in outbound:
            b = _build_route_bubble(r, "GO", "#1DB446", top_n, trip_name)
            if b:
                bubbles.append(b)
        for r in inbound:
            b = _build_route_bubble(r, "BACK", "#0367D3", top_n, trip_name)
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

    # Best direct deal
    contents.append({"type": "text", "text": "BEST DIRECT", "size": "xxs", "color": "#AAAAAA"})
    contents.append({"type": "text", "text": f"฿{combo['total']:,} roundtrip",
                     "size": "xxl", "weight": "bold", "color": "#1DB446"})

    _add_flight_row(contents, "GO", combo['go_route']['date_label'], go)
    _add_flight_row(contents, "BACK", combo['back_route']['date_label'], back)

    # Best transit deal (may be cheaper)
    transit_combo = _find_cheapest_transit_combo(outbound, inbound, valid_combos)
    if transit_combo and transit_combo['total'] < combo['total']:
        saving = combo['total'] - transit_combo['total']
        contents.append({"type": "separator", "margin": "md"})
        contents.append({"type": "text", "text": f"CHEAPEST (transit, save ฿{saving:,})",
                         "size": "xxs", "color": "#FF8C00", "margin": "md"})
        contents.append({"type": "text", "text": f"฿{transit_combo['total']:,} roundtrip",
                         "size": "lg", "weight": "bold", "color": "#FF8C00"})
        _add_flight_row(contents, "GO", transit_combo['go_route']['date_label'], transit_combo['go_flight'])
        _add_flight_row(contents, "BACK", transit_combo['back_route']['date_label'], transit_combo['back_flight'])

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


def _build_route_bubble(route_data, direction, color, top_n, trip_name=""):
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
        dur = f.get('duration_text', '')

        # Transit info
        if f.get('is_direct'):
            route_line = f"{dep}→{arr}" + (f" ({dur})" if dur else "")
        else:
            layover = f.get('layover_airport', '')[:15]
            lay_dur = f.get('layover_duration', '')
            via = f" via {layover}" if layover else ""
            route_line = f"{dep}→{arr} {f['num_stops']}stop{via}"

        # Baggage with actual kg
        cabin = f.get('cabin_baggage', '').replace(' carry-on', '')
        checked = f.get('checked_baggage', '')
        if 'No checked' in checked or 'no bag' in checked.lower():
            bag_line = f"Cabin {cabin} only (+luggage fee)"
            bag_color = "#E53935"
        else:
            checked_kg = checked.replace(' checked', '')
            bag_line = f"Cabin {cabin} + Luggage {checked_kg}"
            bag_color = "#AAAAAA"

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
                {"type": "text", "text": route_line, "size": "xxs", "color": "#AAAAAA"},
                {"type": "text", "text": bag_line, "size": "xxs", "color": bag_color},
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
                       {"type": "text", "text": f"{trip_name} {direction}" if trip_name else direction,
                        "color": "#FFFFFF", "size": "xs", "weight": "bold"},
                       {"type": "text", "text": f"{route_data['date_label']} {route_data.get('route_code', '')}",
                        "color": "#FFFFFF", "size": "lg", "weight": "bold"},
                   ]},
        "body": {"type": "box", "layout": "vertical", "spacing": "sm",
                 "paddingAll": "md", "contents": body},
    }


def _find_cheapest_transit_combo(outbound, inbound, valid_combos):
    """Find cheapest roundtrip including transit flights."""
    out_by_date = {r['search_date']: r for r in outbound}
    in_by_date = {r['search_date']: r for r in inbound}

    combos = []
    for go_date, back_date in valid_combos:
        out_r = out_by_date.get(go_date)
        in_r = in_by_date.get(back_date)
        if not out_r or not in_r:
            continue

        # All flights with price > 0 (not just direct)
        go_all = [f for f in out_r.get('flights', []) if f.get('price_thb', 0) > 0 and not f.get('is_excluded_airline')]
        back_all = [f for f in in_r.get('flights', []) if f.get('price_thb', 0) > 0 and not f.get('is_excluded_airline')]
        if not go_all or not back_all:
            continue

        cheapest_go = min(go_all, key=best_price)
        cheapest_back = min(back_all, key=best_price)

        combos.append({
            'go_flight': cheapest_go,
            'back_flight': cheapest_back,
            'go_route': out_r,
            'back_route': in_r,
            'total': best_price(cheapest_go) + best_price(cheapest_back),
        })

    if not combos:
        return None
    return min(combos, key=lambda c: c['total'])


def _add_flight_row(contents, direction, date_label, f):
    price = best_price(f)
    src = f.get('best_booking_source', '')
    dep = f.get('departure_time', '?')
    arr = f.get('arrival_time', '?')
    score_int = round(f.get('total_score', 0))
    label = score_label(score_int)

    # Route info
    if f.get('is_direct'):
        dur = f.get('duration_text', '')
        route_text = f"Direct {dep}→{arr}" + (f" ({dur})" if dur else "")
    else:
        layover = f.get('layover_airport', '')[:15]
        lay_dur = f.get('layover_duration', '')
        via = f" via {layover}" if layover else ""
        wait = f" wait {lay_dur}" if lay_dur else ""
        route_text = f"{dep}→{arr} {f.get('num_stops',1)}stop{via}{wait}"

    # Booking source
    src_text = f"Book: {src}" if src else ""

    # Baggage
    cabin = f.get('cabin_baggage', '').replace(' carry-on', '')
    checked = f.get('checked_baggage', '')
    if 'No checked' in checked or 'no bag' in checked.lower():
        bag_text = f"{cabin} only (+luggage fee)"
    else:
        checked_kg = checked.replace(' checked', '')
        bag_text = f"{cabin} + {checked_kg}"

    row_contents = [
        {"type": "box", "layout": "horizontal", "contents": [
            {"type": "text", "text": f"{direction} {date_label}",
             "size": "xxs", "color": "#AAAAAA", "flex": 4},
            {"type": "text", "text": label, "size": "xxs", "weight": "bold",
             "color": "#1DB446" if score_int >= 16 else "#FF8C00",
             "flex": 2, "align": "end"},
        ]},
        {"type": "text", "text": f"฿{price:,} {f['airline'][:18]}",
         "size": "sm", "weight": "bold"},
        {"type": "text", "text": route_text, "size": "xxs", "color": "#999999", "wrap": True},
        {"type": "text", "text": bag_text,
         "size": "xxs", "color": "#E53935" if "+luggage fee" in bag_text else "#999999"},
    ]

    if src_text:
        row_contents.append({"type": "text", "text": src_text, "size": "xxs", "color": "#0367D3"})

    contents.append({"type": "box", "layout": "vertical", "margin": "md", "contents": row_contents})


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
