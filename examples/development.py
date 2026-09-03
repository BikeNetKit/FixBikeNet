"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

fbn.settings.import_path = '../dataexport/cities/cityexport/'
fbn.constants._BETWEENNESS_RANDOM_NODES = 100

gaps = fbn.fixbikenet(
    city_query="Frederiksberg",
    export_file_format="geojson",
    maxgap = 1000,
    import_files = {
        'street_network': 'growable_networks/frederiksberg_dk.gpkg',
    },
)

# data is saved in directory ./results