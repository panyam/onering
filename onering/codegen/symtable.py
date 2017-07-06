
import ipdb
from typelib import core as tlcore
import itertools

class Register(tlcore.Expr):
    """
    A location where a value of a field or constant is stored.
    The advantage of using abstract registers instead of variable "names" is that the names
    can be generated on demand when required instead of upfront - this will help with different
    kinds of code generation strategies instead of required that a registered is a given a name
    eagerly.
    """
    def __init__(self, symtable, name, type_expr = None, is_local = True):
        self.is_local = is_local
        self.symtable = symtable
        self.name = name
        self.is_named = name is not None and type(name) in (str, unicode)
        self.type_expr = type_expr 
        self.type_unknown = type_expr is None
        self._label = None
        if self.is_named:
            self._label = self.name

    def _evaltype(self, resolver_stack):
        return self.type_expr

    def _resolve(self, resolver_stack):
        return self

    @property
    def label(self):
        if not self._label:
            currindex = self.symtable.counter.next()
            currname = "var_%d" % currindex
            while currname in self.symtable._register_for_path:
                currindex = self.symtable.counter.next()
                currname = "var_%d" % currindex
            self._label = currname
        return self._label

    def __repr__(self):
        return "<Reg: 0x%x, Name: %s, Label: %s>" % (id(self), self.name, self._label)

    def __str__(self):
        return self.label

class SymbolTable(tlcore.Expr):
    def __init__(self, parent = None, counter = None):
        self.counter = counter or itertools.count()
        self._parent_table = parent
        self._curr_symtable = self
        self._registers = []
        self._register_for_path = {}

    def _evaltype(self, resolver_stack):
        return None

    def _resolve(self, resolver_stack):
        return self

    @property
    def declarations(self):
        return [ (register.label, register.type_expr) for register in self._registers if register.is_local ]

    def get_register_for_path(self, path, type_expr = None):
        """
        Given a variable or a field path, returns the register associated with that value.
        """
        if type_expr:
            if path not in self._register_for_path:
                self._register_for_path[path] = self.next_register(type_expr)
        return self._register_for_path[path]

    def next_register(self, type_expr):
        """
        Given a type_expr, returns the next register name for that type.
        """
        if type(type_expr) is not tlcore.Type:
            ipdb.set_trace()
            assert False
        return self.register_var(None, type_expr, True)

    def register_var(self, varname, type_expr, is_local):
        assert varname is None or type(varname) in (str, unicode)
        if varname is not None and varname in self._register_for_path:
            assert False, "Register with identifier '%s' already exists" % str(varname)
        register = Register(self, varname, type_expr = type_expr, is_local = is_local)
        self._registers.append(register)
        if varname is not None:
            # Named so register path to
            self._register_for_path[varname] = register
        return register 

