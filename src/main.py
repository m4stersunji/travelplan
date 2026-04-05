import logging
import os
import sys
from datetime import datetime

from config import SEARCH_ROUTES, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END, DB_PATH, DATA_DIR, LOG_DIR
from database import init_db, insert_scrape_run, insert_flight, get_previous_best_price, get_lowest_ever_price, get_scrape_count, insert_price_alert
from scraper import scrape_flights, classify_flight
from notifier import send_line_notification, format_notification_message
from exporter import export_flights_to_csv

logger = logging.getLogger(__name__)


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"scraper_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ]
    )


def process_route(origin, destination, date, label, db_path, data_dir):
    route = f"{origin}-{destination}"

    raw_flights = scrape_flights(origin, destination, date)

    if not raw_flights:
        logger.warning(f"No flights found for {route} on {date}")
        insert_scrape_run(db_path, route=route, search_date=date, status='error')
        return False

    flights = []
    for f in raw_flights:
        classified = classify_flight(f, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END)
        flights.append(classified)

    run_id = insert_scrape_run(db_path, route=route, search_date=date, status='success')
    for f in flights:
        insert_flight(
            db_path, scrape_run_id=run_id,
            airline=f.get('airline', ''), flight_number=f.get('flight_number', ''),
            departure_time=f.get('departure_time', ''), arrival_time=f.get('arrival_time', ''),
            duration_minutes=f.get('duration_minutes', 0), price_thb=f.get('price_thb', 0),
            aircraft_type=f.get('aircraft_type', ''), num_stops=f.get('num_stops', 0),
            is_direct=f.get('is_direct', False),
            is_excluded_airline=f.get('is_excluded_airline', False),
            is_preferred_time=f.get('is_preferred_time', False),
        )

    prev_best = get_previous_best_price(db_path, route, date)
    lowest_ever = get_lowest_ever_price(db_path, route, date)
    scrape_count = get_scrape_count(db_path, route, date)

    direct_prices = [f['price_thb'] for f in flights if f['is_direct'] and not f['is_excluded_airline'] and f['price_thb'] > 0]
    current_best = min(direct_prices) if direct_prices else None
    is_lowest = current_best is not None and (lowest_ever is None or current_best <= lowest_ever)

    insert_price_alert(db_path, run_id, route, date, current_best, prev_best, is_lowest)

    date_label = datetime.strptime(date, '%Y-%m-%d').strftime('%d %b')
    route_display = f"{origin}→{destination}"
    message = format_notification_message(
        route=route_display, search_date=date_label,
        flights=flights, prev_best_price=prev_best,
        lowest_ever=lowest_ever, scrape_count=scrape_count,
    )
    send_line_notification(message)

    os.makedirs(data_dir, exist_ok=True)
    scraped_at = datetime.now().isoformat()
    flights_with_timestamp = [{**f, 'scraped_at': scraped_at} for f in flights]
    export_flights_to_csv(data_dir, route, date, flights_with_timestamp)

    logger.info(f"Done {route} {date}: {len(flights)} flights, best ฿{current_best:,}" if current_best else f"Done {route} {date}: {len(flights)} flights (no direct non-excluded)")
    return True


def main():
    setup_logging()
    logger.info("=" * 60)
    logger.info(f"Starting flight price check at {datetime.now().isoformat()}")
    logger.info("=" * 60)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    init_db(DB_PATH)

    results = []
    for route in SEARCH_ROUTES:
        success = process_route(
            origin=route['origin'],
            destination=route['destination'],
            date=route['date'],
            label=route['label'],
            db_path=DB_PATH,
            data_dir=DATA_DIR,
        )
        results.append((route['label'], success))

    logger.info("=" * 60)
    for label, success in results:
        status = "OK" if success else "FAIL"
        logger.info(f"  {status} {label}")
    logger.info("=" * 60)
    logger.info("Done.")


if __name__ == '__main__':
    main()
