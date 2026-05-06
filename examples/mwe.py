"""Minimum working example of fixbikenet."""

import fixbikenet as fbn

gaps = fbn.fixbikenet(
    city_name="Frederiksberg municipality",
)

# data is saved in current working directory, as gaps.gpkg