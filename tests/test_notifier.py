import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from notifier import format_price_change, format_combined_message, build_flex_message


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


def _make_route_results():
    return [
        {
            'route': 'BKK-DAD', 'search_date': '2026-05-29', 'date_label': '29 May',
            'flights': [
                {'airline': 'Thai AirAsia', 'departure_airport': 'DMK', 'departure_time': '07:50',
                 'arrival_airport': 'DAD', 'arrival_time': '09:30', 'price_thb': 3370,
                 'aircraft_type': 'A320', 'num_stops': 0, 'is_direct': True,
                 'is_excluded_airline': False},
                {'airline': 'Vietnam Airlines', 'departure_airport': 'BKK', 'departure_time': '18:05',
                 'arrival_airport': 'DAD', 'arrival_time': '19:45', 'price_thb': 5335,
                 'aircraft_type': '', 'num_stops': 0, 'is_direct': True,
                 'is_excluded_airline': False},
            ],
            'prev_best': 3500, 'lowest_ever': 3370, 'scrape_count': 3,
            'price_history': [{'best_price': 3370}, {'best_price': 3500}],
        },
        {
            'route': 'DAD-BKK', 'search_date': '2026-06-01', 'date_label': '01 Jun',
            'flights': [
                {'airline': 'Vietnam Airlines', 'departure_airport': 'DAD', 'departure_time': '10:00',
                 'arrival_airport': 'BKK', 'arrival_time': '11:40', 'price_thb': 4508,
                 'aircraft_type': '', 'num_stops': 0, 'is_direct': True,
                 'is_excluded_airline': False},
            ],
            'prev_best': 4700, 'lowest_ever': 4508, 'scrape_count': 3,
            'price_history': [{'best_price': 4508}, {'best_price': 4700}],
        },
    ]


def test_format_combined_message():
    msg = format_combined_message(_make_route_results())
    assert 'Thai AirAsia' in msg
    assert '3,370' in msg
    assert 'Vietnam Airlines' in msg
    assert 'BEST COMBO' in msg


def test_build_flex_message():
    flex = build_flex_message(_make_route_results())
    assert flex['type'] == 'carousel'
    assert len(flex['contents']) >= 2  # at least outbound + summary
    # Check outbound bubble has header
    assert flex['contents'][0]['header']['contents'][0]['text'] == 'OUTBOUND'


def test_format_combined_message_no_flights():
    route_results = [
        {
            'route': 'BKK-DAD', 'search_date': '2026-05-29', 'date_label': '29 May',
            'flights': [], 'prev_best': None, 'lowest_ever': None,
            'scrape_count': 0, 'price_history': [],
        },
    ]
    msg = format_combined_message(route_results)
    assert 'BKK-DAD' in msg
