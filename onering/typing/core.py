
from ipdb import set_trace
from onering.common import errors

class Context(object):
    """ A type context/environment that provides bindings between names and types. """
    def __init__(self):
        self.root = {}
        self.typefqns = {}

    def add(self, fqn, thetype):
        """ Adds a type given its fqn """
        currfqn = self.fqn_for(thetype)
        if currfqn:
            # The type has already been added, it needs to be added by a reference instead
            set_trace()
            assert False
        self.typefqns[thetype] = fqn
        parts = fqn.split(".")
        module, last = parts[:-1], parts[-1]
        parent = self.ensure(".".join(module))
        parent[last] = thetype

    def fqn_for(self, thetype):
        """ Given a type, returns it FQN. """
        return self.typefqns.get(thetype, None)

    def ensure(self, fqn):
        parts = fqn.split(".")
        curr = self.root
        for p in parts:
            if p not in curr:
                curr[p] = {}
            curr = curr[p]
        return curr

class Type(object):
    def __init__(self, args = None):
        self.args = args or []
        self.validator = None

    def __repr__(self):
        out = "<%s(0x%x)" % (self.__class__.__name__, id(self))
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
        return TypeApp(self, *type_vals)

class TypeVar(Type):
    """ A type variable.  """
    def __init__(self, name):
        assert name is not None and name.strip(), "Type vars MUST have names"
        Type.__init__(self)
        self.name = name

class TypeApp(Type):
    """ Type applications allow generics to be concretized. 

        TypeApps follow certain rules.  Say if we have a type:
        
            Map = record Map[A,B,C,D,E,F] { .... }

        Following are some possibilities:
            Map[Int, String]            -> Valid - Binds A and B
            Map[A = Int, C = String]    -> Valid - Binds A and C
            Map[Int, String][A = Float] -> Invalid - Should result in error since A is already bound
            Map[Int, String][D = Int]   -> Valid - Fine, same as Map[A = Int, B = String, D = Int]
            Map[Int, String, Int, Float, Double, Boolean]   -> Valid - Fine as all params bound
            Map[Int, String, Int, Float, Double, Boolean, String]   -> Invalid - Since we have more params than required
            T[Int]   -> Valid - Though is actually same as above, but since T is a type var, 
                        Int "could" bind if the resolved value of T can take a parameter as per above rule!
            T[A = Int]  -> Invalid since T could be a type that has a parameter but not called A.
    """
    def __init__(self, target_type, *type_args, **type_kwargs):
        Type.__init__(self)

        self.param_values = {}
        self.unused_values = []
        self.root_type = target_type
        if isinstance(target_type, TypeApp):
            self.root_type = target_type.root_type
            for k,v in target_type.param_values.items():
                self.apply_to_key(k, v)
        for v in type_args: self.apply(v)
        for k,v in type_kwargs: self.apply_to_key(k, v)

    def apply_to_key(self, key, value):
        """ Applies a value to a key. """
        if type(value) is str:
            value = TypeVar(value)
        # Ensure this value has not already been applied.
        if isinstance(self.root_type, TypeVar):
            raise errors.ORException("Values cannot be bound by key for TypeVars")
        if key in self.param_values:
            raise errors.ORException("Type argument '%s' is already bound to a value" % key)
        self.param_values[key] = value
        return self

    def apply(self, value):
        if type(value) is str:
            value = TypeVar(value)

        if isinstance(self.root_type, TypeVar):
            self.unused_values.append(value)
        else:
            # Get the next unbound type argument in the root type and apply this value to it
            next_arg = next(filter(lambda x: x not in self.param_values, self.root_type.args), None)
            if not next_arg:
                raise errors.ORException("Trying to bind type (%s), but no more unbound arguments left in TypeApp" % repr(value))
            self.param_values[next_arg] = value
        return self

class NativeType(Type):
    """ A native type whose details are not known but cannot be 
    inspected further - like a leaf type. 

    eg Array<T>, Map<K,V> etc
    """
    def __init__(self, args = None):
        Type.__init__(self, args)
        self.mapper_functor = None

class TypeClass(Type):
    def __init__(self, args = None):
        Type.__init__(self, args)
        self.methods = {}

    def add_traits(self, *names_and_func_types):
        for n, ft in zip(*[iter(names_and_func_types)]*2):
            assert isinstance(ft, FunctionType)
            self.methods[n] = ft
        return self

class FunctionType(Type):
    def __init__(self, args = None):
        Type.__init__(self, args)
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

class DataType(Type):
    """ Non leaf types.  These include:

        Product types (Records, Tuples, Named tuples etc) and 
        Sum types (Eg Unions, Enums (Tagged Unions), Algebraic Data Types.
    """

    name_required = False
    sum_type = True

    def __init__(self, args = None):
        Type.__init__(self, args)
        self.child_types = []
        self.child_names = []

    def add(self, child_type, child_name = None):
        assert not (self.name_required and child_name is None), "Name is required and cannot be empty"
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
        if type(child_type) is str:
            child_type = TypeVar(child_type)
        self.child_types.append(child_type)
        self.child_names.append(child_name)

class RecordType(DataType):
    name_required = True
    sum_type = False

class TupleType(DataType):
    sum_type = False

class UnionType(DataType): pass
