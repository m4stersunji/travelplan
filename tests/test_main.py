import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import patch
from main import process_route


def test_process_route_with_mock_scraper():
    mock_flights = [
        {
            'airline': 'Thai AirAsia', 'flight_number': 'FD636',
            'departure_time': '10:15', 'arrival_time': '12:15',
            'duration_minutes': 120, 'price_thb': 3250,
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
                origin='BKK', destination='DAD', date='2026-05-29',
                label='BKK-DAD-May29', db_path=db_path, data_dir=data_dir
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
                origin='BKK', destination='DAD', date='2026-05-29',
                label='BKK-DAD-May29', db_path=db_path, data_dir=data_dir
            )

            assert result['success'] is False
