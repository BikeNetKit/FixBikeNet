"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

fbn.settings.import_path = '../dataexport/cities/cityexport/'
fbn.constants._BETWEENNESS_RANDOM_NODES = 100

gaps = fbn.fixbikenet(
    city_query="Frederiksberg",
    radius = 1000,
    mingap = 0,
    maxgap = 500,
    numgaps = 20,
    import_files = {
        'city_boundary': 'boundaries/frederiksberg_dk.geojson',
        'street_network': 'streetbike_networks/frederiksberg_dk.gpkg',
    },
)

# data is saved in directory ./results