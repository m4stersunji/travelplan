import csv
import os
import logging

logger = logging.getLogger(__name__)

CSV_FIELDS = [
    'scraped_at', 'airline', 'flight_number', 'departure_time', 'arrival_time',
    'duration_minutes', 'price_thb', 'aircraft_type', 'num_stops',
    'is_direct', 'is_excluded_airline', 'is_preferred_time',
]


def export_flights_to_csv(data_dir, route, search_date, flights):
    filename = f"{route}-{search_date}.csv"
    filepath = os.path.join(data_dir, filename)
    file_exists = os.path.exists(filepath)

    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        for flight in flights:
            writer.writerow(flight)

    logger.info(f"Exported {len(flights)} flights to {filepath}")
    return filepath
