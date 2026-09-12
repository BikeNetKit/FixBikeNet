import contextlib
from importlib.metadata import PackageNotFoundError, version

from fixbikenet.fixbikenet import fixbikenet

from . import config, functions

__author__ = "MS, AV, MK"
__author_email__ = "email@domain.com"

with contextlib.suppress(PackageNotFoundError):
    __version__ = version("fixbikenet")