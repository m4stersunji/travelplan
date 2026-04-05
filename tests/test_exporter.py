import sys
import os
import csv
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from exporter import export_flights_to_csv


def test_export_creates_csv_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        flights = [
            {
                'airline': 'Thai AirAsia', 'flight_number': 'FD636',
                'departure_time': '10:15', 'arrival_time': '12:15',
                'duration_minutes': 120, 'price_thb': 3250,
                'aircraft_type': 'A320', 'num_stops': 0,
                'is_direct': True, 'is_excluded_airline': False,
                'is_preferred_time': True, 'scraped_at': '2026-04-05T14:00:00',
            },
        ]
        filepath = export_flights_to_csv(tmpdir, 'BKK-DAD', '2026-05-29', flights)
        assert os.path.exists(filepath)
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['airline'] == 'Thai AirAsia'
        assert rows[0]['price_thb'] == '3250'


def test_export_appends_to_existing_csv():
    with tempfile.TemporaryDirectory() as tmpdir:
        flights1 = [
            {
                'airline': 'AirAsia', 'flight_number': 'FD1',
                'departure_time': '10:00', 'arrival_time': '12:00',
                'duration_minutes': 120, 'price_thb': 4000,
                'aircraft_type': 'A320', 'num_stops': 0,
                'is_direct': True, 'is_excluded_airline': False,
                'is_preferred_time': True, 'scraped_at': '2026-04-05T10:00:00',
            },
        ]
        flights2 = [
            {
                'airline': 'VietJet', 'flight_number': 'VZ1',
                'departure_time': '09:00', 'arrival_time': '11:00',
                'duration_minutes': 120, 'price_thb': 3500,
                'aircraft_type': 'A321', 'num_stops': 0,
                'is_direct': True, 'is_excluded_airline': False,
                'is_preferred_time': True, 'scraped_at': '2026-04-05T14:00:00',
            },
        ]
        export_flights_to_csv(tmpdir, 'BKK-DAD', '2026-05-29', flights1)
        filepath = export_flights_to_csv(tmpdir, 'BKK-DAD', '2026-05-29', flights2)
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
