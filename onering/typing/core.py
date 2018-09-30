
class Module(object):
    def __init__(self, name, parent = None):
        self._name = name
        self.parent = parent
        # SubModules of this module
        self.modules = {}
        # Entries in this module (that are not sub modules)
        self.entries = {}

    @property
    def name(self):
        return self._name

    def ensure_module(self, submodule):
        parts = submodule.split(".")
        curr = self
        for p in parts:
            if p not in curr.modules:
                newmodule = Module(p, curr)
                curr.modules[p] = newmodule
                curr = newmodule
        return curr

    def add_entry(self, name, value):
        assert name not in self.entries
        self.entries[name] = value

class Type(object):
    def __init__(self, name = None, args = None):
        self._name = name
        self.args = args or []
        self.validator = None

    @property
    def name(self):
        return self._name

    def __repr__(self):
        out = "<%s(0x%x)" % (self.__class__.__name__, id(self))
        if self.name:
            out += ": " + self.name
        if self.args:
            out += " [%s]" % ", ".join(self.args)
        out += ">"
        return out

    def set_validator(self, validator):
        self.validator = validator
        return self

    def __getitem__(self, type_vals):
        if type(type_vals) is tuple:
            type_vals = list(iter(type_vals))
        elif type(type_vals) is not list:
            type_vals = [type_vals]
        param_values = dict(zip(self.args, type_vals))
        return self.apply(**param_values)

    def apply(self, **param_values):
        return TypeApp(self, **param_values)

class TypeAlias(Type):
    """ A type variable.  """
    def __init__(self, target_type, name = None):
        assert name is not None and name.strip(), "Type aliases MUST have names"
        Type.__init__(self, name)
        self.target_type = target_type

class TypeVar(Type):
    """ A type variable.  """
    def __init__(self, name = None, args = None):
        assert name is not None and name.strip(), "Type vars MUST have names"
        Type.__init__(self, name, args)

class TypeApp(Type):
    """ Type applications allow generics to be concretized. """
    def __init__(self, target_type, **param_values):
        Type.__init__(self, target_type.name)

        # Ensure String values are auto converted to TypeVars
        self.param_values = {k: TypeVar(v) if type(v) is str else v for k,v in param_values.items()}
        self.root_type = target_type
        if isinstance(target_type, TypeApp):
            self.root_type = target_type.root_type
            self.param_values.update(target_type.param_values)
            # now only update *new* values that have not been duplicated
            for k,v in param_values.iteritems():
                if k in target_type.args:
                    self.param_values[k] = v

class NativeType(Type):
    """ A native type whose details are not known but cannot be 
    inspected further - like a leaf type. 

    eg Array<T>, Map<K,V> etc
    """
    def __init__(self, name = None, args = None):
        Type.__init__(self, name, args)
        self.mapper_functor = None

class DataType(Type):
    """ Non leaf types.  These include:

        Product types (Records, Tuples, Named tuples etc) and 
        Sum types (Eg Unions, Enums (Tagged Unions), Algebraic Data Types.
    """
    def __init__(self, name = None, args = None):
        Type.__init__(self, name, args)
        self.child_types = []
        self.child_names = []

    def add(self, child_type, child_name = None):
        if child_name and self.name_exists(child_name):
            assert False, "Type '%s' already taken" % child_name
        self._add_type(child_type, child_name)
        return self

    def add_multi(self, *child_types_and_names):
        for t, n in zip(*[iter(child_types_and_names)]*2):
            self.add(t,n)
        return self

    def name_exists(self, name):
        return name in self.child_names

    def _add_type(self, child_type, child_name):
        self.child_types.append(child_type)
        self.child_names.append(child_name)

class TypeClass(Type):
    def __init__(self, name = None, args = None):
        Type.__init__(self, name, args)
        self.methods = {}

    def add_traits(self, *names_and_func_types):
        for n, ft in zip(*[iter(names_and_func_types)]*2):
            assert isinstance(ft, FunctionType)
            self.methods[n] = ft
        return self

class FunctionType(Type):
    def __init__(self, name = None, args = None):
        Type.__init__(self, name, args)
        self._input_types = []
        self._return_type = None

    @property
    def return_type(self):
        return self._return_type

    @property
    def input_types(self):
        return self._input_types

    def returns(self, return_type):
        self._return_type = return_type
        return self

    def with_inputs(self, *input_types):
        for it in input_types:
            if type(it) is str:
                it = TypeVar(it)
            self._input_types.append(it)
        return self

class RecordType(DataType): pass

class TupleType(DataType): pass

class UnionType(DataType): pass
