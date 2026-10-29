"""Main procedure for running `fixbikenet`."""

from . import constants, settings, osm, _overpass
import os
import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
import warnings
pd.set_option('display.max_columns', None) # for debugging
np.set_printoptions(legacy='1.25')
import sys  # noqa: F401, use sys.exit() for debugging
import time
import matplotlib.pyplot as plt

from fixbikenet.utils import (
    _get_weighted_distances,
    _import_data_files,
    _print_footer,
    _print_header,
    _reset_auto_settings,
    _resolve_crs_calculations,
    _validate_parameters,
    _validate_settings,
    add_point_data_to_net,
    compute_local_betweenness_centrality,
    create_gdf_with_geoms,
    download_network,
    find_actual_gaps,
    find_contact_nodes,
    find_edges_to_drop,
    find_potential_gaps,
    gap_declustering,
    get_correct_edgetuples,
    graph_edges_to_gdf,
    graph_nodes_to_gdf,
    import_network,
    initialize_progress_bar,
    assign_pbi_to_edges,
    rank_gaps_by_b,
    slugify,
    weigh_edges,
)


def fixbikenet(
    city_query,
    min_gap_length = 20,
    max_gap_length = 800,
    num_gaps = 50,
    export_data = True,
    city_id = None,
    export_plot=False,
    import_files={},
):
    """Find gaps in bicycle networks and return the `num_gaps` that are the most
    important to fill.

    Parameters
    ----------
    city_query : str
        Name of the city that the analysis should be performed on.
    min_gap_length : int, default 20
        Minimum distance between node pairs to be considered as a potential 
        gap, in meters.
    max_gap_length : int, default 800
        Maximum distance between node pairs to be considered as a potential 
        gap, in meters.
    num_gaps : int, default 50
        Number of gaps to find.
    export_data : bool, default True
        If set to True, data will be saved to a file. The filename is 
        [slug].[settings.export_file_format], where slug is a string id made 
        out of `city_query` (or `city_id` if set).
    city_id : str | None, default None
        If set, the slugified `city_id` is used in the filename of the data 
        export. For example, a `city_id` "Athens" will slugify into "athens" 
        in filenames. If set to None, the slugified `city_query` is used in the
        filename of the data export. It is useful to set a `city_id` for cities
        where the `city_query` is not the city name, for example to set for a 
        `city_query` "Municipality of Athens" the `city_id` to "Athens".
    export_plot : bool, optional, default False
        If set to True, plot will be saved to a file.
    import_files: dict, default {}
        The following key:value entries can be set:

        - 'city_boundary' : None or str, default None
            If not set to None, the study area is selected from the 
            (Multi)Polygon provided in the city_boundary shape or gpkg file, 
            ideally in unprojected latitude-longitude degrees (EPSG:4326), but 
            EPSG:3857 also works.
        - 'street_network' : str | None, default None
            If not set to None, the street network is loaded from this file. 
            For best results, this network should encompass both car and 
            protected bicycle infrastructure. Must be a gpkg file in 
            unprojected crs EPSG:4326 with layers nodes and edges, with the
            structure that an undirected osmnx street network g has after saved 
            via ox.io.save_graph_geopackage(). For example:
            >>> import fixbikenet as fbn
            >>> g = ox.graph_from_place("Barcelona", simplify=False, retain_all=True, custom_filter = fbn.osm.CARPBI_NETWORK_CUSTOM_FILTER)
            >>> g = nx.MultiGraph(ox.convert.to_digraph(g))
            >>> ox.io.save_graph_geopackage(g, "Barcelona_carpbi_network.gpkg").
        - 'point_data' : None or str, default None
            If not set to None, an additional data set of points will be loaded 
            from this file, representing point events like traffic crashes or 
            citizen feedback to improve bike infrastructure. Must be a gpkg or geojson file in unprojected CRS EPSG:4326 containing only point objects, optionally with an int ``num`` column that encodes the 
            number of point events. The data set is used to re-prioritize the ordering of the network gaps, controlled with `settings.import_data_impact`.

    Returns
    -------
    gaps_ordered : geopandas.geodataframe.GeoDataFrame
        Ordered geodataframe with the `num_gaps` most important gaps to fill.

    References
    ----------
    [1] Vybornova, A., Cunha, T., Gühnemann, A. and Szell, M. (2023), Automated Detection of Missing Links in Bicycle Networks. Geogr Anal, 55: 239-267. https://doi.org/10.1111/gean.12324
    """

    # Setup
    starttime = time.time()
    np.random.seed(settings.random_seed) # Set random number generator seed for reproducibility
    setting_was_auto = _validate_settings()
    import_files = _validate_parameters(city_query, min_gap_length, max_gap_length, export_data, import_files)
    _print_header(city_query)
    
    ### Import data files
    num_data_files, point_data, _ = _import_data_files(import_files) # trip_data set to _. To do in the future.

    # Get city boundary
    if import_files['city_boundary']:
        city_boundary_shp = gpd.read_file(settings.import_path+import_files['city_boundary'])
        city_boundary = city_boundary_shp.iloc[[0]]
    else:
        city_boundary = ox.geocoder.geocode_to_gdf(city_query)
    
    if import_files['street_network'] is not None:
        progress_bar = initialize_progress_bar("Importing network data", 1, "network")
        g = import_network(import_files['street_network'])
    else:
        ### downloading and preprocessing data from OSM. To do: Fix download with custom filters
        progress_bar = initialize_progress_bar("Downloading OSM data", 1, "network")
        # Get city boundary 
        if import_files['city_boundary']:
            city_boundary_shp = gpd.read_file(settings.import_path+import_files['city_boundary'])
            city_boundary_gdf = city_boundary_shp.iloc[[0]]    
        else:
            city_boundary_gdf = ox.geocoder.geocode_to_gdf(city_query)
        city_boundary_geometry = city_boundary_gdf.geometry[0]
        # Fetch carpbi network data from osmnx
        # Due to retain_all=False, this fetches the largest connected component
        g = download_network(city_query, network_type='drive', custom_filter=osm.CARPBI_NETWORK_CUSTOM_FILTER, retain_all=False, city_boundary_geometry=city_boundary_geometry)
    
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
    g = assign_pbi_to_edges(g)
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
    potential_gaps = find_potential_gaps(contact_nodes, nodes_gdf, max_gap_length)

    # add routing for gaps in network
    found_gaps, found_gaps_nsp = find_actual_gaps(G, potential_gaps, min_gap_length)

    # calculating local betweenness score dependent on radius
    ebc = compute_local_betweenness_centrality(G, nodes_gdf)

    G_lengths = nx.get_edge_attributes(G, "length")
    nx.set_edge_attributes(G, G_lengths, "distance")
    nx.set_edge_attributes(G, G_lengths, "distance_weighted")
    # Add point data to edges
    if point_data is not None:
        G_gaps = nx.MultiGraph(G.subgraph(set(n for nlist in found_gaps_nsp for n in nlist))) # To do once pythonmin>=3.15: *nlist for nlist in found_gaps_nsp
        edges_gaps = ox.graph_to_gdfs(G_gaps, nodes=False)
        edges_gaps = edges_gaps.to_crs(constants._CRS_CALCULATIONS) # Project
        edges_gaps.reset_index(drop=False, inplace=True)
        edges_gaps = add_point_data_to_net(point_data, edges_gaps)
        num_points_list = edges_gaps["num_points"]
        edges_gaps['pair'] = list(zip(edges_gaps.u, edges_gaps.v))
        edge_list = edges_gaps['pair']
        num_points_dict = dict(zip(edge_list, num_points_list))
        nx.set_edge_attributes(G, 0, "num_points")
        nx.set_edge_attributes(G, num_points_dict, "num_points")
        dist_weighted_dict = _get_weighted_distances(G, "num_points", inverted=True) # d_crash in [2]_, but the distance is multiplied instead of divided
        nx.set_edge_attributes(G, dist_weighted_dict, "distance_weighted")

    # calculate parameter B for all gaps, used for deciding which gaps are most important
    Bs = rank_gaps_by_b(found_gaps_nsp, G, ebc)
    df = pd.DataFrame(
        {
            "gap": found_gaps,
            "benefit": Bs,
            "nodelist": found_gaps_nsp,
        }
    )
    df = df.sort_values(by="benefit", ascending=False).reset_index(drop=True)

    # Only keep the num_gaps*constants._CLUSTER_GAPS_PER_FINAL_GAP most 
    # important gaps before declustering. If there are fewer than 
    # num_gaps*constants._CLUSTER_GAPS_PER_FINAL_GAP gaps keep only those
    if df.shape[0] > num_gaps*constants._CLUSTER_GAPS_PER_FINAL_GAP:
        df = df.iloc[:num_gaps*constants._CLUSTER_GAPS_PER_FINAL_GAP]

    #decluster edges
    gap_df = gap_declustering(df, G, ebc, contact_nodes, min_gap_length)

    progress_bar = initialize_progress_bar("Postprocess data", 5)
    gap_df = gap_df.nlargest(num_gaps, "benefit").reset_index(drop=True)
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
    gaps_ordered['length'] = gaps_ordered['geometry'].length.astype(int)

    edges_pbi_gdf = edges_gdf[edges_gdf["pbi"] == 1]

    # Back to unprojected (potentially). No more calculations after here.
    gaps_ordered.to_crs(epsg=4326, inplace=True)
    edges_pbi_gdf.to_crs(epsg=4326, inplace=True)
    edges_gdf.to_crs(epsg=4326, inplace=True)
    gaps_ordered = gaps_ordered[['path', 'benefit', 'name', 'edge_list', 'source', 'target', 'ordering', 'length', 'geometry']]

    progress_bar.update(1)
    progress_bar.close()

    # Cleanup
    keepedgedata = ['length', 'geometry']
    keepgapdata = ['source', 'target', 'benefit', 'name', 'ordering', 'length', 'geometry']
    for p in edges_pbi_gdf.keys():
        if p not in keepedgedata:
            del edges_pbi_gdf[p] 
    for p in gaps_ordered.keys():
            if p not in keepgapdata:
                del gaps_ordered[p] 

    if export_data:
        if len(gaps_ordered)<1:
            warnings.warn("No gaps found. No data was exported.")
        else:
            # Generate export data filename
            os.makedirs(settings.export_path, exist_ok=True)
            if city_id is None:
                city_string = city_query
            else:
                city_string = city_id
            export_data_filename = (
                    slugify(city_string) + "-fixbikenet-gaps" + "." + settings.export_file_format
            )

            edges_gdf = edges_gdf.drop(["osmid"], axis=1)
            city_boundary.to_crs(epsg=4326, inplace=True)
            if settings.export_file_format == "geojson":
                progress_bar = initialize_progress_bar("Exporting data", 4, "file")
                gaps_ordered.to_file(settings.export_path + export_data_filename, driver="GeoJSON", RFC7946="YES")
                progress_bar.update(1)
                edges_pbi_gdf.to_file(settings.export_path + slugify(city_string) + "-fixbikenet-existing_bike_network.geojson", driver="GeoJSON", RFC7946="YES")
                progress_bar.update(1)
                edges_gdf.to_file(settings.export_path + slugify(city_string) + "-fixbikenet-existing_street_network.geojson", driver="GeoJSON", RFC7946="YES")
                progress_bar.update(1)
                city_boundary.to_file(settings.export_path + slugify(city_string) + "-fixbikenet-city_boundary.geojson", driver="GeoJSON", RFC7946="YES")
                progress_bar.update(1)
            elif settings.export_file_format == "gpkg":
                f = settings.export_path + export_data_filename
                if os.path.exists(f):
                    os.remove(f) # mode="w" does not work for to_file with gpkg. It always appends. Therefore, existing file needs to be deleted.
                progress_bar = initialize_progress_bar("Exporting data", 1, "file")
                gaps_ordered.to_file(f, driver="GPKG", layer="Identified gaps")
                edges_pbi_gdf.to_file(f, driver="GPKG", layer="Existing bike network", append=True)
                edges_gdf.to_file(f, driver="GPKG", layer="Existing street network", append=True)
                city_boundary.to_file(f, driver="GPKG", layer="City boundary", append=True)
                progress_bar.update(1)
            progress_bar.close()

            if export_plot:
                os.makedirs("./results/plots/", exist_ok=True)
                fig, ax = plt.subplots(1, 1, figsize=(10, 10))
                edges_pbi_gdf.plot(ax=ax, color="grey")
                gaps_ordered.plot(ax=ax, color="red")
                ax.set_axis_off()
                fig.savefig("./results/plots/"+export_data_filename+".png", dpi=150, bbox_inches='tight')
                plt.close()

    # Cleanup, finalize
    _reset_auto_settings(setting_was_auto)
    endtime = time.time()
    _print_footer(export_data, endtime, starttime)

    return gaps_ordered
