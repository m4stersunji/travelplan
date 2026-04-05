import logging
import requests
from datetime import datetime

from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

logger = logging.getLogger(__name__)

LINE_API_URL = "https://api.line.me/v2/bot/message/push"


def send_line_notification(message):
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


def format_combined_message(route_results, top_n=5):
    """Format a single combined message for all route/date combos.

    route_results: list of dicts with keys:
        route, search_date, date_label, flights, prev_best, lowest_ever,
        scrape_count, price_history
    """
    lines = [f"BKK-DAD Price Update"]
    lines.append(f"{datetime.now().strftime('%d %b %H:%M')}")
    lines.append("")

    # Group by direction
    outbound = [r for r in route_results if r['route'].startswith('BKK')]
    inbound = [r for r in route_results if r['route'].startswith('DAD')]

    # --- OUTBOUND ---
    if outbound:
        lines.append("OUTBOUND BKK > DAD")
        lines.append("-" * 28)
        for r in outbound:
            lines.append(f"  {r['date_label']}")
            all_flights = sorted(r['flights'], key=lambda f: f['price_thb'])[:top_n]
            if not all_flights:
                lines.append("  No flights found")
            for f in all_flights:
                price = f"฿{f['price_thb']:,}"
                change = format_price_change(f['price_thb'], r['prev_best'])
                direct = "" if f['is_direct'] else f" ({f['num_stops']}stop)"
                excluded = " *" if f['is_excluded_airline'] else ""
                pref = " <<" if f.get('is_preferred_time') else ""
                airline = f['airline'][:18]
                lines.append(f"  {price:>8} {change:>6} {airline}{direct}{excluded}{pref}")
            lines.append("")

    # --- INBOUND ---
    if inbound:
        lines.append("RETURN DAD > BKK")
        lines.append("-" * 28)
        for r in inbound:
            lines.append(f"  {r['date_label']}")
            all_flights = sorted(r['flights'], key=lambda f: f['price_thb'])[:top_n]
            if not all_flights:
                lines.append("  No flights found")
            for f in all_flights:
                price = f"฿{f['price_thb']:,}"
                change = format_price_change(f['price_thb'], r['prev_best'])
                direct = "" if f['is_direct'] else f" ({f['num_stops']}stop)"
                excluded = " *" if f['is_excluded_airline'] else ""
                airline = f['airline'][:18]
                lines.append(f"  {price:>8} {change:>6} {airline}{direct}{excluded}")
            lines.append("")

    # --- BEST COMBO ---
    best_combos = _find_best_combos(outbound, inbound)
    if best_combos:
        lines.append("BEST ROUNDTRIP")
        lines.append("-" * 28)
        for combo in best_combos[:3]:
            lines.append(f"  ฿{combo['total']:,} = {combo['out_date']} ฿{combo['out_price']:,} + {combo['in_date']} ฿{combo['in_price']:,}")
        lines.append("")

    # --- HISTORICAL SUMMARY ---
    lines.append("HISTORY")
    lines.append("-" * 28)
    for r in route_results:
        if r['lowest_ever'] is not None:
            trend = _get_trend(r.get('price_history', []))
            lines.append(f"  {r['date_label']}: low ฿{r['lowest_ever']:,} {trend} ({r['scrape_count']} checks)")
    lines.append("")

    # Legend
    lines.append("* = excluded airline | << = preferred time")

    return "\n".join(lines)


def _find_best_combos(outbound, inbound):
    """Find cheapest roundtrip combinations."""
    combos = []
    for out_r in outbound:
        out_direct = [f for f in out_r['flights'] if f['is_direct'] and not f['is_excluded_airline'] and f['price_thb'] > 0]
        if not out_direct:
            continue
        best_out = min(out_direct, key=lambda f: f['price_thb'])

        for in_r in inbound:
            in_direct = [f for f in in_r['flights'] if f['is_direct'] and not f['is_excluded_airline'] and f['price_thb'] > 0]
            if not in_direct:
                continue
            best_in = min(in_direct, key=lambda f: f['price_thb'])

            combos.append({
                'total': best_out['price_thb'] + best_in['price_thb'],
                'out_date': out_r['date_label'],
                'out_price': best_out['price_thb'],
                'in_date': in_r['date_label'],
                'in_price': best_in['price_thb'],
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
    # Compare newest vs oldest in history
    newest = prices[0]
    oldest = prices[-1]
    if newest < oldest:
        return "trending down"
    elif newest > oldest:
        return "trending up"
    else:
        return "stable"
