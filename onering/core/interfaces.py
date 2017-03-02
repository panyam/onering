
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
        self.fqn = fqn
        self._parent = parent
        self._functions = {}
        self._children = {}

    @property
    def parent(self):
        return self._parent

    def __repr__(self):
        return "<Interface - ID: 0x%x, Name: %s>" % (id(self), self.fqn)

    def add_interface(self, interface):
        """Adds a child/nested interface to this interface."""
        ipdb.set_trace()
        if interface.fqn in self._children:
            raise errors.OneringException("Duplicate interface found: %s" % interface.fqn)
        self._children[interface.fqn] = interface

    def add_function(self, func_type):
        """Adds a function to this interface."""
        if func_type.name in self._functions:
            raise errors.OneringException("Duplicate function found: %s" % func_type.name)
        self._functions[func_type.name] = func_type
