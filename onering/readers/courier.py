
from __future__ import absolute_import
import os
import ipdb
import json

from typelib import core as tlcore
from typelib import utils
from typelib import errors
from courier import parser

class CourierSchemaLoader(object):
    """
    Takes care of loading courier schemas.   Courier schemas are compilation units that may contain one or more
    records in them.   
    Courier schemas require that the folder hierarchy of the schemas (files) on disk reflect the 
    namespace.
    """
    def __init__(self, type_registry):
        self.type_registry = type_registry

    def load(self, fqn_or_path, root_dir = "."):
        """
        Loads a type given its fqn or all types at a particular path.
        """
        if os.sep in fqn_or_path:
            root_dir = os.path.abspath(root_dir)
            if not fqn_or_path.startswith("/"):
                fqn_or_path = os.path.abspath(os.path.join(root_dir, fqn_or_path))
            return self.load_from_path(fqn_or_path)
        else:
            assert False, "FQN resolution not yet done as directory structure may not reflect namespace"
            return self.load_by_name(fqn_or_path, return_cached = True)

    def load_from_path(self, file_path):
        """
        Reads one or more schemas from the given the absolute path and registers it into the schema registry.

        Reads the given file path and all records defined in it and inserts it into the type registry passed
        in the constructor.
        As far as this method is concerned only the entries found in the type registry should be used 
        (unless it can load others it can find).
        """
        print("Reading from: %s" % file_path)

        p = parser.Parser(open(file_path), self.type_registry)
        p.parse()

