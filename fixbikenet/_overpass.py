"""Overpass settings for `fixbikenet`. Do not change."""

_op_ref = "FixBikeNet Python package (https://github.com/BikeNetKit/FixBikeNet)"

import osmnx.settings as oxs
oxs.http_user_agent = _op_ref
oxs.http_referer = _op_ref