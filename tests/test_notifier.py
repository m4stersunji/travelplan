import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flight_utils import best_price, get_trend, verdict_string, score_label, eligible_flights
from notifier import build_flex_message


def test_best_price_with_booking():
    f = {'price_thb': 3370, 'best_booking_price': 3076}
    assert best_price(f) == 3076


def test_best_price_without_booking():
    f = {'price_thb': 3370}
    assert best_price(f) == 3370


def test_get_trend_falling():
    history = [{'best_price': 3000}, {'best_price': 3500}]
    assert get_trend(history) == "Falling"


def test_get_trend_rising():
    history = [{'best_price': 3500}, {'best_price': 3000}]
    assert get_trend(history) == "Rising"


def test_verdict_collecting():
    v = verdict_string(3000, 3200, 2900, "Stable", 54, 1)
    assert "Collecting" in v


def test_verdict_buy():
    v = verdict_string(2950, 3200, 2900, "Stable", 54, 5)
    assert "BUY" in v


def test_score_label():
    assert score_label(17) == "Excellent"
    assert score_label(13) == "Good"
    assert score_label(9) == "Fair"
    assert score_label(5) == "Poor"


def test_eligible_flights():
    flights = [
        {'is_direct': True, 'is_excluded_airline': False, 'price_thb': 3000},
        {'is_direct': False, 'is_excluded_airline': False, 'price_thb': 2000},
        {'is_direct': True, 'is_excluded_airline': True, 'price_thb': 1500},
    ]
    result = eligible_flights(flights)
    assert len(result) == 1
    assert result[0]['price_thb'] == 3000


def _make_route_results():
    return [
        {
            'route': 'BKK-DAD', 'route_code': 'BKK-DAD',
            'search_date': '2026-05-29', 'date_label': '29 May',
            'trip_name': 'Danang',
            'flights': [
                {'airline': 'Thai AirAsia', 'departure_airport': 'DMK', 'departure_time': '07:50',
                 'arrival_airport': 'DAD', 'arrival_time': '09:30', 'price_thb': 3370,
                 'best_booking_price': 3076, 'best_booking_source': 'Agoda',
                 'aircraft_type': 'A320', 'num_stops': 0, 'is_direct': True,
                 'is_excluded_airline': False, 'checked_baggage': 'No checked bag',
                 'total_score': 15.5, 'price_score': 10, 'time_score': 5.5},
            ],
            'prev_best': 3500, 'lowest_ever': 3370, 'scrape_count': 3,
            'avg_price': 3400,
            'price_history': [{'best_price': 3370}, {'best_price': 3500}],
        },
        {
            'route': 'DAD-BKK', 'route_code': 'DAD-BKK',
            'search_date': '2026-06-01', 'date_label': '01 Jun',
            'trip_name': 'Danang',
            'flights': [
                {'airline': 'Vietnam Airlines', 'departure_airport': 'DAD', 'departure_time': '16:00',
                 'arrival_airport': 'BKK', 'arrival_time': '17:40', 'price_thb': 4508,
                 'aircraft_type': '', 'num_stops': 0, 'is_direct': True,
                 'is_excluded_airline': False, 'checked_baggage': '23kg checked',
                 'total_score': 14.2, 'price_score': 10, 'time_score': 4.2},
            ],
            'prev_best': 4700, 'lowest_ever': 4508, 'scrape_count': 3,
            'avg_price': 4600,
            'price_history': [{'best_price': 4508}, {'best_price': 4700}],
        },
    ]


def test_build_flex_message():
    valid_combos = [('2026-05-29', '2026-06-01')]
    flex = build_flex_message(_make_route_results(), valid_combos)
    assert flex['type'] == 'carousel'
    assert len(flex['contents']) >= 2
    # Summary bubble first, titled by trip name
    assert flex['contents'][0]['header']['contents'][0]['text'] == 'Danang'
