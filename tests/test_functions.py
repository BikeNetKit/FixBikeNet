import pytest
import networkx as nx
from networkx.utils.misc import graphs_equal

from fixbikenet.functions import *

@pytest.fixture
def create_test_graph():
    G = nx.MultiDiGraph()
    G.add_edges_from([(1,2), (1,3), (2,3)])
    highway_values = {(1,2,0):{'highway':'living_street'},(1,3,0):{'highway': 'motorway'},(2,3,0):{'highway':'path'}}
    nx.set_edge_attributes(G,highway_values)
    return G

@pytest.fixture
def create_validation_graph():
    G = nx.MultiDiGraph()
    G.add_edges_from([(1, 2), (1, 3), (2, 3)])
    attributes = {(1, 2,0): {'highway': 'living_street', 'pbi': True}, (1, 3,0): {'highway': 'motorway', 'pbi': False},
                      (2, 3,0): {'highway': 'path', 'pbi': True}}
    nx.set_edge_attributes(G, attributes)
    return G

def test_edge_infra_mapping(create_test_graph, create_validation_graph):
    assert graphs_equal(map_edges_to_bike_infrastructure(create_test_graph), create_validation_graph)