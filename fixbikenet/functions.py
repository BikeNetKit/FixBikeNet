import networkx as nx
import random
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import re
import itertools
import sys # use sys.exit() for debugging
from shapely.geometry import Point, LineString
from . import config
from . import settings

def import_network(street_network, import_path=settings.import_path):
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

    nodes = gpd.read_file(import_path+street_network, layer='nodes')
    edges = gpd.read_file(import_path+street_network, layer='edges')

    # Set indices as required by osmnx.convert.graph_from_gdfs
    # See: https://osmnx.readthedocs.io/en/stable/user-reference.html#osmnx.utils_graph.graph_from_gdfs
    nodes = nodes.set_index(['osmid'])
    edges = edges.set_index(['u', 'v', 'key'])

    g = ox.convert.graph_from_gdfs(nodes, edges)

    #city_boundary_gdf = gpd.GeoDataFrame(gpd.GeoSeries(nodes.union_all().convex_hull), geometry=0, crs=nodes.crs) # We do this before the projection of nodes below
    # To do: To be super-correct, the hull should be buffered by settings.seed_point_snap_distance (in degrees due to being unprojected)

    return g

def map_edges_to_bike_infrastructure(g):
    """
    map if edges in graph have bike infrastructure as specified in config.py

    Parameters
    ----------
    g :networkx.MultiDiGraph
        simplified graph representing the street network

    Returns
    -------
    g : networkx.MultiDiGraph
        simplified graph representing the street network, with added binary edge attribute "pbi"
    """

    # add binary edge attribute "pbi" (protected bike infra: True/False)
    for edge in g.edges(keys=True):
        if g.edges[edge].get("cycleway") in config.cycleway_bike_infra:
            g.edges[edge]["pbi"] = 1
        elif g.edges[edge].get("cycleway:right") in config.cycleway_right_bike_infra:
            g.edges[edge]["pbi"] = 1
        elif g.edges[edge].get("cycleway:left") in config.cycleway_left_bike_infra:
            g.edges[edge]["pbi"] = 1
        elif g.edges[edge].get("cycleway:both") in config.cycleway_both_bike_infra:
            g.edges[edge]["pbi"] = 1
        elif g.edges[edge].get("highway") in config.highway_bike_infra:
            g.edges[edge]["pbi"] = 1
        else:
            g.edges[edge]["pbi"] = 0
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

def find_actual_gaps(G, potential_gaps):
    """
        determines which potential gaps are actual gaps by finding paths between all contact nodes and only keeping the gaps that have no protected bike infrastructure

        Parameters
        ----------
        G: networkx.Graph
            undirected simple graph representing the street network with weighted edges
        potential_gaps: list
            all unique potential gaps in protected bicycle network

        Returns
        -------
        found_gaps: list
            list of all gaps in protected bicycle network
        found_gaps_nsp: list
            list of paths in network for all gaps in protected bicycle network
        """
    pbi_dict = nx.get_edge_attributes(G, "pbi")

    found_gaps = []
    found_gaps_nsp = []

    for u, v in potential_gaps:

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

        if valid:
            found_gaps.append((u, v))
            found_gaps_nsp.append(nodelist)

    return found_gaps, found_gaps_nsp

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

    # for each node, compute "local" ebc (buffered with radius!)
    # for comp feas, now only subset of randomly drawn 300 nodes
    random.seed(1312)
    random_nodes = random.choices(list(G.nodes), k=300)
    for node in random_nodes:
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
    """
    calculates b for all gaps

    Parameters
    ----------
    found_gaps_nsp: list
        list of paths in network for all gaps in protected bicycle network
    G: networkx.Graph
        undirected simple graph representing the street network with weighted edges
    ebc: dict
        local betweenness centrality values for all edges in network

    Returns
    -------
    Bs: list
        list of values of b for all gaps in protected bicycle network
    """
    Bs = []
    for nodelist in found_gaps_nsp:
        edgelist = [tuple(sorted(z)) for z in zip(nodelist, nodelist[1:])]
        lengths = np.array([G.edges[edge]["length"] for edge in edgelist])
        #ebcs = np.array([ebc[edge] for edge in edgelist])
        ebcs = np.array([ebc.get(edge, ebc.get(edge[::-1])) for edge in edgelist])
        B = sum(lengths * ebcs) / sum(lengths)
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

def gap_declustering(gaps_df, G, ebc, contact_nodes):
    """
    Parameters
    ----------
    gaps_df : pd.DataFrame
        Dataframe containing gaps in protected bicycle network
    G : networkx.Graph
        undirected simple graph representing the street network with weighted edges
    ebc: dict
        local betweenness centrality values for all edges in network
    contact_nodes : list

    Returns
    -------
    result: pd.DataFrame
        Dataframe with node path for gaps and the newly calculated benefit metric
    """
    C = nx.Graph()
    C.graph.update(G.graph)
    gap_edges = set()

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

    for comp in components:
        while comp.number_of_edges() > 0:
            # contact nodes (in the paper it says degree != 2, but contact nodes work better)
            terminals = [
                n
                for n in comp.nodes()
                if n in contact_nodes
            ]
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
                    if node_path:
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

            # Remove selected path
            edge_path = list(
                        zip(best_path[:-1], best_path[1:])
                    )
            comp.remove_edges_from(edge_path)
            # comp.remove_nodes_from(best_path)
            # Remove isolated nodes
            isolates = list(nx.isolates(comp))
            comp.remove_nodes_from(isolates)
    result = pd.DataFrame(
        {
            "path": selected_paths,
            "benefit": selected_scores,
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