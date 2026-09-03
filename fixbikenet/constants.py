"""Global constants for `fixbikenet` that can be tweaked during development, but 
should not be changed later by the user. Especially technical or internal 
constants start with an underscore.


_BETWEENNESS_RANDOM_NODES : int, default 300
    Number of random nodes to select for local betweenness calculations, for
    computational reasons.
_CLUSTER_GAPS_PER_FINAL_GAP : int, default 15
    Factor to multiply `numgaps` with, giving the number of gaps to consider for declustering.
_CRS_CALCULATIONS : str, default 'auto'
    EPSG code of the coordinate reference system that is used to project OSM 
    data for calculations. This has to be a distance-preserving projected CRS, 
    so '3857' (WGS 84 / Pseudo-Mercator) would be wrong! Option 'auto' selects
    the best UTM via `estimate_utm_crs()`.
_PROGRESS_BAR_DESC_LENGTH : int, default 23
    Character length of tqdm progress bar descriptions. This is the space given 
    to text like "Importing network data ", which is at the maximum of 23 
    characters.
_PROGRESS_BAR_LENGTH : int, default 23
    Character length of tqdm progress bars.
_ROUTING_PENALTY : dict, default {0: 1.5, 1: 1}
    Factor to multiply length of non-pbi/pbi for routing, to avoid routing
    through parallel streets when slightly longer pbi is available. By 
    default, non-pbi counts as 50% longer than pbi.
"""

_BETWEENNESS_RANDOM_NODES = 300
_CLUSTER_GAPS_PER_FINAL_GAP = 15
_CRS_CALCULATIONS = 'auto'
_PROGRESS_BAR_DESC_LENGTH = 24
_PROGRESS_BAR_LENGTH = 23
_ROUTING_PENALTY = {0: 1.5, 1: 1}