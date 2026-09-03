import pytest
import geopandas as gpd
import osmnx as ox
import fixbikenet as fbn
from pandas.testing import assert_frame_equal

fbn.constants._CRS_CALCULATIONS = 'auto'
fbn.constants._BETWEENNESS_RANDOM_NODES = 100


@pytest.fixture
def validation_gdf_frederiksberg():
    gdf = gpd.read_file("./tests/test_data/frederiksberg-fixbikenet-gaps.gpkg", layer='Identified gaps')
    return gdf[['source', 'target']]


def test_fixbikenet_case_success_offline1(validation_gdf_frederiksberg):
    """Verify that the offline version of fixbikenet works as intended.
    """
    fbn.constants._ROUTING_PENALTY = {0: 1.5, 1: 1}
    gaps_ordered = fbn.fixbikenet(
            city_query="Frederiksberg",
            radius = 1000,
            mingap = 0,
            maxgap = 500,
            numgaps = 20,
            import_files={
                'city_boundary': "./tests/test_data/frederiksberg_boundary.geojson",
                'street_network': "./tests/test_data/frederiksberg_streetbike_network.gpkg",
            },
        )

    assert_frame_equal(
        validation_gdf_frederiksberg,
        gaps_ordered[['source', 'target']]
    )
