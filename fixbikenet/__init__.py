"""
FixBikeNet is a Python package to identifiy the most important gaps to fill in
a city’s bicycle network.

Full documentation at: https://docs.bikenetkit.org/FixBikeNet/

If you use FixBikeNet, please cite: https://doi.org/10.1111/gean.12324
"""

import contextlib
from importlib.metadata import PackageNotFoundError, version

from fixbikenet.fixbikenet import fixbikenet
from . import constants
from . import osm
from . import settings
from . import utils

__author__ = "FixBikeNet contributors"
__author_email__ = "michael@szell.net"

with contextlib.suppress(PackageNotFoundError):
    __version__ = version("fixbikenet")