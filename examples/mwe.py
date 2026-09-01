"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

gaps = fbn.fixbikenet(
    city_query="Frederiksberg municipality",
    export_file_format="geojson",
)

# data is saved in directory ./results