
from __future__ import absolute_import
import ipdb
from enum import Enum
from onering import errors
from onering.utils import ResolutionStatus
from onering.core.utils import FieldPath
from onering.core import exprs as orexprs
from onering.core.projections import SimpleFieldProjection
from typelib.annotations import Annotatable

class Interface(Annotatable):
    """
    Interfaces are the definition of a service/api and contain a list of method declarations
    or child interfaces.
    """
    def __init__(self, fqn, parent = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self._parent = parent
        self._functions = {}

    @property
    def parent(self):
        return self._parent

    def __repr__(self):
        return "<Interface - ID: 0x%x, Name: %s>" % (id(self), self.fqn)
