from . import constants
from . import settings
import os
import numpy as np
import networkx as nx
import osmnx as ox
import geopandas as gpd
import pandas as pd
pd.set_option('display.max_columns', None) # for debugging
import warnings
from tqdm.auto import tqdm
import time
import sys # use sys.exit() for debugging
import matplotlib.pyplot as plt
from collections import defaultdict
from fixbikenet.functions import (
    compute_local_betweenness_centrality,
    create_gdf_with_geoms,
    find_actual_gaps,
    find_contact_nodes,
    find_edges_to_drop,
    find_potential_gaps,
    gap_declustering,
    get_correct_edgetuples,
    graph_nodes_to_gdf,
    graph_edges_to_gdf,
    import_network,
    initialize_progress_bar,
    rank_gaps_by_b,
    map_edges_to_bike_infrastructure,
    slugify,
    weigh_edges,
    _print_footer,
    _print_header,
    _resolve_crs_calculations,
    _validate_parameters,
    _validate_settings,
)

def fixbikenet(
    city_query,
    radius = 2500,
    mingap = 20,
    maxgap = 800,
    numgaps = 50,
    export_data = True,
    city_id = None,
    export_file_format="geojson",
    export_plot=False,
    import_files={},
):
    """
    Finds gaps in bicycle networks and returns the `numgaps` that are the most important to fill.

    Parameters
    ----------
    city_query : str
        name of the city that the analysis should be performed on
    radius : int, default 2500
        cut-off length for computation of local betweenness centrality, in meters
    mingap : int, default 20
        minimum distance between node pairs to be considered as a potential gap, in meters
    maxgap : int, default 800
        maximum distance between node pairs to be considered as a potential gap, in meters
    numgaps : int, default 50
        Number of gaps to find.
    export_data : bool, optional, default True
        If set to True, data will be saved to a file. The filename is [slug].gpkg, where slug is a string id made out of city_name
    city_id : str | None, default None
        If set, the slugified city_id is used in the filename of the data export. For example, a city_id "Athens" will slugify into "athens" in filenames. If set to None, the slugified city_query is used in the filename of the data export. It is useful to set a city_id for cities where the city_query is not the city name, for example to set for a city_query "Municipality of Athens" the city_id to "Athens".
    export_file_format : str, optional, default "geojson"
        File format for the data export, relevant if export_data set to True. Default "geojson", also possible "gpkg". If exporting as geojson, generates extra files for street network and city boundary. If exporting as gkpg, these are added all in one file as extra layers.
    export_plot : bool, optional, default False
        If set to True, plot will be saved to a file
    import_files: dict, default {}
        The following key:value entries can be set:

            - 'street_network' : str | None, default None
                If not set to None, the street network is loaded from this file. Must be a gpkg file in unprojected crs EPSG:4326 with layers nodes and edges, with the structure that an undirected osmnx street network g has after saved via ox.io.save_graph_geopackage(). For example:
                >>> ox.settings.useful_tags_way = ["highway", "cycleway", "cycleway:right", "cycleway:left", "cycleway:both", "cyclestreet"]
                >>> g = ox.graph_from_place("Barcelona", network_type='all', simplify=False)
                >>> g = nx.MultiGraph(ox.convert.to_digraph(g))
                >>> ox.io.save_graph_geopackage(g, "Barcelona_streets.gpkg").

    Returns
    -------
    gaps_ordered : geopandas.geodataframe.GeoDataFrame
        ordered geodataframe with the `numgaps` most important gaps to fill

    References
    ----------
    [1] Vybornova, A., Cunha, T., Gühnemann, A. and Szell, M. (2023), Automated Detection of Missing Links in Bicycle Networks. Geogr Anal, 55: 239-267. https://doi.org/10.1111/gean.12324
    """
    # Setup
    starttime = time.time()
    np.random.seed(settings.random_seed)  # Set random number generator seed for reproducibility
    setting_was_auto = _validate_settings()
    import_files = _validate_parameters(city_query, radius, mingap, maxgap, export_data, export_file_format, import_files)
    _print_header(city_query)
    

    if import_files['street_network'] is not None:
        progress_bar = initialize_progress_bar("Importing network data", 1, "network")
        g = import_network(import_files['street_network'])
    else:
        ### downloading and preprocessing data from OSM. To do: Fix download with custom filters
        progress_bar = initialize_progress_bar("Downloading OSM data", 1, "network")
        ox.settings.useful_tags_way = ["highway", "cycleway", "cycleway:right", "cycleway:left", "cycleway:both", "cyclestreet"]
        # fetch street network data from osmnx
        g = ox.graph_from_place(
            city_query, network_type='all', simplify=False
        )
    progress_bar.update(1)
    progress_bar.close()

    progress_bar = initialize_progress_bar("Processing network", 2)
    g = ox.simplify_graph(
        g,
        edge_attrs_differ=['cycleway', 'highway', 'cycleway:right', 'cycleway:left', 'cycleway:both']
    )
    progress_bar.update(1)
    g = ox.distance.add_edge_lengths(g)

    # check which edges have existing bike infrastructure as defined in config/config_osm.yml and assign boolean value to edges
    g = map_edges_to_bike_infrastructure(g)
    progress_bar.update(1)
    progress_bar.close()

    edges_to_drop = find_edges_to_drop(g)
    g.remove_edges_from(edges_to_drop)

    # Capital-G: the Graph() object we will be working with from now on
    G = nx.Graph(g)

    # add weight to edges for path calculation, using constants._ROUTING_PENALTY
    G = weigh_edges(G)

    # creating new gdfs for nodes and edges of G
    nodes_gdf = graph_nodes_to_gdf(G)
    edges_gdf = graph_edges_to_gdf(G)
    _resolve_crs_calculations(nodes_gdf)
    nodes_gdf = nodes_gdf.to_crs(constants._CRS_CALCULATIONS)
    edges_gdf = edges_gdf.to_crs(constants._CRS_CALCULATIONS)

    # finding contact nodes in network
    contact_nodes = find_contact_nodes(G)

    # finding potential gaps in network
    potential_gaps = find_potential_gaps(contact_nodes, nodes_gdf, maxgap)

    # add routing for gaps in network
    found_gaps, found_gaps_nsp = find_actual_gaps(G, potential_gaps, mingap)

    # calculating local betweenness score dependent on radius
    ebc = compute_local_betweenness_centrality(G, nodes_gdf, radius)

    # calculate parameter B for all gaps, used for deciding which gaps are most important
    Bs = rank_gaps_by_b(found_gaps_nsp, G, ebc)
    df = pd.DataFrame(
        {
            "gap": found_gaps,
            "benefit": Bs,
            "nodelist": found_gaps_nsp
        }
    )
    df = df.sort_values(by="benefit", ascending=False).reset_index(drop=True)

    # Only keep the numgaps*constants._CLUSTER_GAPS_PER_FINAL_GAP most 
    # important gaps before declustering. If there are fewer than 
    # numgaps*constants._CLUSTER_GAPS_PER_FINAL_GAP gaps keep only those
    if df.shape[0] > numgaps*constants._CLUSTER_GAPS_PER_FINAL_GAP:
        df = df.iloc[:numgaps*constants._CLUSTER_GAPS_PER_FINAL_GAP]

    #decluster edges
    gap_df = gap_declustering(df, G, ebc, contact_nodes)

    progress_bar = initialize_progress_bar("Postprocess data", 5)
    gap_df = gap_df.nlargest(numgaps, "benefit").reset_index(drop=True)
    progress_bar.update(1)

    # compute list of all edges that are part of each gap, where each edge is u,v
    gap_df["edge_list"] = gap_df.path.apply(lambda x: get_correct_edgetuples(edges_gdf, x))
    progress_bar.update(1)

    # assign source and target nodes for each gap
    gap_df["source"] = [t[0] for t in gap_df.path]
    gap_df["target"] = [t[-1] for t in gap_df.path]
    progress_bar.update(1)

    # add actual geometries in network to each gap
    gaps_ordered = create_gdf_with_geoms(gap_df, edges_gdf)
    progress_bar.update(1)

    gaps_ordered['ordering'] = gaps_ordered.index
    gaps_ordered['length'] = gaps_ordered['geometry'].length

    edges_pbi_gdf = edges_gdf[edges_gdf["pbi"] == 1]

    # Back to unprojected (potentially). No more calculations after here.
    gaps_ordered.to_crs(epsg=4326, inplace=True)
    edges_pbi_gdf.to_crs(epsg=4326, inplace=True)
    edges_gdf.to_crs(epsg=4326, inplace=True)
    progress_bar.update(1)
    progress_bar.close()

    # Generate export data filename
    if export_data:
        os.makedirs(settings.export_path, exist_ok=True)
        if city_id is None:
            city_string = city_query
        else:
            city_string = city_id
        export_data_filename = (
                slugify(city_string) + "-fixbikenet-gaps" + "." + export_file_format
        )

    if export_data:
        edges_pbi_gdf.drop(["osmid"], axis=1, inplace=True)
        edges_gdf.drop(["osmid"], axis=1, inplace=True)
        city_boundary = ox.geocoder.geocode_to_gdf(city_query)
        city_boundary.to_crs(epsg=4326, inplace=True)
        if export_file_format == "geojson":
            progress_bar = initialize_progress_bar("Exporting data", 4, "file")
            gaps_ordered.to_file(settings.export_path + export_data_filename, driver="GeoJSON", RFC7946="YES")
            progress_bar.update(1)
            edges_pbi_gdf.to_file(settings.export_path + slugify(city_string) + "-fixbikenet" +  "-existing_bike_network.geojson", driver="GeoJSON", RFC7946="YES")
            progress_bar.update(1)
            edges_gdf.to_file(settings.export_path + slugify(city_string) + "-fixbikenet" + "-existing_street_network.geojson", driver="GeoJSON", RFC7946="YES")
            progress_bar.update(1)
            city_boundary.to_file(settings.export_path + slugify(city_string) + "-city_boundary.geojson", driver="GeoJSON", RFC7946="YES")
            progress_bar.update(1)
        elif export_file_format == "gpkg":
            progress_bar = initialize_progress_bar("Exporting data", 1, "file")
            gaps_ordered.to_file(settings.export_path + export_data_filename, driver="GPKG", layer="Identified gaps")
            edges_pbi_gdf.to_file(settings.export_path + export_data_filename, driver="GPKG", layer="Existing bike network", append=True)
            edges_gdf.to_file(settings.export_path + export_data_filename, driver="GPKG", layer="Existing street network", append=True)
            city_boundary.to_file(settings.export_path + export_data_filename, driver="GPKG", layer="City boundary", append=True)
            progress_bar.update(1)
        progress_bar.close()

        if export_plot:
            os.makedirs("./results/plots/", exist_ok=True)
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            edges_pbi_gdf.plot(ax=ax, color="grey")
            gaps_ordered.plot(ax=ax, color="red")
            ax.set_axis_off()
            fig.savefig(f"./results/plots/"+export_data_filename+".png", dpi=150, bbox_inches='tight')
            plt.close()

    # Cleanup, finalize
    endtime = time.time()
    _print_footer(export_data, endtime, starttime)

    return gaps_ordered
