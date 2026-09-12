"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

fbn.settings.import_path = '../dataexport/cities/cityexport/'
fbn.constants._BETWEENNESS_RANDOM_NODES = 100
fbn.settings.export_file_format = 'geojson'

city = "paris_fr"

gaps = fbn.fixbikenet(
    city_query = city,
    import_files = {
        'city_boundary': 'boundaries/'+city+'.geojson',
        'street_network': 'streetbike_networks/'+city+'.gpkg',
    },
)

# data is saved in directory ./results