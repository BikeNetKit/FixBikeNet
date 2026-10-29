import pytest
import osmnx as ox
import bikenetlib as bnl

ox.settings.use_cache = False

@pytest.fixture
def pbi_network_downloaded():
    g = ox.graph_from_place(
        "Frederiksberg municipality",
        custom_filter=bnl.osm.PBI_CUSTOM_FILTER,
    )
    return g

def test_PBI_CUSTOM_FILTER(pbi_network_downloaded):
    # Frederiksberg has more than 100 bike lanes
    assert len(pbi_network_downloaded) > 100


@pytest.fixture
def rail_stations_downloaded():
    r = ox.features_from_place(
        "Frederiksberg municipality",
        tags={"railway": ["station", "halt"]},
    )
    return r

def test_rail_stations(rail_stations_downloaded):
    # Frederiksberg has more than 5 rail stations
    assert len(rail_stations_downloaded) > 5