import contextlib
from importlib.metadata import PackageNotFoundError, version

from . import config
from . import functions
from fixbikenet.fixbikenet import fixbikenet

__author__ = "MS, AV, MK"
__author_email__ = "email@domain.com"

with contextlib.suppress(PackageNotFoundError):
    __version__ = version("fixbikenet")