"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

gaps = fbn.fixbikenet(
    city_name="Frederiksberg municipality",
    export_file_format="geojson",
)

# data is saved in current working directory, as gaps.gpkg