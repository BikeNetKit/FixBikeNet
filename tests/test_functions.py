import pytest
from networkx.utils.misc import graphs_equal
import geopandas as gpd
from shapely.geometry import Point

from fixbikenet.functions import *

@pytest.fixture
def create_test_graph():
    G = nx.MultiDiGraph()
    G.add_edges_from([(1,2), (1,3), (2,3)])
    highway_values = {(1,2,0):{'highway':'living_street'},
                      (1,3,0):{'highway': 'motorway'},
                      (2,3,0):{'highway':'path'}}
    nx.set_edge_attributes(G,highway_values)
    return G

@pytest.fixture
def create_validation_graph():
    G = nx.MultiDiGraph()
    G.add_edges_from([(1, 2), (1, 3), (2, 3)])
    attributes = {(1,2,0): {'highway': 'living_street', 'pbi': True},
                  (1,3,0): {'highway': 'motorway', 'pbi': False},
                  (2,3,0): {'highway': 'path', 'pbi': True}}
    nx.set_edge_attributes(G, attributes)
    return G

def test_edge_infra_mapping(create_test_graph, create_validation_graph):
    assert graphs_equal(map_edges_to_bike_infrastructure(create_test_graph), create_validation_graph)

@pytest.fixture
def create_parallel_test_graph():
    G = nx.MultiDiGraph()
    G.add_edges_from([(1, 2),(1,2), (1, 3), (2, 3)])
    attributes = {(1, 2, 0): {'highway': 'living_street', 'pbi': True},
                  (1, 2, 1): {'highway': 'living_street', 'pbi': False},
                  (1, 3, 0): {'highway': 'motorway', 'pbi': False},
                  (2, 3, 0): {'highway': 'path', 'pbi': True}}
    nx.set_edge_attributes(G, attributes)
    return G

@pytest.fixture
def create_validation_edge_list():
    edge_list = [(1, 2, 1)]
    return edge_list

def test_find_edges_to_drop(create_parallel_test_graph, create_validation_edge_list):
    assert find_edges_to_drop(create_parallel_test_graph) == create_validation_edge_list

@pytest.fixture
def create_graph_to_weigh():
    G = nx.Graph()
    G.add_edges_from([(1, 2), (1, 3), (2, 3)])
    attributes = {(1, 2): {'length': 10, 'pbi': True},
                  (1, 3): {'length': 4, 'pbi': False},
                  (2, 3): {'length': 5, 'pbi': True}}
    nx.set_edge_attributes(G, attributes)
    return G

@pytest.fixture
def create_weighted_graph():
    G = nx.Graph()
    G.add_edges_from([(1, 2), (1, 3), (2, 3)])
    attributes = {(1, 2): {'length': 10, 'pbi': True, 'weight': 10},
                  (1, 3): {'length': 4, 'pbi': False, 'weight': 20},
                  (2, 3): {'length': 5, 'pbi': True, 'weight': 5}}
    nx.set_edge_attributes(G, attributes)
    return G

@pytest.fixture
def create_penalty():
    penalty = {
        0: 5,
        1: 1
    }
    return penalty

def test_weigh_edges(create_graph_to_weigh, create_weighted_graph, create_penalty):
    assert graphs_equal(weigh_edges(create_graph_to_weigh, create_penalty), create_weighted_graph)

@pytest.fixture
def create_validation_contact_nodes():
    contact_nodes = [1,3]
    return contact_nodes

def test_find_contact_nodes(create_weighted_graph, create_validation_contact_nodes):
    assert find_contact_nodes(create_weighted_graph) == create_validation_contact_nodes

@pytest.fixture
def create_test_contact_nodes():
    contact_nodes = [1,3,4]
    return contact_nodes

@pytest.fixture
def create_maxgap():
    maxgap = 50
    return maxgap

@pytest.fixture
def create_test_nodes_gdf():
    nodes ={'osmid':[1,2,3,4],'geometry':[Point(1,1), Point(1000,1000), Point(3,3), Point(2000,2000)]}
    nodes_gdf = gpd.GeoDataFrame(nodes)
    nodes_gdf.set_index('osmid',inplace=True)
    return nodes_gdf

@pytest.fixture
def create_validation_gaps():
    gaps = [(1,3)]
    return gaps

def test_find_potential_gaps(create_test_contact_nodes, create_maxgap, create_test_nodes_gdf, create_validation_gaps):
    assert find_potential_gaps(create_test_contact_nodes,create_test_nodes_gdf, create_maxgap) == create_validation_gaps

@pytest.fixture
def create_graph_for_routing():
    G = nx.Graph()
    G.add_edges_from([(1, 2), (1, 3), (2, 3), (3,4)])
    attributes = {(1, 2): {'length': 10, 'pbi': True, 'weight': 10},
                  (1, 3): {'length': 4, 'pbi': False, 'weight': 20},
                  (2, 3): {'length': 5, 'pbi': True, 'weight': 5},
                  (3, 4): {'length': 6, 'pbi': False, 'weight': 30}}
    nx.set_edge_attributes(G, attributes)
    return G

@pytest.fixture
def create_potential_gaps():
    potential_gaps = [(1,4), (2,3), (3,4)]
    return potential_gaps

@pytest.fixture
def create_validation_found_gap_paths():
    found_gap_paths = ([(1,4), (3,4)], [[1,3,4],[3,4]])
    return found_gap_paths

def test_find_actual_gaps(create_graph_for_routing, create_potential_gaps, create_validation_found_gap_paths):
    assert find_actual_gaps(create_graph_for_routing, create_potential_gaps) == create_validation_found_gap_paths

@pytest.fixture
def create_betweenness_nodes():
    nodes = {'osmid': [1, 2, 3, 4], 'geometry': [Point(1, 1), Point(5000, 5000), Point(3, 3), Point(1000, 1000)]}
    nodes_gdf = gpd.GeoDataFrame(nodes)
    nodes_gdf.set_index('osmid', inplace=True)
    return nodes_gdf

@pytest.fixture
def create_radius():
    radius = 2000
    return radius

@pytest.fixture
def create_validation_ebc():
    ebc = {(1,2):54.5, (1,3): 0, (2,3): 54.5, (3,4): 56.5}
    return ebc

def test_compute_local_betweenness_centrality(create_graph_for_routing, create_betweenness_nodes, create_radius, create_validation_ebc):
    assert compute_local_betweenness_centrality(create_graph_for_routing, create_betweenness_nodes, create_radius) == create_validation_ebc