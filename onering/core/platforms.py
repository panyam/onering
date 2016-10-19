
from __future__ import absolute_import
import ipdb
from itertools import izip
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
        self._type_bindings = []
        self._root_type_node = TypeTrieNode(None)

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
        self._type_bindings.append({"type": type_binding, "template": native_template})
        # self._root_type_node.insert_type_binding(type_binding)

    def match_typeref_binding(self, typeref):
        """
        Given a starting typeref, matches the template that should be used along with all 
        the bound parameter names (and their value typerefs) that should be passed to 
        the template string for rendering.

        TODO: Decide whether we also want to render the template too
        """
        for tbdict in self._type_bindings:
            tb = tbdict["type"]
            bound_params = tb.matches_typeref(typeref)
            if bound_params:
                return tb, tbdict["template"], bound_params
        return None, None, None

class TypeBinding(object):
    def __init__(self, name, is_param = False):
        self.name = name
        self.is_param = is_param
        self.args = []

    def __repr__(self):
        name = self.name
        if self.is_param: name = "$" + name
        return "<TB, ID: 0x%x, Name: %s, NumArgs: %d>" % (id(self), name, len(self.args))

    @property
    def argcount(self):
        return len(self.args)

    def add_argument(self, arg):
        if not self.args:
            self.args = []
        self.args.append(arg)

    def matches_typeref(self, typeref, bound_params = None):
        """
        Given a typeref returns True along with all the "bound" type parameters.
        Otherwise returns False,None.
        """
        if bound_params is None:
            bound_params = {}
        if self.is_param:
            # then we can just bind the value into typeref
            if self.name in bound_params:
                raise errors.OneringException("Binding parameter '$%s' already encountered" % self.name)
            bound_params[self.name] = typeref
            return bound_params

        fqn = typeref.fqn
        # Check based on FQN first
        if fqn:
            if fqn == self.name and len(self.args) == 0:
                # Type binding must have no children
                # because the fqn of a typeref is just an alias
                # and cannot be used as a type indicator (that's where 
                # the constructor comes in).   This can change if/when
                # type aliases could refer to a constructor instead of 
                # the type itself
                return bound_params
            return None

        # Now based on the final type
        final_type = typeref.final_type
        if final_type.constructor == self.name and final_type.argcount == self.argcount:
            # make sure each of the child args match
            # Now check the arguments to see if they match
            for type_arg, binding_arg in izip(final_type.args, self.args):
                bound_params = binding_arg.matches_typeref(type_arg.typeref, bound_params)
                if bound_params is None:
                    return None

            # All children matched so this is a match and bound_params contains
            # the typerefs bound to each of the params
            return bound_params

        return None

class TypeTrieNode(object):
    """
    A node in the type binding trie.
    """
    def __init__(self, type_name, is_param = False):
        self.type_name = type_name
        self.is_param = is_param
        self.arglist_options = []
        self.is_terminal = False

    def add_arglist_pattern(self, arglist):
        """
        A node in this trie can either be a "basic" type, ie int, byte, char etc
        In this case the type_name would be set and there wouldnt be any arguments.

        However it could also be a complex type like map[ktype, vtype] or in this case 
        each combination of args to this complex type must also be maintained, 
        eg for array[byte, String], array[int, Long], array[$1, $2], then the 
        "map" node must contain 3 options = (byte, String), (int, Long), ($1, $2) to 
        indicate which template string is to be picked.

        For this each entry in the arglist must be a TypeTrieNode
        """
        # arglist_option can either be a list of strings
        if type(arglist) is not list:
            arglist = [arglist]
        # Ensure all elements are either strings or TypeTrieNodes
        assert all(map(lambda x: type(x) is TypeTrieNode, arglist)), "Arguments must be strings or TypeTrieNodes"
        self.arglist_options.append(arglist)

    def insert_type_binding(self, type_binding):
        targetnode = None
        # First check for the type name
        for arglist in self.arglist_options:
            if len(arglist) == 1 and arglist[0].fqn == type_binding.fqn:
                targetnode = arglist[0]
                break
        else:
            targetnode = TypeTrieNode(type_binding.fqn)

        type_binding_arg_names = [a.fqn for a in type_binding.args]

        if len(targetnode.arglist_options) == 0 and len(type_binding.args) == 0:
            # we have reache the end so mark targetnode as terminal too
            targetnode.is_terminal = True

        for arglist in targetnode.arglist_options:
            # See if constructors match
            constructors = [a.fqn for a in arglist]
            if constructors == type_binding_arg_names:
                for n1, t1 in izip(arglist, type_binding.args):
                    n1.insert_type_binding(t1)
                
        ipdb.set_trace()
        # Now check args match for target nodes
        curr_node = targetnode
