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