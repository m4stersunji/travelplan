import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from notifier import format_price_change, format_notification_message


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
    assert '—' in result


def test_format_price_change_no_previous():
    result = format_price_change(3600, None)
    assert 'NEW' in result


def test_format_notification_message():
    flights = [
        {
            'airline': 'Thai AirAsia', 'flight_number': 'FD636',
            'departure_time': '10:15', 'arrival_time': '12:15',
            'price_thb': 3250, 'aircraft_type': 'A320', 'num_stops': 0,
            'is_direct': True, 'is_excluded_airline': False, 'is_preferred_time': True,
        },
        {
            'airline': 'Emirates', 'flight_number': 'EK374',
            'departure_time': '08:00', 'arrival_time': '16:30',
            'price_thb': 2900, 'aircraft_type': '777', 'num_stops': 1,
            'is_direct': False, 'is_excluded_airline': True, 'is_preferred_time': False,
        },
    ]
    msg = format_notification_message(
        route='BKK→DAD', search_date='29 May',
        flights=flights, prev_best_price=3600,
        lowest_ever=3250, scrape_count=10
    )
    assert 'Thai AirAsia' in msg
    assert 'FD636' in msg
    assert '3,250' in msg
    assert 'Emirates' in msg
    assert 'LOWEST EVER' in msg or '⭐' in msg
