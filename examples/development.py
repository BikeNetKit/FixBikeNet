"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

fbn.settings.import_path = '../dataexport/cities/cityexport/'
fbn.constants._BETWEENNESS_RANDOM_NODES = 300

gaps = fbn.fixbikenet(
    city_query="Frederiksberg Municipality",
    export_file_format="geojson",
    maxgap = 800,
    import_files = {
        'street_network': 'streetbike_networks/frederiksberg_dk.gpkg',
    },
)

# data is saved in directory ./results