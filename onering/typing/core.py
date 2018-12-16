
from ipdb import set_trace
import typing
from taggedunion import *
from onering.common import errors, annotations

def ensure_type(type_or_str):
    if isinstance(type_or_str, str):
        type_or_str = Type.as_var(type_or_str)
    return type_or_str 

def ensure_expr(expr_or_str):
    if isinstance(expr_or_str, str):
        expr_or_str = Var(expr_or_str)
    return expr_or_str 

class NativeType(object):
    def __init__(self):
        pass

class TypeFun(object):
    def __init__(self, args : typing.List[str], body : "Type"):
        self.args = args
        self.body = ensure_type(body)

class TypeApp(object):
    def __init__(self, operator, operands):
        self.operator = ensure_type(operator)
        self.operands = map(ensure_type, operands)

class FunType(object):
    def __init__(self, *input_output_types):
        self.input_names = []
        self.input_types = []
        self.return_name = None
        self.return_type = None
        for i,t in enumerate(input_output_types):
            if type(t) is tuple:
                n,t = ensure_type(t)
            else:
                n,t = None, ensure_type(t)
            if i == len(input_output_types) - 1:
                self.return_name = n
                self.return_type = t
            else:
                self.input_names.append(n)
                self.input_types.append(t)

class DataType(object):
    def __init__(self, children):
        #children can be a list or a dict
        self.is_labelled = False
        self.child_names = None
        if type(children) is list:
            self.child_types = list(map(ensure_type, children))
        else:
            assert type(children) is dict, "Children must be a list or dict"
            self.is_labelled = True
            self.child_names = children.keys()
            self.child_types = list(map(ensure_type, children.values()))

    def get(self, index_or_key):
        if not self.child_names:
            assert type(index_or_key) in (int, float), "Key must be an int for unlabelled data types"
            return self.child_types[index_or_key]

        assert type(index_or_key) is str, "Key must be an str for labelled data types"
        for n,t in zip(self.child_names, self.child_types):
            if n == index_or_key:
                return t
        set_trace()
        raise Exception("Child/Variant %s not found" % index_or_key)

class RefinedType(object):
    def __init__(self, target_type):
        self.target_type = ensure_type(target_type)

class Type(Union, annotations.Annotatable):
    native = Variant(NativeType)
    funtype = Variant(FunType)
    record = Variant(DataType)
    tuple = Variant(DataType)
    union = Variant(DataType)
    var = Variant(str)
    fun = Variant(TypeFun)
    app = Variant(TypeApp)
    refined = Variant(RefinedType)

    def __getitem__(self, expr_vals):
        """ Performs a type application. """
        if type(expr_vals) is tuple:
            expr_vals = list(iter(expr_vals))
        elif type(expr_vals) is not list:
            expr_vals = [expr_vals]
        return Type.as_app(self, map(ensure_type, expr_vals))
