
from __future__ import absolute_import
import ipdb
from enum import Enum
from onering import errors
from onering.utils.misc import ResolutionStatus, FQN
from onering.core.utils import FieldPath
from onering.core import exprs as orexprs
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
        self._interfaces = {}

    @property
    def interfaces(self):
        return self._interfaces

    @property
    def functions(self):
        return self._functions

    @property
    def parent(self):
        return self._parent

    def __repr__(self):
        return "<Interface - ID: 0x%x, Name: %s>" % (id(self), self.fqn)

    def add_interface(self, interface):
        """Adds a child/nested interface to this interface."""
        name = FQN(interface.fqn, None).name
        if name in self._interfaces:
            raise errors.OneringException("Duplicate interface found: %s" % name)
        self._interfaces[name] = interface

    def add_function(self, func_type):
        """Adds a function to this interface."""
        if func_type.fqn in self._functions:
            raise errors.OneringException("Duplicate function found: %s" % func_type.fqn)
        self._functions[func_type.fqn] = func_type

    def __json__(self, **kwargs):
        out = super(Interface, self).__json__(**kwargs)
        out["name"] = FQN(self.fqn, None).name
        if kwargs.get("include_docs", False) and self.docs:
            out["docs"] = self.docs
        if self._functions:
            out["funs"] = [func.json(**kwargs) for func in self._functions.itervalues()]
        if self._interfaces:
            out["interfaces"] = [interface.json(**kwargs) for interface in self._interfaces.itervalues()]
        return out
