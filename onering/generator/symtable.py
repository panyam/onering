
import ipdb
import itertools

class Register(object):
    """
    A location where a value of a field or constant is stored.
    The advantage of using abstract registers instead of variable "names" is that the names
    can be generated on demand when required instead of upfront - this will help with different
    kinds of code generation strategies instead of required that a registered is a given a name
    eagerly.
    """
    def __init__(self, symtable, name, typeref = None, is_local = True):
        self.is_local = is_local
        self.symtable = symtable
        self.name = name
        self.is_named = name is not None and type(name) in (str, unicode)
        self.typeref = typeref
        self._label = None
        if self.is_named:
            self._label = self.name

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
        return "<ID: 0x%x, Name: %s, Label: %s>" % (id(self), self.name, self._label)

    def __str__(self):
        return self.label

class SymbolTable(object):
    def __init__(self, parent = None, counter = None):
        self.counter = counter or itertools.count()
        self._parent_table = parent
        self._curr_symtable = self
        self._registers = []
        self._register_for_path = {}

    @property
    def declarations(self):
        return [ (register.label, register.typeref) for register in self._registers if register.is_local ]

    def get_register_for_path(self, path, typeref = None):
        """
        Given a variable or a field path, returns the register associated with that value.
        """
        if typeref:
            if path not in self._register_for_path:
                self._register_for_path[path] = self.next_register(typeref)
        return self._register_for_path[path]

    def next_register(self, typeref):
        """
        Given a typeref, returns the next register name for that type.
        """
        return self.register_var(None, typeref, True)

    def register_var(self, varname, typeref, is_local):
        assert varname is None or type(varname) in (str, unicode)
        if varname is not None and varname in self._register_for_path:
            assert False, "Register with identifier '%s' already exists" % str(varname)
        register = Register(self, varname, typeref = typeref, is_local = is_local)
        self._registers.append(register)
        if varname is not None:
            # Named so register path to
            self._register_for_path[varname] = register
        return register 

