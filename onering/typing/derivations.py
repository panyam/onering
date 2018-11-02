import typing

class Derivation(object):
    """ Purpose of a derivation is to declare rules that convert let a type
    be derived from N source types.  This would not only create a new type but 
    also allow code gen to know about how to transform instances of given source 
    types into instances of the target one.
    """
    def __init__(self, source_types : List[Type], target_name : str):
        self.source_types = source_types
        self.target_name = target_name
        self.forward_transforms = []
        self.reverse_transforms = []


class Transform(object):
    """ A transformation between fields in a source type and fields in a target type. """
    def __init__(self, target_vars : List[Var], expression : Expr):
        self.expression = expression
        self.target_vars = target_vars

class Expr(object):
    """ An expression used in a transformation is either a literal, 
        a variable or a function call over other expressions.
    """
    @property
    def is_variable(self) -> bool: return False

    @property
    def is_function(self) -> bool: return False

    @property
    def is_literal(self) -> bool: return False

class Var(Expr):
    def __init__(self, value : Var, temporary : bool = False)
        self.value = value

    @property
    def is_variable(self) -> bool : return True

class Literal(Expr):
    def __init__(self, value)
        self.value = value

    @property
    def is_literal(self) -> bool: return True

class FunApp(Expr):
    def __init__(self, funcname : str, args : List[Expr], type_args : List[Type] = None)
        self.funcname = funcname
        self.args = args
        self.type_args = type_args

    @property
    def is_function(self) -> bool: return True
