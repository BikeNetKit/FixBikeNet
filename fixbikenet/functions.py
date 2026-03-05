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