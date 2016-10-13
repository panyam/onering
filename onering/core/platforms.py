
from typelib.annotations import Annotatable
from onering.core import functions

class Platform(Annotatable):
    """
    Contains all platform specific bindings from onering types to native types.
    """
    def __init__(self, name, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.name = name
        self._functions = {}
        self._types = []

    def add_function(self, function_or_fqn, native_fqn, annotations = None, docs = ""):
        function_fqn = function_or_fqn
        if type(function_or_fqn) is functions.Function:
            function_fqn = function_or_fqn.fqn

        if function_fqn in self._functions:
            raise errors.OneringException("Duplicate function found: %s" % function_fqn)
        self._functions[function_fqn] = {"fqn": native_fqn,
                                         "annotations": annotations or [],
                                         "docs": docs}

    def get_function_binding(self, function_or_fqn):
        """
        Returns the native platform specific binding of a function (or its fqn)
        """
        function_fqn = function_or_fqn
        if type(function_or_fqn) is functions.Function:
            function_fqn = function_or_fqn.fqn

        # TODO - return None on missing?
        self._functions[function_fqn]["fqn"]

    def add_type_binding(self, type_binding, native_template, annotations = None, docs = ""):
        # TODO - Order things around and check for duplicates
        self._types.append({"type": type_binding, "template": native_template})

class TypeBinding(object):
    def __init__(self, fqn):
        self.fqn = fqn
        self.args = None

    def matches_typeref(self, typeref, type_registry):
        """
        Given a typeref returns True along with all the "bound" type parameters.
        Otherwise returns False,None.
        """
        pass
