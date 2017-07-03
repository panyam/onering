
import ipdb
from onering.core import errors
from onering.dsl import lexer
from typelib.core import Expr

class ContainsExpr(Expr):
    def __init__(self, source_expr, field_name):
        self.source_expr = source_expr
        self.field_name = field_name

class NotExpr(Expr):
    def __init__(self, source_expr):
        self.source_expr = source_expr

class GetterExpr(Expr):
    """ An expression for a getter. """
    def __init__(self, source_expr, field_name):
        self.source_expr = source_expr
        self.field_name = field_name

    def __repr__(self):
        return "GET %s[%s] -> %s" % (self.source_register, self.field_key, self.target_register)

class SetterExpr(Expr):
    """ An expression for a setter. """
    def __init__(self, source_expr, field_name, value_expr):
        self.source_expr = source_expr
        self.field_name = field_name
        self.value_expr = value_expr

    def __repr__(self):
        return "SET %s[%s] -> %s" % (self.source_expr, self.field_name, self.value_expr)

