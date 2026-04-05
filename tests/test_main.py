import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import patch
from main import process_route


def test_process_route_with_mock_scraper():
    mock_flights = [
        {
            'airline': 'Thai AirAsia', 'flight_number': '',
            'departure_airport': 'DMK', 'departure_time': '07:50',
            'arrival_airport': 'DAD', 'arrival_time': '09:30',
            'duration_minutes': 100, 'price_thb': 3370,
            'aircraft_type': 'A320', 'num_stops': 0,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        data_dir = tmpdir

        with patch('main.scrape_flights', return_value=mock_flights):
            from database import init_db
            init_db(db_path)

            result = process_route(
                origin='Bangkok', destination='Danang', date='2026-05-29',
                label='BKK-DAD-May29', route_code='BKK-DAD',
                db_path=db_path, data_dir=data_dir
            )

            assert result['success'] is True
            assert len(result['flights']) == 1
            assert result['route'] == 'BKK-DAD'


def test_process_route_scraper_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        data_dir = tmpdir

        with patch('main.scrape_flights', return_value=[]):
            from database import init_db
            init_db(db_path)

            result = process_route(
                origin='Bangkok', destination='Danang', date='2026-05-29',
                label='BKK-DAD-May29', route_code='BKK-DAD',
                db_path=db_path, data_dir=data_dir
            )

            assert result['success'] is False
