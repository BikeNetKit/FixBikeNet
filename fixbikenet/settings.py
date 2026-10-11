"""Global settings for `fixbikenet` that can be configured by the user.

export_file_format : {'gpkg', 'geojson'}, default 'gpkg'
    File format for the data export, relevant if `export_data` is set to True. 
    If exporting as geojson, generates extra files for seed points, city 
    boundary, and existing bicycle network (if relevant). If exporting as gkpg, these are added all in one file as extra layers.
export_path : dict(str)
    Paths to results folder to save data.
import_data_impact : float, default 10000
    Impact of imported trip or point data on results. Must be non-negative.
import_point_data_snap_distance : int, default 100
    Maximum distance between point data and network links for snapping, in 
    meters.
import_path : str
    Path to import files (as defined in `fixbikenet`'s import_files parameter).
random_seed : int, default 43
    Random number generator seed for reproducibility
silent : bool, default False
    If set to True, suppresses all user feedback. Useful for batch exports.
"""

export_file_format = 'gpkg'
export_path = "./results/"
import_data_impact = 10000
import_point_data_snap_distance = 100
import_path = "./"

random_seed = 43 # off-by-one error
silent = False