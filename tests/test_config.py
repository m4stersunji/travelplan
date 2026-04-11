import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import (
    SEARCH_ROUTES, EXCLUDED_AIRLINES,
    DB_PATH, DATA_DIR, LOG_DIR,
)


def test_search_routes_has_danang_trip():
    routes = SEARCH_ROUTES
    assert len(routes) >= 4
    origins = {r["origin"] for r in routes}
    destinations = {r["destination"] for r in routes}
    assert "Bangkok" in origins
    assert "Danang" in destinations or "Danang" in origins


def test_search_routes_have_route_codes():
    for r in SEARCH_ROUTES:
        assert 'route_code' in r
        assert r['route_code'] in ('BKK-DAD', 'DAD-BKK', 'BKK-KIX', 'TYO-BKK')


def test_excluded_airlines_contains_middle_east_carriers():
    assert "Emirates" in EXCLUDED_AIRLINES
    assert "Qatar Airways" in EXCLUDED_AIRLINES
    assert "Etihad" in EXCLUDED_AIRLINES


def test_paths_are_absolute():
    assert os.path.isabs(DB_PATH)
    assert os.path.isabs(DATA_DIR)
    assert os.path.isabs(LOG_DIR)
