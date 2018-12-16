
from ipdb import set_trace
import typing
from onering.common import errors, annotations

def ensure_type(type_or_str):
    if isinstance(type_or_str, str):
        type_or_str = TypeVar(type_or_str)
    return type_or_str 

def ensure_expr(expr_or_str):
    if isinstance(expr_or_str, str):
        expr_or_str = Var(expr_or_str)
    return expr_or_str 

class Expr(annotations.Annotatable):
    def __init__(self):
        annotations.Annotatable.__init__(self)

    @property
    def rank(self): return 0

    @property
    def copy(self):
        val = self._copy()
        return val

    def __getitem__(self, expr_vals):
        if type(expr_vals) is tuple:
            expr_vals = list(iter(expr_vals))
        elif type(expr_vals) is not list:
            expr_vals = [expr_vals]
        return App(self, *expr_vals)

class NativeExpr(Expr):
    """ Native expressions have no definition and are just a way to jump out to a foreign expression via the runtime. """
    pass

class Type(object):
    def __init__(self):
        self.validator = None

    def set_validator(self, validator):
        self.validator = validator
        return self

    @property
    def rank(self): return 1

class Var(Expr):
    def __init__(self, name : str):
        Expr.__init__(self)
        assert name is not None and name.strip(), "Type vars MUST have names"
        self.name = name
        # What does this bind to?
        self.bound_value = None
        self.bound_parent = None

    def _copy(self):
        return self.__class__(self.name)

    @property
    def is_bound(self) -> bool:
        return self.bound_value is not None or self.bound_parent is not None

    @property
    def final_value(self) -> Type:
        """ Returns the ultimate value this variable is bound to since a Var 
        can bind to another Var and so on.
        TODO - Can there be cycles here?
        """
        t = self
        while t and issubclass(t.__class__, Var):
            t = t.bound_value
        return t

class Fun(Expr):
    def __init__(self, args : typing.List[str], result : Expr):
        Expr.__init__(self)
        self.args = args
        self.result = result

    def _copy(self):
        return self.__class__(self.name, self.args, self.result)

class App(Expr):
    def __init__(self, target, *args : typing.List[Expr], **kwargs : typing.Dict[str, Expr]):
        Expr.__init__(self)
        target = ensure_expr(target)
        self.target = target
        self.args = []
        self.kwargs = {}
        self.apply(*args, **kwargs)

    def apply(self, *args : typing.List[Expr], **kwargs : typing.Dict[str, Expr]):
        self.args.extend(args)
        self.kwargs.update(kwargs)

    def _copy(self):
        return self.__class__(self.target, *self.args, **self.kwargs)

class BoxExpr(Expr):
    """ Compound expressions allow us to construct expressions that have
    "children".  However the structure of the children themselves are not
    known so we depend on a Functor behavior to access and update these
    children.
    """
    def children(self):
        """ Expressions can contain "child" expressions that make it up. """
        return []

    def setfmap(self, func):
        """ Sets the functor mapper for this compound expression """
        return None

    def _copy(self):
        return val

class TypeFun(Type, Fun):
    def __init__(self, args : typing.List[str], result : Type):
        Type.__init__(self)
        Fun.__init__(self, args, result)

class TypeVar(Type, Var):
    def __init__(self, name : str):
        Type.__init__(self)
        Var.__init__(self, name)

class TypeApp(Type, App):
    def __init__(self, target, *expr_args, **expr_kwargs):
        Type.__init__(self)
        App.__init__(self, target, *expr_args, **expr_kwargs)

class NativeType(Type, NativeExpr):
    """ A native type whose details are not known but cannot be 
    inspected further - like a leaf type. 

    eg Array<T>, Map<K,V> etc
    """
    def __init__(self):
        Type.__init__(self)
        NativeExpr.__init__(self)

class FunctionType(Type, BoxExpr):
    def __init__(self):
        Type.__init__(self)
        BoxExpr.__init__(self)
        self._input_names = []
        self._input_types = []
        self._return_type = None

    def _copy(self):
        out = FunctionType()
        out._input_names = self._input_names[:]
        out._input_types = self._input_types[:]
        out._return_type = self._return_type
        return out

    @property
    def return_type(self):
        return self._return_type

    @property
    def input_types(self):
        return self._input_types

    def returns(self, return_type):
        self._return_type = return_type
        return self

    def add_input(self, input_type, input_name = None):
        if type(input_type) is tuple:
            assert input_name is None
            input_type, input_name = input_type
        it, name = input_type, input_name
        it = ensure_type(it)
        self._input_types.append(it)
        self._input_names.append(name)
        return self

    def with_inputs(self, *input_types):
        map(self.add_input, input_types)
        return self

class DataType(Type, BoxExpr):
    """ All type functions/abstractions!

        Product types (Records, Tuples, Named tuples etc) and 
        Sum types (Eg Unions, Enums (Tagged Unions), Algebraic Data Types.
    """
    def __init__(self):
        Type.__init__(self)
        BoxExpr.__init__(self)
        self._child_types = []
        self._child_names = []

    @property
    def is_labelled(self): return False

    @property
    def is_sum_type(self): return True

    def _copy(self):
        out = self.__class__()
        out._child_names = self._child_names[:]
        out._child_types = self._child_types[:]
        return out

    def get(self, name):
        """ Get's a child if we are a labelled data type. """
        for n,t in zip(self._child_names, self._child_types):
            if n == name:
                return t
        return None

    def add(self, child_type, child_name = None, override = False):
        assert not (self.is_labelled and child_name is None), "Name is required and cannot be empty"
        index = self.indexof(child_name)
        if child_name and index >= 0:
            if not override:
                assert False, "Type '%s' already taken" % child_name
            self._set_type(index, child_type, child_name)
        else:
            self._add_type(child_type, child_name)
        return self

    def add_multi(self, *child_types_and_names):
        for t, n in zip(*[iter(child_types_and_names)]*2):
            self.add(t,n)
        return self

    def indexof(self, name):
        for i,n in enumerate(self._child_names):
            if n == name: return i
        return -1

    def name_exists(self, name):
        return name in self._child_names

    def _add_type(self, child_type, child_name):
        child_type = ensure_type(child_type)
        self._child_types.append(child_type)
        self._child_names.append(child_name)

    def _set_type(self, index, child_type, child_name):
        child_type = ensure_type(child_type)
        self._child_types[index] = child_type
        self._child_names[index] = child_name

    def include(self, othertype):
        return self

class RecordType(DataType):
    @property
    def is_labelled(self): return True

    @property
    def is_sum_type(self): return False

class TupleType(DataType):
    @property
    def is_sum_type(self): return False

class UnionType(DataType):
    pass

class RefinedType(Type, BoxExpr):
    """ Refined types are types decorated by logical predicates or constraints.
    TODO - Do we need a special wrapper type here or can predicates not apply
    to *all* types?
    """
    def __init__(self, target_type):
        Type.__init__(self)
        BoxExpr.__init__(self)
        self.target_type = target_type

