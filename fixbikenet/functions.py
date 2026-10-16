"""Utility functions for `fixbikenet`."""

import itertools
import os
import re
from collections import defaultdict

import numpy as np
import pandas as pd

from . import constants, settings, osm

pd.set_option('display.max_columns', None) # for debugging
import datetime
import sys  # noqa: F401, use sys.exit() for debugging

import geopandas as gpd
import networkx as nx
import osmnx as ox
import shapely
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from tqdm import tqdm


def _validate_parameters(
        city_query,
        radius,
        mingap,
        maxgap,
        export_data,
        import_files,
    ):
    """ Check if user parameter input is valid. If not, raise an exception or 
    warning.
    
    Parameters
    ----------
    Same as `growbikenet.growbikenet()`
    Additionally:
    constants._PRESET_TAGS : dict
        Dictionary of preset seed point tags.

    Returns
    -------
    import_files : defaultdict
        Defaultdict of file names to import.

    """
    if type(city_query) != str:
        raise TypeError("city_query must be a string")
    if type(radius) != int:
        raise TypeError("radius must be an integer")
    if type(mingap) != int:
        raise TypeError("mingap must be an integer")
    if type(maxgap) != int:
        raise TypeError("maxgap must be an integer")
    if type(export_data) is not bool:
        raise TypeError("export_data must be a boolean")
    
    if type(import_files) is not dict:
        raise TypeError("import_files must be a dictionary")
    # Prepare special case import_files. Turn it into a defaultdict where missing keys are None.
    import_files = defaultdict(lambda: None, import_files)

    # Import files
    for filename in ['city_boundary','street_network']:
        if type(import_files[filename]) is str and not os.path.isfile(settings.import_path+import_files[filename]):
            raise FileNotFoundError(filename+" not found")
    
    return import_files

def _validate_settings():
    """ Check if user settings input is valid. If not, raise an exception or 
    warning.

    Returns
    -------
    setting_was_auto : dict
        Dictionary remembering which setting or constant was set to auto, so 
        it can be reset to auto in the end.
    """

    if type(constants._CRS_CALCULATIONS) is not str:
        raise TypeError("constants._CRS_CALCULATIONS must be a string")
    if settings.export_file_format != "geojson" and settings.export_file_format != "gpkg":
        raise ValueError("settings.export_file_format must be 'geojson' or 'gpkg'")

    setting_was_auto = {'crs_calculations': False}
    # Ask whether constants._CRS_CALCULATIONS was 'auto'
    if constants._CRS_CALCULATIONS == 'auto':
        setting_was_auto['crs_calculations'] = True
    return setting_was_auto

def _resolve_crs_calculations(gdf):
    """ Resolve constants._CRS_CALCULATIONS = 'auto'
    
    Parameters
    ----------
    gdf : geopandas.geodataframe.GeoDataFrame
        A geodataframe from which to estimate the UTM CRS
    """
    if constants._CRS_CALCULATIONS == 'auto':
        constants._CRS_CALCULATIONS = gdf.estimate_utm_crs()

def _reset_auto_settings(setting_was_auto):
    """Reset settings and constants to auto.
    """
    if setting_was_auto['crs_calculations']:
        constants._CRS_CALCULATIONS = 'auto'

def _print_header(city_query):
    """Print header.
    """
    if not settings.silent:
        print((constants._PROGRESS_BAR_DESC_LENGTH+constants._PROGRESS_BAR_LENGTH)*"=")
        print("RUNNING FIXBIKENET FOR CITY: " + city_query)
        print((constants._PROGRESS_BAR_DESC_LENGTH+constants._PROGRESS_BAR_LENGTH)*"-"+"╮")

def _print_footer(export_data, endtime, starttime):
    """Print footer.
    """
    if not settings.silent:
        print((constants._PROGRESS_BAR_DESC_LENGTH+constants._PROGRESS_BAR_LENGTH)*"-"+"╯")
        if export_data:
            print("Data exported to "+settings.export_path)
        if export_data or export_plots:
            print((constants._PROGRESS_BAR_DESC_LENGTH+constants._PROGRESS_BAR_LENGTH)*"-")
        print("FINISHED IN " + str(datetime.timedelta(seconds = round(endtime - starttime))))
        print((constants._PROGRESS_BAR_DESC_LENGTH+constants._PROGRESS_BAR_LENGTH)*"=")

def initialize_progress_bar(desc_string, total=1, unit="step"):
    """Initialize tqdm progress bar.
    """
    return tqdm(
        desc=("{:<"+str(constants._PROGRESS_BAR_DESC_LENGTH)+"}").format(desc_string),
        total=total,
        unit=unit,
        bar_format='{l_bar}{bar:'+str(constants._PROGRESS_BAR_LENGTH-7)+'}{r_bar}',
        disable=settings.silent,
    )


def download_network(city_query, network_type='drive', custom_filter=None, retain_all=True, city_boundary_geometry=None):
    """Download and prepare a street network from OSM via OSMnx.

    Downloads a network with a given `network_type` and `custom_filter` using ``ox.graph_from_place()``. Then, stores the undirected OSM data in geodataframes and projects using `constants._CRS_CALCULATIONS`.

    Parameters
    ----------
    city_query : str
        Name of the city that the analysis should be performed on. Overruled 
        (for data fetching) if `city_boundary_geometry` is set.
    network_type : {'drive', 'all', 'all_public', 'bike', 'drive_service', 'walk'}, default 'drive'
        What type of street network to retrieve if `custom_filter` is None.
    custom_filter : None or str or list[str], default None
        A custom ways filter to be used instead of the `network_type` presets.
    retain_all : bool, default True
        If True, return the entire graph even if it is not connected, useful 
        for disconnected bicycle networks. If False, retain only the largest 
        weakly connected component, useful for road networks.
    city_boundary_geometry : None or shapely.Polygon or shapely.MultiPolygon, 
    default None
        If not set to None, the study area is selected from this geometry.

    Returns
    -------
    nodes : geopandas.geodataframe.GeoDataFrame
        Extracted OSM nodes, projected.
    edges : geopandas.geodataframe.GeoDataFrame
        Extracted OSM edges, projected.
    g_undir : networkx.classes.multigraph.MultiGraph
        Extracted networkX graph, undirected.
    """
    # Fetch street network data from osmnx
    if city_boundary_geometry is None:
        g = ox.graph_from_place(
        city_query, network_type=network_type, custom_filter=custom_filter, retain_all=retain_all
        )
    else:
        g = ox.graph_from_polygon(
        city_boundary_geometry, network_type=network_type, custom_filter=custom_filter, retain_all=retain_all
        )

    g_undir = g.to_undirected().copy() # convert to undirected (dropping OSMnx keys!)

    return g_undir


def import_network(street_network):
    """Import and project a street network from gpkg file

    For all edges between a pair of nodes u and v there must be one edge with key 0.

    Parameters
    ----------
    street_network : str
        The street network will be loaded from this file. Must be a gpkg file in unprojected crs EPSG:4326 with layers nodes and edges, with the structure that a osmnx street network g has after saving its undirected version via ox.io.save_graph_geopackage(). For example:
        >>> g = ox.graph_from_place("Barcelona", network_type='all')
        >>> g = nx.MultiGraph(ox.convert.to_digraph(g))
        >>> ox.io.save_graph_geopackage(g, "Barcelona_streets.gpkg")
    import_path : str, default settings.import_path
        Path to import files.

    Returns
    -------
    nodes : geopandas.geodataframe.GeoDataFrame
        Extracted OSM nodes, projected
    edges : geopandas.geodataframe.GeoDataFrame
        Extracted OSM edges, projected
    g_undir : networkx.classes.multigraph.MultiGraph
        Extracted networkX graph, undirected
    city_boundary_gdf : geopandas.geodataframe.GeoDataFrame
        Convex hull of the street network
    """

    nodes = gpd.read_file(settings.import_path+street_network, layer='nodes')
    edges = gpd.read_file(settings.import_path+street_network, layer='edges')

    # Set indices as required by osmnx.convert.graph_from_gdfs
    # See: https://osmnx.readthedocs.io/en/stable/user-reference.html#osmnx.utils_graph.graph_from_gdfs
    nodes = nodes.set_index(['osmid'])
    edges = edges.set_index(['u', 'v', 'key'])

    g = ox.convert.graph_from_gdfs(nodes, edges)

    #city_boundary_gdf = gpd.GeoDataFrame(gpd.GeoSeries(nodes.union_all().convex_hull), geometry=0, crs=nodes.crs) # We do this before the projection of nodes below
    # To do: To be super-correct, the hull should be buffered by settings.seed_point_snap_distance (in degrees due to being unprojected)

    return g


def _import_data_files(import_files):
    """Import data files.
    """
    num_data_files = int(bool(import_files['point_data'])) + int(bool(import_files['trip_data']))
    point_data = None
    trip_data = None
    if num_data_files:
        progress_bar = initialize_progress_bar("Importing data files", num_data_files, "file")
        if import_files['point_data']:
            point_data = gpd.read_file(settings.import_path+import_files['point_data'])
            progress_bar.update(1)
        if import_files['trip_data']:
            trip_data = pd.read_csv(settings.import_path+import_files['trip_data'])
            progress_bar.update(1)
        progress_bar.close()
    return num_data_files, point_data, trip_data


def assign_pbi_to_edges(g):
    """Assign a boolean pbi attribute to all edges in a graph depending if they 
    are considered protected bike infrastructure (pbi).

    Parameters
    ----------
    g : networkx.MultiDiGraph
        Simplified graph representing the street network.

    Returns
    -------
    g : networkx.MultiDiGraph
        Simplified graph representing the street network, with added binary edge attribute "pbi".
    """
    for edge in g.edges(keys=True):
        assigned_pbi = 0
        for tag in osm.PBI_DICT:
            if g.edges[edge].get(tag) in osm.PBI_DICT[tag]:
                assigned_pbi = 1
        if not assigned_pbi: # Check if the edge fulfills a subcriterion
            for tag in osm.PBI_DICT_SUB:
                subtag = list(osm.PBI_DICT_SUB[tag][1].keys())[0]
                if g.edges[edge].get(tag) in osm.PBI_DICT_SUB[tag][0] and g.edges[edge].get(subtag) in osm.PBI_DICT_SUB[tag][1][subtag] and g.edges[edge].get("access") != 'private':
                    assigned_pbi = 1
        g.edges[edge]["pbi"] = assigned_pbi

    return g


def bike_infra_mapping_gdf(g, edges_gdf):
    """
    add binary edge attribute pbi to edges_gdf

    Parameters
    ----------
    g : networkx.MultiDiGraph
        simplified graph representing the street network, with added binary edge attribute "pbi"
    edges_gdf: geopandas.GeoDataFrame
        edges representing the street network

    Returns
    -------
    edges_gdf: geopandas.GeoDataFrame
        edges representing the street network with added binary attribute "pbi"
    """
    # Build dict of edge attribute
    attr_dict = {
        (u, v, k): data['pbi']
        for u, v, k, data in g.edges(keys=True, data=True)
    }

    # Map to GeoDataFrame
    edges_gdf['pbi'] = edges_gdf.index.map(attr_dict)
    return edges_gdf

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

    for uv in tqdm(
            uvs,
            desc=("{:<"+str(constants._PROGRESS_BAR_DESC_LENGTH)+"}").format("Dropping parallel edges"),
            leave=True,
            unit="edge",
            total=len(uvs),
            bar_format='{l_bar}{bar:'+str(constants._PROGRESS_BAR_LENGTH-7)+'}{r_bar}',
            disable=settings.silent,
        ):
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

def weigh_edges(G):
    """Add weight parameter to all edges in G, calculated by multiplying the
    length of the edge with the corresponding penalty value.

    Parameters
    ----------
    G : networkx.Graph
        Undirected simple graph representing the street network.

    Returns
    -------
    G : networkx.Graph
        Undirected simple graph representing the street network with weighted 
        edges.
    """
    for edge in G.edges:
        # compute edge weight
        edge_pbi = G.edges[edge]["pbi"]
        edge_length = G.edges[edge]["length"]
        edge_weight = edge_length * constants._ROUTING_PENALTY[edge_pbi]
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
    contact_nodes : list
        list of all nodes that fulfill criteria to be a contact node
    nodes_gdf : geopandas.GeoDataFrame
        all nodes in street network
    maxgap : int
        user defined maximal euclidean distance between two contact nodes

    Returns
    -------
    potential_gaps : list
        all unique potential gaps in protected bicycle network
    """
    potential_gaps = []
    nodes_gdf['osmid'] = nodes_gdf.index
    contact_nodes_gdf = nodes_gdf[nodes_gdf['osmid'].isin(contact_nodes)]

    for node in contact_nodes:
        node_buffer = contact_nodes_gdf.loc[node, "geometry"].buffer(maxgap)
        q = contact_nodes_gdf.sindex.query(node_buffer, predicate="intersects")
        neighbours = list(contact_nodes_gdf.iloc[q].index)
        neighbours.remove(node)
        # convention: sort by ascending OSMID...
        node_pairs = [tuple(sorted(z)) for z in zip([node] * len(neighbours), neighbours)]
        potential_gaps += node_pairs

    # ... so that we can easily deduplicate
    potential_gaps = list(set(potential_gaps))
    return potential_gaps

def find_actual_gaps(G, potential_gaps, mingap):
    """Determine which potential gaps are actual gaps by finding paths between 
    all contact nodes and only keeping the gaps that have no protected bike
    infrastructure.

    Parameters
    ----------
    G : networkx.Graph
        Undirected simple graph representing the street network with weighted 
        edges.
    potential_gaps : list
        All unique potential gaps in protected bicycle network.
    mingap : int
        Minimum distance between node pairs to be considered as a potential gap, in meters.

    Returns
    -------
    found_gaps : list
        List of all gaps in protected bicycle network.
    found_gaps_nsp : list
        List of paths in network for all gaps in protected bicycle network.
    """
    pbi_dict = nx.get_edge_attributes(G, "pbi")

    found_gaps = []
    found_gaps_nsp = []

    for u, v in tqdm(
            potential_gaps,
            desc=("{:<"+str(constants._PROGRESS_BAR_DESC_LENGTH)+"}").format("Finding gaps"),
            leave=True,
            unit="gap",
            total=len(potential_gaps),
            bar_format='{l_bar}{bar:'+str(constants._PROGRESS_BAR_LENGTH-7)+'}{r_bar}',
            disable=settings.silent,
        ):

        try:
            nodelist = nx.shortest_path(G, u, v, weight="length")
        except nx.NetworkXNoPath:
            continue

        # assume valid until proven otherwise
        valid = True

        for i in range(len(nodelist) - 1):
            a, b = nodelist[i], nodelist[i + 1]

            # undirected edge normalization (ONLY once per lookup)
            key = (a, b) if (a, b) in pbi_dict else (b, a)

            if pbi_dict.get(key, 1) != 0:
                valid = False
                break

        gaplength = nx.shortest_path_length(G, u, v, weight="length")
        if valid and gaplength >= mingap:
            found_gaps.append((u, v))
            found_gaps_nsp.append(nodelist)

    return found_gaps, found_gaps_nsp


def add_point_data_to_net(points, edges):
    """Match point data to network edges.

    Parameters
    ----------
    points : geopandas.geodataframe.GeoDataFrame
        A geodataframe of unprojected point geometries, optional having a 
        column ``num`` containing an integer. This could be (number of) point 
        events like crashes or citizen feedback to improve bike infrastructure. 
        If a ``num`` column is not provided, assumes 1 per point.
    edges : geopandas.geodataframe.GeoDataFrame
        A geodataframe of projected spatial network edges. This is the routed 
        network of seed points.
    matching_distance : int, default `settings.import_point_data_snap_distance`
        Matching distance in meters. Set via 
        `settings.import_point_data_snap_distance`.

    Returns
    -------
    edges_with_data : geopandas.geodataframe.GeoDataFrame
        The same spatial network edges, but with a new int column 
        ``num_points`` populated with the summed up ``num`` values of all 
        points, matched to the closest links if within `matching_distance`. 
    """

    edges_with_data = edges.copy()

    points_projected = points.to_crs(constants._CRS_CALCULATIONS)

    # If column "num" is not provided assume 1 event per point
    if 'num' in points_projected.columns:
        nums = points_projected['num']
    else:
        nums = [1] * len(points_projected)

    # Initialize the 'num_points' column to 0 for all edges
    edges_with_data['num_points'] = 0 * len(edges_with_data)

    # Get geometries of edges and points
    edges_geoms = edges_with_data['geometry']
    points_geoms = points_projected['geometry']

    # Build an r-tree spatial index by position for subsequent iloc
    rtree = STRtree(edges_geoms)    
                            
    for point in points_geoms.items(): # point = (id, POINT(x, y))

        # Query the tree for all the edges within the matching distance of the point
        edges_within_matching_distance = rtree.query(
            point[1],
            predicate='dwithin',
            distance=settings.import_point_data_snap_distance
        )

        # If no edges are within the matching distance, continue to the next point
        if len(edges_within_matching_distance) == 0:
            continue

        # Calculate the distances from the point to each of the edges, and round to 10 decimal places to avoid floating point precision issues
        distances = []
        for edge in edges_within_matching_distance:
            distance = np.around(shapely.distance(point[1], edges_geoms.iloc[edge]), decimals=10)
            distances.append(distance)

        # Get the edges that are closest to the point
        closest_edges = edges_within_matching_distance[np.where(distances == np.min(distances))]

        # Get the lowest index of the closest edges
        closest_edges_min_index = np.sort(closest_edges)[0]

        # Get the number of events at the point
        num = nums[point[0]]

        # Add the number of events to the nearest edge
        edges_with_data.loc[closest_edges_min_index, 'num_points'] += num

    # Move the 'geometry' column to the end of the GeoDataFrame
    # Necessary for testing the function
    cols = [c for c in edges_with_data.columns if c != 'geometry'] + ['geometry']
    edges_with_data = edges_with_data[cols]

    return edges_with_data


def _get_weighted_distances(B, num_types, inverted=False):
    """Get weighted distances by edge attribute num_types.

    Parameters
    ----------
    B : networkx.classes.multigraph.MultiGraph
        The routed, grown bicycle network graph, where edges have the attribute 
        `num_types`. The numerical attribute "distance" must exist for all 
        edges.
    num_types : str
        Name of the attribute to weight the distances.

    Returns
    -------
    dist_weighted_by_types_dict : dict
        Dictionary where keys are the edges (tuples of node ids), and values 
        are the weighted distances following [1]_.

    Notes
    -----
    The calculation follows [1]_, only without +1 in the numerator and with a 
    small epsilon to prevent division by zero.

    References
    ----------
    .. [1] P. Folco, L. Gauvin, M. Tizzoni, M. Szell, `Data-driven micromobility network planning for demand and safety`, Environment and planning B: Urban analytics and city science 50(8), 2087-2102 (2023)
    """

    num_types_dict = nx.get_edge_attributes(B, num_types)
    dist_dict = nx.get_edge_attributes(B, "distance")
    num_types_per_km_dict = {}

    for k,d in dist_dict.items():
        if d != 0:
            num_types_per_km_dict[k] = 1000*num_types_dict[k]/d
        else: # To do: How can it be zero? Turin self-loop: (1668523317, 1668523317)
            num_types_per_km_dict[k] = 0
    max_n = max(num_types_per_km_dict.values())+1e-10

    dist_weighted_by_types_dict = {}
    for k,d in dist_dict.items():
        if inverted:
            dist_weighted_by_types_dict[k] = d * (1+settings.import_data_impact*(num_types_per_km_dict[k]/max_n))
        else:
            dist_weighted_by_types_dict[k] = d / (1+settings.import_data_impact*(num_types_per_km_dict[k]/max_n))

    return dist_weighted_by_types_dict


def compute_local_betweenness_centrality(G, nodes_gdf, radius):
    """
    computes weighted betweenness centrality for paths within radius

    Parameters
    ----------
    G: networkx.Graph
        undirected simple graph representing the street network with weighted edges
    nodes_gdf: geopandas.GeoDataFrame
        all nodes in street network
    radius: int
        maximum length of path for betweennessn centrality calculation, set by user

    Returns
    -------
    ebc: dict
        local betweenness centrality values for all edges in network
    """
    # set current ebc value of all G edges to 0
    for edge in G.edges:
        G.edges[edge]["ebc"] = 0

    # create dict that will be updated at each step
    ebc = nx.get_edge_attributes(G, "ebc")

    # For each node, compute "local" ebc (buffered with radius!)
    # For computational reasons, only over a subset of randomly drawn 
    # constants._BETWEENNESS_RANDOM_NODES nodes
    random_nodes = np.random.choice(list(G.nodes), size=constants._BETWEENNESS_RANDOM_NODES)
    for node in tqdm(
            random_nodes,
            desc=("{:<"+str(constants._PROGRESS_BAR_DESC_LENGTH)+"}").format("Calculating betweenness"),
            leave=True,
            unit="step",
            total=len(random_nodes),
            bar_format='{l_bar}{bar:'+str(constants._PROGRESS_BAR_LENGTH-7)+'}{r_bar}',
            disable=settings.silent,
        ):
        node_buffer = nodes_gdf.loc[node, "geometry"].buffer(radius)
        q = nodes_gdf.sindex.query(node_buffer, predicate="intersects")
        neighbours = list(nodes_gdf.iloc[q].index)
        local_ebc = nx.edge_betweenness_centrality_subset(
            G=G,
            sources=[node],
            targets=neighbours,
            normalized=False,  # important! otherwise the addition makes no sense
            weight="weight"  # using penalty for non-pbi
        )

        # update ebc dictionary
        for k, v in local_ebc.items():
            ebc[k] += v  # updating ebc!!
    return ebc

def rank_gaps_by_b(found_gaps_nsp, G, ebc):
    """Calculate b for all gaps.

    Parameters
    ----------
    found_gaps_nsp : list
        List of paths in network for all gaps in protected bicycle network.
    G : networkx.Graph
        Undirected simple graph representing the street network with weighted
        edges.
    ebc : dict
        Local betweenness centrality values for all edges in network.

    Returns
    -------
    Bs: list
        list of values of b for all gaps in protected bicycle network
    """
    Bs = []
    for nodelist in tqdm(
            found_gaps_nsp,
            desc=("{:<"+str(constants._PROGRESS_BAR_DESC_LENGTH)+"}").format("Ordering gaps"),
            leave=True,
            unit="gap",
            total=len(found_gaps_nsp),
            bar_format='{l_bar}{bar:'+str(constants._PROGRESS_BAR_LENGTH-7)+'}{r_bar}',
            disable=settings.silent,
        ):
        edgelist = [tuple(sorted(z)) for z in zip(nodelist, nodelist[1:])]
        lengths = np.array([G.edges[edge]["distance"] for edge in edgelist])
        lengths_weighted = np.array([G.edges[edge]["distance_weighted"] for edge in edgelist])
        #ebcs = np.array([ebc[edge] for edge in edgelist])
        ebcs = np.array([ebc.get(edge, ebc.get(edge[::-1])) for edge in edgelist])
        B = sum(lengths_weighted * ebcs) / sum(lengths)
        Bs.append(B)
    return Bs

def get_correct_edgetuples(edge_gdf, nodelist):
    """
    helper function that maps a node list (output of nx.shortest_paths)
    to the correct set of edge tuples that can be used for INDEXING THE EDGE GDF

    Parameters
    ----------
    edge_gdf: geopandas.geodataframe.GeoDataFrame
        The street network, in a projected coordinate reference system
    nodelist: list
        A list of nodes that make up source and targets of edges

    Returns
    -------
    edgelist_final: list
        List of edge tuples that can be used for INDEXING THE EDGE GDF
    """
    edgelist_prelim = zip(nodelist, nodelist[1:])
    edgelist_final = []
    temp_gdf = edge_gdf.sort_index() # To circumvent PerformanceWarning, see https://stackoverflow.com/questions/54307300/what-causes-indexing-past-lexsort-depth-warning-in-pandas
    for edge_prelim in edgelist_prelim:
        if edge_prelim in temp_gdf.index:
            edgelist_final.append(edge_prelim)
        else:
            edgelist_final.append(tuple([edge_prelim[1], edge_prelim[0]]))
    return edgelist_final

def create_gdf_with_geoms(df, edges):
    """
    Parameters
    ----------
    df: pandas.DataFrame
        Dataframe with path nodes and path edges
    edges: geopandas.GeoDataFrame
        The street network, in a projected coordinate reference system

    Returns
    -------
    gdf: geopandas.GeoDataFrame
        projected GeoDataFrame with path nodes and path edges and merged geometries
    """
    # get geometry by merging all geoms from edge gdf
    df = df.copy()
    df["geometry"] = df.edge_list.apply(
        lambda x: edges.loc[x].geometry.union_all()
    )
    # convert edges into a gdf
    gdf = gpd.GeoDataFrame(df, crs=edges.crs, geometry="geometry")
    # merge multilinestring into linestring where possible (should be possible everywhere)
    gdf["geometry"] = gdf.line_merge()
    return gdf

def graph_nodes_to_gdf(G):
    """
    Parameters
    ----------
    G: networkx.Graph
        undirected simple graph representing the street network with weighted edges

    Returns
    -------
    nodes_gdf: geopandas.GeoDataFrame
        geodataframe with nodes from G
    """
    rows = []
    for n, data in G.nodes(data=True):
        rows.append({
            "node": n,
            **data,
            "geometry": Point(data["x"], data["y"])
        })
    nodes_gdf = gpd.GeoDataFrame(
        rows,
        geometry="geometry",
        crs=G.graph.get("crs")
    ).set_index("node")

    return nodes_gdf

def graph_edges_to_gdf(G):
    """
    Parameters
    ----------
    G: networkx.Graph
        undirected simple graph representing the street network with weighted edges

    Returns
    -------
    edges_gdf: geopandas.GeoDataFrame
        geodataframe with edges from G, including edge attributes
    """
    rows = []
    for u, v, data in G.edges(data=True):
        # if geometry already exists on the edge, use it
        if "geometry" in data:
            geom = data["geometry"]
        else:
            # otherwise build a straight line from node coordinates
            geom = LineString([
                (G.nodes[u]["x"], G.nodes[u]["y"]),
                (G.nodes[v]["x"], G.nodes[v]["y"])
            ])
        rows.append({
            "u": u,
            "v": v,
            **data,
            "geometry": geom
        })
    edges_gdf = gpd.GeoDataFrame(
        rows,
        geometry="geometry",
        crs=G.graph.get("crs")
    ).set_index(["u", "v"])

    return edges_gdf

def compute_benefit_metric(comp, node_path, ebc):
    """
    computes Benefit metric B for edge in connected component of edges.

    Parameters
    ----------
    comp : networkx.Graph
        connected component of edges
    node_path : list
        list of nodes on path
    ebc: dict
        local betweenness centrality values for all edges in network

    Returns
    -------
    B: float
        Benefit metric B for edge
    """
    edgelist = [tuple(sorted(z)) for z in zip(node_path, node_path[1:])]
    lengths = np.array([comp.edges[edge]["length"] for edge in edgelist])
    #ebcs = np.array([ebc[edge] for edge in edgelist])
    ebcs = np.array([ebc.get(edge, ebc.get(edge[::-1])) for edge in edgelist])
    B = sum(lengths * ebcs) / sum(lengths)
    return B

def gap_declustering(gaps_df, G, ebc, contact_nodes, mingap):
    """
    Parameters
    ----------
    gaps_df : pd.DataFrame
        Dataframe containing gaps in protected bicycle network
    G : networkx.Graph
        undirected simple graph representing the street network with weighted edges
    ebc : dict
        local betweenness centrality values for all edges in network
    contact_nodes : list
    mingap : int
        Minimum distance between node pairs to be considered as a potential gap, in meters.

    Returns
    -------
    result : pd.DataFrame
        Dataframe with node path for gaps and the newly calculated benefit metric
    """
    C = nx.Graph()
    C.graph.update(G.graph)
    gap_edges = set()
    contact_nodes = set(contact_nodes)

    # collect all edges used by the gap paths
    for nodelist in gaps_df["nodelist"]:
        for u, v in zip(nodelist[:-1], nodelist[1:]):
            if G.has_edge(u, v):
                gap_edges.add((u, v))
            elif G.has_edge(v, u):
                gap_edges.add((v, u))
            else:
                raise KeyError(f"Edge {(u, v)} not found in G")

    # add those edges + all their attributes
    for u, v in gap_edges:
        C.add_node(u, **G.nodes[u])
        C.add_node(v, **G.nodes[v])
        C.add_edge(u, v, **G[u][v])

    components = [
        C.subgraph(nodes).copy()
        for nodes in nx.connected_components(C)
    ]
    selected_paths = []
    selected_scores = []
    selected_names = []

    for comp in tqdm(
            components,
            desc=("{:<"+str(constants._PROGRESS_BAR_DESC_LENGTH)+"}").format("Declustering gaps"),
            leave=True,
            unit="cluster",
            total=len(components),
            bar_format='{l_bar}{bar:'+str(constants._PROGRESS_BAR_LENGTH-7)+'}{r_bar}',
            disable=settings.silent,
        ):
        while comp.number_of_edges() > 0:
            # contact nodes (in the paper it says degree != 2, but contact nodes work better)
            terminals = list(set(comp.nodes()) & contact_nodes)
            candidate_paths = []
            # shortest paths between all terminal pairs
            for source, target in itertools.combinations(terminals, 2):
                try:
                    node_path = nx.shortest_path(
                        comp,
                        source=source,
                        target=target,
                        weight="length"
                    )
                    gaplength = nx.shortest_path_length(
                        comp,
                        source=source,
                        target=target,
                        weight="length"
                    )
                    if node_path and gaplength >= mingap:
                        candidate_paths.append(node_path)
                except nx.NetworkXNoPath:
                    continue
            if not candidate_paths:
                break
            # Compute benefit metric
            best_path = None
            best_score = float("-inf")
            for path in candidate_paths:
                score = compute_benefit_metric(
                    comp,
                    path,
                    ebc
                )
                if score > best_score:
                    best_score = score
                    best_path = path
            if best_path is None:
                break

            # Store selected gap
            selected_paths.append(best_path)
            selected_scores.append(best_score)

            # Walk through edges until finding a name
            name = "n/a"
            for i in [-1]+list(range(len(best_path))):
                try: 
                    name = G[best_path[i]][best_path[i+1]]['name']
                except:
                    pass
                if name != "" and name != "n/a":
                    break
            if name == "":
                name = "n/a"
            selected_names.append(name)

            # Remove selected path
            edge_path = list(
                        zip(best_path[:-1], best_path[1:])
                    )
            comp.remove_edges_from(edge_path)
            # Remove isolated nodes
            isolates = list(nx.isolates(comp))
            comp.remove_nodes_from(isolates)
    result = pd.DataFrame(
        {
            "path": selected_paths,
            "benefit": selected_scores,
            "name": selected_names
        }
    )
    return result

def slugify(s):
    """Slugify a string

    Source: https://github.com/Chalarangelo/30-seconds-of-code/blob/master/content/snippets/python/s/slugify.md
    Note: A clean global solution would be using unidecode, but we do not want extra dependencies for this. We assume European city names in latin alphabet, some special letters like Hungarian long ö already mapped.

    Parameters
    ----------
    s : str
        String to slufigy

    Returns
    -------
    s : str
        Slugified string
    """
    s = s.lower().strip()
    s = re.sub(r'[\s-]+', '', s)  # Remove white spaces, -
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'^-+|-+$', '', s)
    tab = str.maketrans(
        "áéíóúàèìùòâêîôûäëïöüǎěǐǒǔãẽĩõũăåæçčıłñňøœřßșşšůŷÿźž",
        "aeiouaeiouaeiouaeiouaeiouaeiouaaaccilnnoorssssuyyzz"
    )
    s = s.translate(tab)
    return s