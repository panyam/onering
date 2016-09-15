VERSION = (0, 0, 8)

def get_version(version = None):
    version = version or VERSION
    return ".".join(map(str, list(version)))

__version__ = get_version(VERSION)

###### __all__ = [ "backends", "console", "core", "dsl", "readers", "templates", "context", "errors", "resolver", "utils", "version" ]
