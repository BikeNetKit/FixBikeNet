# import packages
import osmnx as ox
import os
import matplotlib.pyplot as plt
from collections import defaultdict

# import functions
from fixbikenet.functions import *

def fixbikenet(
    city_query,
    proj_crs = "3857",
    radius = 2500,
    maxgap = 1000,
    penalty = {0: 1.5, 1: 1},
    export_data = True,
    city_id = None,
    export_file_format="geojson",
    export_plot=False,
    import_files={},
):
    """
    Finds gaps in bicycle networks and returns the 100 that are the most important to fill.
    Parameters
    ----------
    city_query : str
        name of the city that the analysis should be performed on
    proj_crs : str, default '3857'
        coordinate reference system that is used to project osm data. Default is '3857' (WGS 84 / Pseudo-Mercator)
    radius : int, default 2500
        cut-off length for computation of local betweenness centrality, in meters
    maxgap : int, default 1000
        maximum distance between node pairs to be considered as a potential gap
    penalty : dict, default {0:1.5, 1: 1}
        weighing for shortest path calculations, where streets without protected bike infrastructure (pbi) get penalized
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
            "street_network" : str | None, default None
                If not set to None, the street network is loaded from this file. Must be a gpkg file in unprojected crs EPSG:4326 with layers nodes and edges, with the structure that an undirected osmnx street network g has after saved via ox.io.save_graph_geopackage(). For example:
                >>> ox.settings.useful_tags_way = ["highway", "cycleway", "cycleway:right", "cycleway:left", "cycleway:both", "cyclestreet"]
                >>> g = ox.graph_from_place("Barcelona", network_type='all', simplify=False)
                >>> g = nx.MultiGraph(ox.convert.to_digraph(g))
                >>> ox.io.save_graph_geopackage(g, "Barcelona_streets.gpkg").
    Returns
    -------
    gdf : geopandas.geodataframe.GeoDataFrame
        ordered geodataframe with the 100 most important gaps to fill

    References
    ----------
    [1] Vybornova, A., Cunha, T., Gühnemann, A. and Szell, M. (2023), Automated Detection of Missing Links in Bicycle Networks. Geogr Anal, 55: 239-267. https://doi.org/10.1111/gean.12324
    """
    # check if user input is valid
    if type(city_query) != str:
        raise TypeError("city_query must be a string")
    if type(proj_crs) != str:
        raise TypeError("proj_crs must be a string")
    if type(radius) != int:
        raise TypeError("radius must be an integer")
    if type(maxgap) != int:
        raise TypeError("maxgap must be an integer")
    if type(export_data) is not bool:
        raise TypeError("export_data must be a boolean")
    if export_file_format != "geojson" and export_file_format != "gpkg":
        raise ValueError("export_file_format must be 'geojson' or 'gpkg'")
    if type(import_files) is not dict:
        raise TypeError("import_files must be a dictionary")
        # Prepare special case import_files. Turn it into a defaultdict where missing keys are None.
    import_files = defaultdict(lambda: None, import_files)

    if import_files['street_network'] is not None:
        print("Importing street network..")
        g = import_network(import_files['street_network'])

    else:
        ### downloading and preprocessing data from OSM
        print("Downloading OSM data..")

        ox.settings.useful_tags_way = ["highway", "cycleway", "cycleway:right", "cycleway:left", "cycleway:both", "cyclestreet"]

        # fetch street network data from osmnx
        g = ox.graph_from_place(
            city_query, network_type='all', simplify=False
        )

    g = ox.simplify_graph(
        g,
        edge_attrs_differ=['cycleway', 'highway', 'cycleway:right', 'cycleway:left', 'cycleway:both']
    )

    # check which edges have existing bike infrastructure as defined in config/config_osm.yml and assign boolean value to edges
    g = map_edges_to_bike_infrastructure(g)

    print("Dropping parallel edges..")
    edges_to_drop = find_edges_to_drop(g)
    g.remove_edges_from(edges_to_drop)

    print("Detecting gaps..")
    # Capital-G: the Graph() object we will be working with from now on
    G = nx.Graph(g)

    # add weight to edges for path calculation, using penalty
    G = weigh_edges(G, penalty)

    # creating new gdfs for nodes and edges of G
    nodes_gdf = graph_nodes_to_gdf(G)
    edges_gdf = graph_edges_to_gdf(G)
    nodes_gdf = nodes_gdf.to_crs(proj_crs)
    edges_gdf = edges_gdf.to_crs(proj_crs)

    # finding contact nodes in network
    contact_nodes = find_contact_nodes(G)

    # finding potential gaps in network
    potential_gaps = find_potential_gaps(contact_nodes, nodes_gdf, maxgap)

    # add routing for gaps in network
    found_gaps, found_gaps_nsp = find_actual_gaps(G, potential_gaps)

    # calculating local betweenness score dependent on radius
    print("Calculating betweenness centrality..")
    ebc = compute_local_betweenness_centrality(G, nodes_gdf, radius)

    print("Ranking gaps..")
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

    # only keep the 1000 most important gaps before declustering. If there are fewer than 1000 gaps keep only those
    if df.shape[0] > 1000:
        df = df.iloc[:1000]

    #decluster edges
    gap_df = gap_declustering(df, G, ebc)
    gap_df = gap_df.sort_values(by="benefit", ascending=False).reset_index(drop=True)

    # compute list of all edges that are part of each gap, where each edge is u,v
    gap_df["edge_list"] = gap_df.path.apply(lambda x: get_correct_edgetuples(edges_gdf, x))

    # only keep the 100 most important gaps. If there are fewer than 100 gaps keep only those
    if gap_df.shape[0] > 100:
        gap_df = gap_df.iloc[:100]

    # assign source and target nodes for each gap
    gap_df["source"] = [t[0] for t in gap_df.path]
    gap_df["target"] = [t[-1] for t in gap_df.path]

    # add actual geometries in network to each gap
    gdf = create_gdf_with_geoms(gap_df, edges_gdf)

    gdf['ordering'] = gdf.index
    gdf['length'] = gdf['geometry'].length

    edges_pbi_gdf = edges_gdf[edges_gdf["pbi"] == 1]

    # Back to unprojected (potentially). No more calculations after here.
    gdf.to_crs(epsg=4326, inplace=True)
    edges_pbi_gdf.to_crs(epsg=4326, inplace=True)
    edges_gdf.to_crs(epsg=4326, inplace=True)

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
        ### save data
        print("Saving data..")
        edges_pbi_gdf.drop(["osmid"], axis=1, inplace=True)
        edges_gdf.drop(["osmid"], axis=1, inplace=True)
        city_boundary = ox.geocoder.geocode_to_gdf(city_query)
        city_boundary.to_crs(epsg=4326, inplace=True)
        if export_file_format == "geojson":
            gdf.to_file(settings.export_path + export_data_filename, driver="GeoJSON", RFC7946="YES")
            edges_pbi_gdf.to_file(settings.export_path + slugify(city_string) + "-fixbikenet" +  "-existing_bike_network.geojson", driver="GeoJSON", RFC7946="YES")
            edges_gdf.to_file(settings.export_path + slugify(city_string) + "-fixbikenet" + "-existing_street_network.geojson", driver="GeoJSON", RFC7946="YES")
            city_boundary.to_file(settings.export_path + slugify(city_string) + "-city_boundary.geojson", driver="GeoJSON", RFC7946="YES")
        elif export_file_format == "gpkg":
            gdf.to_file(settings.export_path + export_data_filename, driver="GPKG", layer="Identified gaps")
            edges_pbi_gdf.to_file(settings.export_path + export_data_filename, driver="GPKG", layer="Existing bike network", append=True)
            edges_gdf.to_file(settings.export_path + export_data_filename, driver="GPKG", layer="Existing street network", append=True)
            city_boundary.to_file(settings.export_path + export_data_filename, driver="GPKG", layer="City boundary", append=True)

        if export_plot:
            print("Saving plot..")
            os.makedirs("./results/plots/", exist_ok=True)
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            edges_pbi_gdf.plot(ax=ax, color="grey")
            gdf.plot(ax=ax, color="red")
            ax.set_axis_off()
            fig.savefig(f"./results/plots/"+export_data_filename+".png", dpi=150, bbox_inches='tight')
            plt.close()

    return gdf