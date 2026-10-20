"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

# fbn.settings.import_path = '/Users/mszell/Tresorit/bikenetkitshare/'
# fbn.constants._BETWEENNESS_RANDOM_NODES = 100
fbn.settings.export_file_format = 'gpkg'
# fbn.settings.import_point_data_snap_distance = 100

# fbn.settings.import_data_impact = 10000

# fbn.settings.import_path = '/Users/mszell/Tresorit/bikenetkitshare/'
# city_id = "copenhagen_dk" #"copenhagen_dk"frederiksberg_dk

# fbn.fixbikenet(
#             city_query="Copenhagen", # "Frederiksberg"Copenhagen
#             import_files={
#                 'city_boundary': 'boundaries/'+city_id+'.geojson',
#                 'street_network': 'streetbike_networks/'+city_id+'.gpkg',
#                 'point_data': 'special/copenhagen_citizen_input.geojson',
#             },
#         )

fbn.settings.radius = 1000

fbn.fixbikenet(
    city_query="Frederiksberg Municipality",
    min_gap_length = 0,
    max_gap_length = 100,
    num_gaps = 20,
    import_files={
        'city_boundary': "./tests/test_data/frederiksberg_boundary.geojson",
        # 'street_network': "./tests/test_data/frederiksberg_streetbike_network.gpkg",
    },
)