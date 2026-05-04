# import packages
import pandas as pd
import osmnx as ox

# import functions
from fixbikenet.functions import *

def fixbikenet(
    city_name,
    proj_crs = "3857",
    radius = 2000,
    maxgap = 50,
    penalty = {0: 5, 1: 1},
):
    """
    Finds gaps in bicycle networks and returns the 100 that are the most important to fill.
    Parameters
    ----------
    city_name : str
        name of the city that the analysis should be performed on
    proj_crs : str, default '3857'
        coordinate reference system that is used to project osm data. Default is '3857' (WGS 84 / Pseudo-Mercator)
    radius : int, default 2000
        cut-off length for computation of local betweenness centrality, in meters
    maxgap : int, default 50
        maximum distance between node pairs to be considered as a potential gap
    penalty : dict, default {0:5, 1: 1}
        weighing for shortest path calculations, where streets without protected bike infrastructure (pbi) get penalized

    Returns
    -------
    gdf : geopandas.geodataframe.GeoDataFrame
        ordered geodataframe with the 100 most important gaps to fill

    References
    ----------
    [1] Vybornova, A., Cunha, T., Gühnemann, A. and Szell, M. (2023), Automated Detection of Missing Links in Bicycle Networks. Geogr Anal, 55: 239-267. https://doi.org/10.1111/gean.12324
    """
    # check if user input is valid
    if type(city_name) != str:
        raise TypeError("city_name must be a string")
    if type(proj_crs) != str:
        raise TypeError("proj_crs must be a string")
    if type(radius) != int:
        raise TypeError("radius must be an integer")
    if type(maxgap) != int:
        raise TypeError("maxgap must be an integer")

    ### downloading and preprocessing data from OSM
    print("Downloading OSM data..")

    # fetch street network data from osmnx
    g = ox.graph_from_place(
        city_name, network_type='all', simplify=False
    )
    g = ox.simplify_graph(
        g,
        edge_attrs_differ=['highway']
    )

    # export osmnx data to gdfs
    nodes_gdf, edges_gdf = ox.graph_to_gdfs(
        g,
        nodes=True,
        edges=True,
        node_geometry=True,
        fill_edge_geometry=True
    )

    # project to proj_crs
    nodes_gdf = nodes_gdf.to_crs(proj_crs)
    edges_gdf = edges_gdf.to_crs(proj_crs)


    # check which edges have existing bike infrastructure as defined in config/config_osm.yml and assign boolean value to edges
    g = map_edges_to_bike_infrastructure(g)
    edges_gdf = bike_infra_mapping_gdf(g, edges_gdf)

    print("Checking for parallel edges to drop...")
    edges_to_drop = find_edges_to_drop(g)
    g.remove_edges_from(edges_to_drop)
    print("Edges dropped")

    # Capital-G: the Graph() object we will be working with from now on
    G = nx.Graph(g)

    # add weight to edges for path calculation, using penalty
    G = weigh_edges(G, penalty)

    # finding contact nodes in network
    contact_nodes = find_contact_nodes(G)

    # finding potential gaps in network
    potential_gaps = find_potential_gaps(contact_nodes, nodes_gdf, maxgap)

    # add routing for gaps in network
    found_gaps, found_gaps_nsp = find_actual_gaps(G, potential_gaps)

    # calculating local betweenness score dependent on radius
    print("Calculating local betweenness centrality..")
    ebc = compute_local_betweenness_centrality(G, nodes_gdf, radius)

    # calculate parameter B for all gaps, used for deciding which gaps are most important
    Bs = rank_gaps_by_b(found_gaps_nsp, G, ebc)

    df = pd.DataFrame(
        {
            "gap": found_gaps,
            "B": Bs,
            "nodelist": found_gaps_nsp
        }
    )
    df = df.sort_values(by="B", ascending=False).reset_index(drop=True)

    # only keep the 100 most important gaps. If there are fewer than 100 gaps keep only those
    if df.length > 100:
        df = df.iloc[:100]

    # assign source and target nodes for each gap
    df["source"] = [t[0] for t in df.gap]
    df["target"] = [t[1] for t in df.gap]

    # compute list of all edges that are part of each gap, where each edge is u,v
    df["edge_list"] = df.nodelist.apply(lambda x: get_correct_edgetuples(edges_gdf, x))

    # drop keys for edges
    edges_gdf = edges_gdf.loc[:, :, 0].copy()

    # add actual geometries in network to each gap
    gdf = create_gdf_with_geoms(df, edges_gdf)

    gdf.to_file("gaps.gpkg", driver="GPKG")

    return gdf