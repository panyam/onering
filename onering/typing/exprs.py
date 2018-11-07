
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
