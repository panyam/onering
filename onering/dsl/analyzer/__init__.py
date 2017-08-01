
from __future__ import absolute_import

import ipdb
from typecube import core as tccore
from typecube import ext as tcext

class Analyzer(object):
    """ The semantic analyzer for a parsed onering expression tree.
    Does the following:

        1. Type checking of all function arguments and return types.
        2. Resolves and fills in binding sites and scoping information for all Variables and TypeRefs
        3. Any preliminary expression re-writes or transformations if necessary
    """
    def __init__(self, context, entities = None):
        """ Creates the analyzer.

        Params:
            context     -   The onering context into which all loaded entities will be found and searched for.
            entities    -   Optional dictionary of entities to limit the analyzing to.
        """
        self.context = context
        self.entities = entities or {}

    def analyze(self):
        pass
