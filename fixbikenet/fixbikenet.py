# import packages
import pandas as pd
import osmnx as ox
import os
import matplotlib.pyplot as plt

# import functions
from fixbikenet.functions import *

def fixbikenet(
    city_name,
    proj_crs = "3857",
    radius = 2500,
    maxgap = 200,
    penalty = {0: 5, 1: 1},
    export_data = True,
    export_file_format="geojson",
    export_plot=False,
):
    """
    Finds gaps in bicycle networks and returns the 100 that are the most important to fill.
    Parameters
    ----------
    city_name : str
        name of the city that the analysis should be performed on
    proj_crs : str, default '3857'
        coordinate reference system that is used to project osm data. Default is '3857' (WGS 84 / Pseudo-Mercator)
    radius : int, default 2500
        cut-off length for computation of local betweenness centrality, in meters
    maxgap : int, default 50
        maximum distance between node pairs to be considered as a potential gap
    penalty : dict, default {0:5, 1: 1}
        weighing for shortest path calculations, where streets without protected bike infrastructure (pbi) get penalized
    export_data : bool, optional, default True
        If set to True, data will be saved to a file. The filename is [slug].gpkg, where slug is a string id made out of city_name
    export_file_format : str, optional, default "geojson"
        File format for the data export, relevant if export_data set to True. Default "geojson", also possible "gpkg". If exporting as geojson, generates extra files for street network and city boundary. If exporting as gkpg, these are added all in one file as extra layers.
    export_plot : bool, optional, default False
        If set to True, plot will be saved to a file
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
    if type(export_data) is not bool:
        raise TypeError("export_data must be a boolean")
    if export_file_format != "geojson" and export_file_format != "gpkg":
        raise ValueError("export_file_format must be 'geojson' or 'gpkg'")

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
    if df.shape[0] > 100:
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

    # Generate export data filename
    if export_data:
        os.makedirs("./results/", exist_ok=True)
        export_data_filename = (
                city_name + "-" + export_file_format
        )

    if export_data:
        ### save data
        print("Saving data..")
        edges_gdf.drop(["osmid"], axis=1, inplace=True)
        city_boundary = ox.geocoder.geocode_to_gdf(city_name)
        city_boundary.to_crs(epsg=proj_crs, inplace=True)
        # We have meter precision, so rounding to integers is fine. Better would be to
        # change dtypes to int, but this does not seem possible without manual looping.
        city_boundary.geometry = city_boundary.geometry.set_precision(grid_size=1)
        edges_gdf.geometry = edges_gdf.geometry.set_precision(grid_size=1)
        gdf.geometry = gdf.geometry.set_precision(grid_size=1)
        if export_file_format == "geojson":
            gdf.to_file("./results/"+export_data_filename, driver="GeoJSON")
            edges_gdf.to_file("./results/"+city_name+"-street_network.geojson", driver="GeoJSON")
            city_boundary.to_file("./results/"+city_name+"-city_boundary.geojson", driver="GeoJSON")
        elif export_file_format == "gpkg":
            gdf.to_file("./results/"+export_data_filename, driver="GPKG", layer="Identified gaps")
            edges_gdf.to_file("./results/"+export_data_filename, driver="GPKG", layer="Street network", append=True)
            city_boundary.to_file("./results/"+export_data_filename, driver="GPKG", layer="City boundary", append=True)

        if export_plot:
            print("Saving plot..")
            os.makedirs("./results/plots/", exist_ok=True)
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))
            edges_gdf.plot(ax=ax, color="grey")
            gdf.plot(ax=ax, color="red")
            ax.set_axis_off()
            fig.savefig(f"./results/plots/"+export_data_filename+".png", dpi=150, bbox_inches='tight')
            plt.close()

    return gdf