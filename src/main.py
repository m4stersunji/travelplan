import logging
import os
import sys
from datetime import datetime

from config import SEARCH_ROUTES, VALID_COMBOS, EXCLUDED_AIRLINES, DB_PATH, DATA_DIR, LOG_DIR, TOP_N_FLIGHTS, SCRAPER_EXPIRY_DATE
from database import init_db, insert_scrape_run, insert_flight, get_previous_best_price, get_lowest_ever_price, get_scrape_count, insert_price_alert, get_price_history, get_average_price
from scraper import scrape_flights, classify_flight, score_flights
from notifier import send_line_notification, send_line_flex, build_flex_message, format_combined_message
from exporter import export_flights_to_csv
from sheets_exporter import push_to_sheets
from sheets_config import load_routes_from_sheet

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


def process_route(origin, destination, date, label, route_code, db_path, data_dir, **kwargs):
    """Process a single route. Returns a result dict for combined notification."""
    route = route_code
    date_label = datetime.strptime(date, '%Y-%m-%d').strftime('%d %b')

    raw_flights = scrape_flights(origin, destination, date)

    if not raw_flights:
        logger.warning(f"No flights found for {route} on {date}")
        insert_scrape_run(db_path, route=route, search_date=date, status='error')
        return {
            'route': route, 'search_date': date, 'date_label': date_label,
            'flights': [], 'prev_best': None, 'lowest_ever': None,
            'scrape_count': 0, 'price_history': [], 'success': False,
        }

    all_flights = []
    for f in raw_flights:
        classified = classify_flight(f, EXCLUDED_AIRLINES)
        all_flights.append(classified)

    # Keep only top N cheapest flights
    all_flights.sort(key=lambda f: f['price_thb'])
    flights = all_flights[:TOP_N_FLIGHTS]

    # Score flights — use config from Sheet if available
    direction = 'outbound' if route_code.startswith('BKK') else 'return'
    ideal_hour = kwargs.get('ideal_hour')
    score_mode = kwargs.get('score_mode')
    flights = score_flights(flights, direction, ideal_hour=ideal_hour, score_mode=score_mode)

    run_id = insert_scrape_run(db_path, route=route, search_date=date, status='success')
    for f in flights:
        insert_flight(
            db_path, scrape_run_id=run_id,
            airline=f.get('airline', ''), flight_number=f.get('flight_number', ''),
            departure_airport=f.get('departure_airport', ''), departure_time=f.get('departure_time', ''),
            arrival_airport=f.get('arrival_airport', ''), arrival_time=f.get('arrival_time', ''),
            duration_minutes=f.get('duration_minutes', 0), price_thb=f.get('price_thb', 0),
            aircraft_type=f.get('aircraft_type', ''), num_stops=f.get('num_stops', 0),
            is_direct=f.get('is_direct', False),
            is_excluded_airline=f.get('is_excluded_airline', False),
            best_booking_price=f.get('best_booking_price'),
            best_booking_source=f.get('best_booking_source'),
            cabin_baggage=f.get('cabin_baggage'),
            checked_baggage=f.get('checked_baggage'),
            service_type=f.get('service_type'),
            price_score=f.get('price_score'),
            time_score=f.get('time_score'),
            total_score=f.get('total_score'),
        )

    prev_best = get_previous_best_price(db_path, route, date)
    lowest_ever = get_lowest_ever_price(db_path, route, date)
    scrape_count = get_scrape_count(db_path, route, date)
    price_history = get_price_history(db_path, route, date, limit=10)
    avg_price = get_average_price(db_path, route, date)

    direct_prices = [f['price_thb'] for f in flights if f['is_direct'] and not f['is_excluded_airline'] and f['price_thb'] > 0]
    current_best = min(direct_prices) if direct_prices else None
    is_lowest = current_best is not None and (lowest_ever is None or current_best <= lowest_ever)

    insert_price_alert(db_path, run_id, route, date, current_best, prev_best, is_lowest)

    # Export CSV
    os.makedirs(data_dir, exist_ok=True)
    scraped_at = datetime.now().isoformat()
    flights_with_timestamp = [{**f, 'scraped_at': scraped_at} for f in flights]
    export_flights_to_csv(data_dir, route, date, flights_with_timestamp)

    logger.info(f"Done {route} {date}: {len(flights)} flights, best ฿{current_best:,}" if current_best else f"Done {route} {date}: {len(flights)} flights")

    return {
        'route': route, 'route_code': route_code,
        'search_date': date, 'date_label': date_label,
        'flights': flights, 'prev_best': prev_best, 'lowest_ever': lowest_ever,
        'scrape_count': scrape_count, 'price_history': price_history,
        'avg_price': avg_price, 'success': True,
        'trip_name': kwargs.get('trip_name', 'Default'),
        'score_mode': kwargs.get('score_mode', 'departure'),
    }


def main():
    setup_logging()

    # Auto-stop check
    if SCRAPER_EXPIRY_DATE:
        try:
            expiry = datetime.strptime(SCRAPER_EXPIRY_DATE, '%Y-%m-%d').date()
            if datetime.now().date() > expiry:
                logger.info(f"Scraper expired on {SCRAPER_EXPIRY_DATE}. To continue, update SCRAPER_EXPIRY_DATE in .env or config.py")
                return
        except ValueError:
            pass

    logger.info("=" * 60)
    logger.info(f"Starting flight price check at {datetime.now().isoformat()}")
    logger.info("=" * 60)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    init_db(DB_PATH)

    # Load routes: try Sheet config first, fall back to config.py
    sheet_routes, sheet_combos = load_routes_from_sheet()
    if sheet_routes:
        active_routes = sheet_routes
        # Temporarily override VALID_COMBOS for this run
        import config as cfg
        cfg.VALID_COMBOS = sheet_combos
        logger.info(f"Using {len(active_routes)} routes from Google Sheets Config")
    else:
        active_routes = SEARCH_ROUTES
        logger.info(f"Using {len(active_routes)} routes from config.py (Sheet config not available)")

    # Collect all results
    route_results = []
    for route in active_routes:
        result = process_route(
            origin=route['origin'],
            destination=route['destination'],
            date=route['date'],
            label=route['label'],
            route_code=route.get('route_code', ''),
            db_path=DB_PATH,
            data_dir=DATA_DIR,
            ideal_hour=route.get('ideal_hour'),
            score_mode=route.get('score_mode'),
            trip_name=route.get('trip_name', 'Default'),
        )
        route_results.append(result)

    # Get current valid combos
    import config as cfg
    current_combos = cfg.VALID_COMBOS

    # Send ONE combined LINE notification (Flex card, fallback to text)
    successful = [r for r in route_results if r['success']]
    if successful:
        flex = build_flex_message(successful, current_combos)
        if not send_line_flex(flex):
            logger.warning("Flex message failed, falling back to text")
            message = format_combined_message(successful)
            send_line_notification(message)
    else:
        logger.warning("No successful scrapes — skipping notification")

    # Push to Google Sheets
    if successful:
        push_to_sheets(successful, current_combos)

    # Summary log
    logger.info("=" * 60)
    for r in route_results:
        status = "OK" if r['success'] else "FAIL"
        logger.info(f"  {status} {r['route']} {r['search_date']}")
    logger.info("=" * 60)
    logger.info("Done.")


if __name__ == '__main__':
    main()
