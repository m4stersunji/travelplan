import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import (
    SEARCH_ROUTES, EXCLUDED_AIRLINES, PREFERRED_DEPARTURE_START,
    PREFERRED_DEPARTURE_END, DB_PATH, DATA_DIR, LOG_DIR,
)

def test_search_routes_has_danang_trip():
    routes = SEARCH_ROUTES
    assert len(routes) >= 4
    origins = {r["origin"] for r in routes}
    destinations = {r["destination"] for r in routes}
    assert "BKK" in origins
    assert "DAD" in destinations or "DAD" in origins

def test_excluded_airlines_contains_middle_east_carriers():
    assert "Emirates" in EXCLUDED_AIRLINES
    assert "Qatar Airways" in EXCLUDED_AIRLINES
    assert "Etihad" in EXCLUDED_AIRLINES
    assert "Oman Air" in EXCLUDED_AIRLINES
    assert "Saudia" in EXCLUDED_AIRLINES
    assert "Gulf Air" in EXCLUDED_AIRLINES
    assert "flynas" in EXCLUDED_AIRLINES
    assert "Air Arabia" in EXCLUDED_AIRLINES

def test_preferred_departure_window():
    assert PREFERRED_DEPARTURE_START == "09:00"
    assert PREFERRED_DEPARTURE_END == "12:00"

def test_paths_are_absolute():
    assert os.path.isabs(DB_PATH)
    assert os.path.isabs(DATA_DIR)
    assert os.path.isabs(LOG_DIR)
