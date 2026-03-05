import pytest
import networkx as nx
from networkx.utils.misc import graphs_equal

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
    G = nx.MultiDiGraph()
    G.add_edges_from([(1, 2), (1, 3), (2, 3)])
    attributes = {(1, 2, 0): {'length': 10, 'pbi': True},
                  (1, 3, 0): {'length': 4, 'pbi': False},
                  (2, 3, 0): {'length': 5, 'pbi': True}}
    nx.set_edge_attributes(G, attributes)
    return G

@pytest.fixture
def create_weighted_graph():
    G = nx.MultiDiGraph()
    G.add_edges_from([(1, 2), (1, 3), (2, 3)])
    attributes = {(1, 2, 0): {'length': 10, 'pbi': True, 'weight': 10},
                  (1, 3, 0): {'length': 4, 'pbi': False, 'weight': 20},
                  (2, 3, 0): {'length': 5, 'pbi': True, 'weight': 5}}
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