import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scraper import build_google_flights_url, parse_flight_data, classify_flight
from config import EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END


def test_build_google_flights_url():
    url = build_google_flights_url(origin='BKK', destination='DAD', date='2026-05-29')
    assert 'google.com/travel/flights' in url
    assert 'BKK' in url
    assert 'DAD' in url


def test_classify_flight_direct_preferred():
    flight = {'airline': 'Thai AirAsia', 'num_stops': 0, 'departure_time': '10:15'}
    classified = classify_flight(flight, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END)
    assert classified['is_direct'] is True
    assert classified['is_excluded_airline'] is False
    assert classified['is_preferred_time'] is True


def test_classify_flight_excluded_airline():
    flight = {'airline': 'Emirates', 'num_stops': 1, 'departure_time': '08:00'}
    classified = classify_flight(flight, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END)
    assert classified['is_direct'] is False
    assert classified['is_excluded_airline'] is True
    assert classified['is_preferred_time'] is False


def test_classify_flight_outside_preferred_time():
    flight = {'airline': 'VietJet', 'num_stops': 0, 'departure_time': '15:30'}
    classified = classify_flight(flight, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START, PREFERRED_DEPARTURE_END)
    assert classified['is_direct'] is True
    assert classified['is_excluded_airline'] is False
    assert classified['is_preferred_time'] is False


def test_parse_flight_data_returns_list():
    result = parse_flight_data("")
    assert isinstance(result, list)
    assert len(result) == 0
