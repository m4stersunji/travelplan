import logging
import requests

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
        return "🆕 NEW"
    diff = current_price - previous_price
    if diff < 0:
        return f"▼ -{abs(diff):,}"
    elif diff > 0:
        return f"▲ +{diff:,}"
    else:
        return "— same"


def format_notification_message(route, search_date, flights, prev_best_price,
                                lowest_ever, scrape_count):
    if not flights:
        return f"✈️ {route} {search_date}\n\n❌ No flights found this check."

    direct_flights = [f for f in flights if f['is_direct'] and not f['is_excluded_airline']]
    other_flights = [f for f in flights if not f['is_direct'] or f['is_excluded_airline']]

    direct_flights.sort(key=lambda f: f['price_thb'])
    other_flights.sort(key=lambda f: f['price_thb'])

    lines = [f"✈️ Flight Price Update — {route} {search_date}", ""]

    if direct_flights:
        best = direct_flights[0]
        change = format_price_change(best['price_thb'], prev_best_price)
        is_lowest = best['price_thb'] <= lowest_ever if lowest_ever else True

        lines.append(f"🏆 Best Deal: {best['airline']} | {best['flight_number']}")
        lines.append(f"   ฿{best['price_thb']:,} ({change})")
        if is_lowest:
            lines.append("   ⭐ LOWEST EVER")
        lines.append(f"   Depart {best['departure_time']} → Arrive {best['arrival_time']}")
        lines.append(f"   Aircraft: {best['aircraft_type'] or 'N/A'}")
        lines.append("")

        if len(direct_flights) > 1:
            lines.append("📊 Other Direct Flights:")
            for f in direct_flights[1:]:
                change = format_price_change(f['price_thb'], prev_best_price)
                pref = " ⏰" if f['is_preferred_time'] else ""
                lines.append(
                    f"   {f['airline']} {f['flight_number']} | "
                    f"฿{f['price_thb']:,} ({change}) | "
                    f"{f['departure_time']}→{f['arrival_time']} | "
                    f"{f['aircraft_type'] or 'N/A'}{pref}"
                )
            lines.append("")

    if other_flights:
        lines.append("📌 With Stops / Excluded Airlines (FYI):")
        for f in other_flights:
            stop_info = f"({f['num_stops']} stop)" if f['num_stops'] > 0 else "(direct)"
            lines.append(
                f"   {f['airline']} {f['flight_number']} | "
                f"฿{f['price_thb']:,} {stop_info} | "
                f"{f['departure_time']}→{f['arrival_time']} | "
                f"{f['aircraft_type'] or 'N/A'}"
            )
        lines.append("")

    from datetime import datetime
    lines.append(f"🕐 Checked: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"📈 Tracking: {scrape_count} checks so far")

    return "\n".join(lines)
