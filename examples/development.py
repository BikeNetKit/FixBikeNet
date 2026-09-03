"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

fbn.settings.import_path = '../dataexport/cities/cityexport/growable_networks/'

gaps = fbn.fixbikenet(
    city_query="Copenhagen",
    export_file_format="geojson",
    maxgap = 1000,
    import_files = {'street_network': 'copenhagen_dk.gpkg'},
)

# data is saved in directory ./results