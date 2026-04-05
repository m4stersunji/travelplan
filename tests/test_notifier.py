import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from notifier import format_price_change, format_combined_message


def test_format_price_change_decrease():
    result = format_price_change(3250, 3600)
    assert '▼' in result
    assert '350' in result


def test_format_price_change_increase():
    result = format_price_change(3800, 3600)
    assert '▲' in result
    assert '200' in result


def test_format_price_change_same():
    result = format_price_change(3600, 3600)
    assert '=' in result


def test_format_price_change_no_previous():
    result = format_price_change(3600, None)
    assert 'NEW' in result


def test_format_combined_message():
    route_results = [
        {
            'route': 'BKK-DAD', 'search_date': '2026-05-29', 'date_label': '29 May',
            'flights': [
                {'airline': 'Vietnam Airlines', 'flight_number': '', 'departure_time': '18:05',
                 'arrival_time': '19:45', 'price_thb': 5335, 'aircraft_type': '', 'num_stops': 0,
                 'is_direct': True, 'is_excluded_airline': False, 'is_preferred_time': False},
                {'airline': 'Emirates', 'flight_number': '', 'departure_time': '20:10',
                 'arrival_time': '21:50', 'price_thb': 5935, 'aircraft_type': '', 'num_stops': 0,
                 'is_direct': True, 'is_excluded_airline': True, 'is_preferred_time': False},
            ],
            'prev_best': 5500, 'lowest_ever': 5335, 'scrape_count': 3,
            'price_history': [{'best_price': 5335}, {'best_price': 5500}],
        },
        {
            'route': 'DAD-BKK', 'search_date': '2026-06-01', 'date_label': '01 Jun',
            'flights': [
                {'airline': 'Vietnam Airlines', 'flight_number': '', 'departure_time': '10:00',
                 'arrival_time': '11:40', 'price_thb': 4508, 'aircraft_type': '', 'num_stops': 0,
                 'is_direct': True, 'is_excluded_airline': False, 'is_preferred_time': False},
            ],
            'prev_best': 4700, 'lowest_ever': 4508, 'scrape_count': 3,
            'price_history': [{'best_price': 4508}, {'best_price': 4700}],
        },
    ]
    msg = format_combined_message(route_results)
    assert 'BKK' in msg
    assert 'Vietnam Airlines' in msg
    assert '5,335' in msg
    assert 'Emirates' in msg
    assert 'BEST ROUNDTRIP' in msg
    assert '9,843' in msg  # 5335 + 4508
    assert 'HISTORY' in msg
    assert 'trending down' in msg


def test_format_combined_message_no_flights():
    route_results = [
        {
            'route': 'BKK-DAD', 'search_date': '2026-05-29', 'date_label': '29 May',
            'flights': [], 'prev_best': None, 'lowest_ever': None,
            'scrape_count': 0, 'price_history': [],
        },
    ]
    msg = format_combined_message(route_results)
    assert 'No flights found' in msg
