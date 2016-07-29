
VERSION = (0, 0, 4)

def get_version(version = None):
    version = version or VERSION
    return ".".join(map(str, list(version)))

__version__ = get_version(VERSION)

from core import *
