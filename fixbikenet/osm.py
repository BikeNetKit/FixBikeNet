"""Global constants for `fixbikenet` related to OpenStreetMap (OSM). These are 
meant for advanced users only who have a good understanding of OSM tags.

PBI_DICT : dict
    Dictionary for protected bicycle infrastructure (pbi), for single criteria.
PBI_DICT_SUB : dict
    Dictionary for protected bicycle infrastructure (pbi), with one 
    sub-criterion. For example, highway~path AND bicycle~designated. Always 
    adds a second criterion access!~private.
"""

# Populate ox.settings.useful_tags_way to make application of custom filter possible
import osmnx as ox
for custom_tag in ["highway", "cycleway", "bicycle", "cycleway:right", "cycleway:left", "cycleway:both", "cyclestreet", "access", "area", "service", "motor_vehicle", "motorcar"]: # This list should contain all tags used in any custom filters
    if custom_tag not in ox.settings.useful_tags_way:
        ox.settings.useful_tags_way.extend(custom_tag)

PBI_DICT = {
    'highway': ['cycleway','living_street'],
    'cyclestreet': ['yes'],
    'bicycle_road': ['yes'],
    'cycleway': ['track'],
    'cycleway:right': ['track','opposite_track'],
    'cycleway:left': ['track','opposite_track'],
    'cycleway:both': ['track','opposite_track'],
}

PBI_DICT_SUB = {
    'highway': [
        ['path','pedestrian','footway'],
        {'bicycle': ['designated','yes','permissive']},
    ]
}
