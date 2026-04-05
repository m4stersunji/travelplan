import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scraper import build_google_flights_url, parse_flight_data, classify_flight
from config import EXCLUDED_AIRLINES


def test_build_google_flights_url():
    url = build_google_flights_url(origin='Bangkok', destination='Danang', date='2026-05-29')
    assert 'google.com/travel/flights' in url
    assert 'Bangkok' in url
    assert 'Danang' in url


def test_classify_flight_direct():
    flight = {'airline': 'Thai AirAsia', 'num_stops': 0, 'departure_time': '10:15'}
    classified = classify_flight(flight, EXCLUDED_AIRLINES)
    assert classified['is_direct'] is True
    assert classified['is_excluded_airline'] is False


def test_classify_flight_excluded_airline():
    flight = {'airline': 'Emirates', 'num_stops': 1, 'departure_time': '08:00'}
    classified = classify_flight(flight, EXCLUDED_AIRLINES)
    assert classified['is_direct'] is False
    assert classified['is_excluded_airline'] is True


def test_classify_flight_non_excluded():
    flight = {'airline': 'VietJet', 'num_stops': 0, 'departure_time': '15:30'}
    classified = classify_flight(flight, EXCLUDED_AIRLINES)
    assert classified['is_direct'] is True
    assert classified['is_excluded_airline'] is False


def test_parse_flight_data_returns_list():
    result = parse_flight_data("")
    assert isinstance(result, list)
    assert len(result) == 0
