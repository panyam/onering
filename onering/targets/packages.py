from __future__ import absolute_import
from ipdb import set_trace
import os
import glob, fnmatch
import importlib
from onering.utils import dirutils, misc

class Package(object):
    """
    Describes a top-level logical onering package.  This is platform independant and 
    only describes the artifact in a generic way.
    """

    class Entity(object):
        """ An entity exported by a package. """
        fqn = None
        is_public = True

    """ Packages that this package depends on logically. """
    dependancies = {}

    def __init__(self, name, version = "0", description = ""):
        self.name = name
        self.version = version
        self.description = description

        # The entities bundled in this package (both private and public).
        # The idea here is that every entity is usually bundled in a package
        # and hosted by it though when loaded, the entities in a package
        # co-exist with the entites of other packages loaded within a common
        # runtime/world.
        self.exported_entities = {}
