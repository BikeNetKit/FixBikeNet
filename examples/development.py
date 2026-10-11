"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

# fbn.settings.import_path = '/Users/mszell/Tresorit/bikenetkitshare/'
fbn.constants._BETWEENNESS_RANDOM_NODES = 100
fbn.settings.export_file_format = 'gpkg'
fbn.constants._ROUTING_PENALTY = {0: 1.5, 1: 1}
fbn.settings.import_point_data_snap_distance = 100

fbn.settings.import_path = '/Users/mszell/Tresorit/bikenetkitshare/'
city_id = "frederiksberg_dk" #"copenhagen_dk"

fbn.fixbikenet(
            city_query="Copenhagen",
            radius = 1000,
            maxgap = 500,
            numgaps = 20,
            import_files={
                'city_boundary': 'boundaries/'+city_id+'.geojson',
                'street_network': 'streetbike_networks/'+city_id+'.gpkg',
                'point_data': 'special/copenhagen_citizen_input.geojson',
            },
        )
