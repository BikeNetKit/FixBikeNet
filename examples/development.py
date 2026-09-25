"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

# fbn.settings.import_path = '/Users/mszell/Tresorit/bikenetkitshare/'
fbn.constants._BETWEENNESS_RANDOM_NODES = 100
fbn.settings.export_file_format = 'gpkg'
fbn.constants._ROUTING_PENALTY = {0: 1.5, 1: 1}



fbn.fixbikenet(
            city_query="Frederiksberg",
            radius = 1000,
            maxgap = 500,
            numgaps = 20,
            import_files={
                'city_boundary': "./tests/test_data/frederiksberg_boundary.geojson",
                'street_network': "./tests/test_data/frederiksberg_streetbike_network.gpkg",
            },
        )

# city = "frederiksberg_dk"
# gaps = fbn.fixbikenet(
#     city_query = city,
#     import_files = {
#         'city_boundary': 'boundaries/'+city+'.geojson',
#         'street_network': 'streetbike_networks/'+city+'.gpkg',
#     },
# )

# data is saved in directory ./results