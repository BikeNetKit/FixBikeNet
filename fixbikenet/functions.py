import yaml

def map_edges_to_bike_infrastructure(g):
    """
    map if edges in graph have bike infrastructure as specified in config_osm.yml

    Parameters
    ----------
    g :networkx.MultiDiGraph
        simplified graph representing the street network

    Returns
    -------
    g : networkx.MultiDiGraph
        simplified graph representing the street network, with added binary edge attribute "pbi"
    """
    # first step: map all highway attributes
    protected_bike_infra = yaml.load(
        open("./config/config_osm.yml"),
        Loader=yaml.FullLoader)["protected_bike_infra"]

    # add binary edge attribute "pbi" (protected bike infra: True/False)
    for edge in g.edges(keys=True):
        g.edges[edge]["pbi"] = protected_bike_infra[
            g.edges[edge]["highway"]
        ]
    return g

def find_edges_to_drop(g):
    """
    find parallel edges that have different pbi values, list the ones with pbi=0

    Parameters
    ----------
    g : networkx.MultiDiGraph
        simplified graph representing the street network, with added binary edge attribute "pbi"

    Returns
    -------
    edges_to_drop: list
        unique list of edges to drop-> edges where pbi values differ and pbi value=0 gets dropped
    """
    # to find parallel edges, get all u,v tuples for which u,v,w>0 exists:
    uvs = [edge[:2] for edge in list(g.edges) if edge[2] > 0]  # >0 includes key=1, key=2, ...
    uvs = list(set(uvs))
    edges_to_drop = []

    for uv in uvs:
        # collect all parallel edges for u-v node pair;
        # account for the fact that edges are directed! uv[::-1]==vu might also be on the list
        parallel_edges = [edge for edge in list(g.edges) if (edge[:2] == uv) or (edge[:2] == uv[::-1])]

        # get set of PBIs for this u-v parallel edge list
        pbis = set([g.edges[e]["pbi"] for e in parallel_edges])

        # if we have both pbi==0 and pbi==1,
        if len(pbis) == 2:
            # add edges with pbi==0 to edges_to_drop list
            to_drop = [e for e in parallel_edges if g.edges[e]["pbi"] == 0]
            edges_to_drop += to_drop

    edges_to_drop = list(set(edges_to_drop))
    return edges_to_drop

def weigh_edges(G, penalty):
    """
    adds weight parameter to all edges in G, which is calculated by multiplying the length of the edge with the corresponding penalty value

    Parameters
    ----------
    G: networkx.Graph
        undirected simple graph representing the street network
    penalty: dictionary
        dictionary of penalty values, dependent on if edge has bike infrastructure or not

    Returns
    -------
    G: networkx.Graph
        undirected simple graph representing the street network with weighted edges
    """
    for edge in G.edges:
        # compute edge weight
        edge_pbi = G.edges[edge]["pbi"]
        edge_length = G.edges[edge]["length"]
        edge_weight = edge_length * penalty[edge_pbi]
        # add as attribute
        G.edges[edge]["weight"] = edge_weight
    return G

def find_contact_nodes(G):
    """
    find nodes that have both edges with protected and without protected bike infrastructure incident on them

    Parameters
    ----------
    G:networkx.Graph
        undirected simple graph representing the street network with weighted edges

    Return
    ------
    contact_nodes: list
        list of all nodes that fulfill criteria to be a contact node
    """
    contact_nodes = []
    for node in G.nodes:
        pbis = set([G.edges[edge]["pbi"] for edge in G.edges(node)])
        if len(pbis) == 2:
            contact_nodes.append(node)
    return contact_nodes

def find_potential_gaps(contact_nodes, nodes_gdf, maxgap):
    """
    finds potential gaps in protected bicycle network, corresponding to two contact nodes that are within maxgap euclidean distance of each other

    Parameters
    ----------
    contact_nodes: list
        list of all nodes that fulfill criteria to be a contact node
    nodes_gdf: geopandas.GeoDataFrame
        all nodes in street network
    maxgap: int
        user defined maximal euclidean distance between two contact nodes

    Returns
    -------
    potential_gaps: list
        all unique potential gaps in protected bicycle network
    """
    potential_gaps = []

    for node in contact_nodes:
        node_buffer = nodes_gdf.loc[node, "geometry"].buffer(maxgap)
        q = nodes_gdf.sindex.query(node_buffer, predicate="intersects")
        neighbours = list(nodes_gdf.iloc[q].index)
        neighbours.remove(node)
        # convention: sort by ascending OSMID...
        node_pairs = [tuple(sorted(z)) for z in zip([node] * len(neighbours), neighbours)]
        potential_gaps += node_pairs

    # ... so that we can easily deduplicate
    potential_gaps = list(set(potential_gaps))
    return potential_gaps