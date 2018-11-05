
from ipdb import set_trace
import typing
from onering.common import errors, annotations

def ensure_type(type_or_str):
    if isinstance(type_or_str, str):
        type_or_str = TypeVar(type_or_str)
    return type_or_str 

class Type(object):
    def __init__(self, args = None):
        self.args = args or []
        self.validator = None
        self._annotations = Annotations()

    def __repr__(self):
        out = "<%s(0x%x)" % (self.__class__.__name__, id(self))
        if self.args:
            out += " [%s]" % ", ".join(self.args)
        out += ">"
        return out

    @property
    def annotations(self): return self._annotations

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

        # What does this bind to?
        self.bound_type = None
        self.bound_parent = None

    @property
    def is_bound(self) -> bool:
        return self.bound_type is not None or self.bound_parent is not None

    @property
    def final_type(self) -> Type:
        """ Returns the ultimate type this variable is bound to since a TypeVar 
        can bind to another TypeVar and so on.
        TODO - Can there be cycles here?
        """
        t = self
        while t and isinstance(t, TypeVar):
            t = t.bound_type
        return t

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
        target_type = ensure_type(target_type)
        self.root_type = target_type
        if isinstance(target_type, TypeApp):
            self.root_type = target_type.root_type
            self.apply(**target_type.param_values)
        self.apply(*type_args, **type_kwargs)

    def apply(self, *values : typing.List[Type], **kvpairs : typing.Map[str, Type]) -> "TypeApp":
        for value in values:
            value = ensure_type(value)
            root_type = self.root_type
            if isinstance(root_type, TypeVar) and not root_type.final_type:
                self.unused_values.append(value)
            else:
                if isinstance(root_type, TypeVar):
                    root_type = root_type.final_type
                # Get the next unbound type argument in the root type and apply this value to it
                next_arg = next(filter(lambda x: x not in self.param_values, root_type.args), None)
                if not next_arg:
                    raise errors.ORException("Trying to bind type (%s), but no more unbound arguments left in TypeApp" % repr(value))
                self.param_values[next_arg] = value

        for key, value in kvpairs.items():
            value = ensure_type(value)
            # Ensure this value has not already been applied.
            if isinstance(self.root_type, TypeVar):
                raise errors.ORException("Values cannot be bound by key for TypeVars")
            if key in self.param_values:
                raise errors.ORException("Type argument '%s' is already bound to a value" % key)
            self.param_values[key] = value
        return self

class NativeType(Type):
    """ A native type whose details are not known but cannot be 
    inspected further - like a leaf type. 

    eg Array<T>, Map<K,V> etc
    """
    def __init__(self, args = None):
        Type.__init__(self, args)
        self.mapper_functor = None

class TypeClass(object):
    def __init__(self, args = None):
        self.args = args or []
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
            it = ensure_type(it)
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
        child_type = ensure_type(child_type)
        self.child_types.append(child_type)
        self.child_names.append(child_name)

class RecordType(DataType):
    name_required = True
    sum_type = False

class TupleType(DataType):
    sum_type = False

class UnionType(DataType): pass

class RefinedType(Type):
    """ Refined types are types decorated by logical predicates or constraints.
    TODO - Do we need a special wrapper type here or can predicates not apply
    to *all* types?
    """
    def __init__(self, target_type, args = None):
        Type.__init__(self, args)
        self.target_type = target_type

    """
        self.predicates = []

    def add(self, predicate):
        self.predicates.append(predicate)
        return self

    def add_multi(self, *predicates):
        map(self.add, predicates)
        return self
    """
