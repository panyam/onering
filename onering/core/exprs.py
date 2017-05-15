import ipdb
from enum import Enum
from onering import errors
from onering.utils.misc import ResolutionStatus
from onering.core.utils import FieldPath
from typelib import core as tlcore
from typelib.annotations import Annotatable
from typelib import unifier as tlunifier
from typelib.exprs import Expression

class LiteralExpression(Expression):
    """
    An expression that contains a literal value like a number, string, boolean, array, or map.
    """
    def __init__(self, value, value_type = None):
        super(LiteralExpression, self).__init__()
        self.value = value
        self._evaluated_typeexpr = self.value_type

    def resolve_bindings_and_types(self, function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        t = type(self.value)
        if t in (str, unicode):
            self._evaluated_typeexpr = context.global_module.get("string")
        elif t is int:
            self._evaluated_typeexpr = context.global_module.get("int")
        elif t is bool:
            self._evaluated_typeexpr = context.global_module.get("bool")
        elif t is float:
            self._evaluated_typeexpr = context.global_module.get("float")

    def __repr__(self):
        return "<Literal - ID: 0x%x, Value: %s>" % (id(self), str(self.value))

class DictExpression(Expression):
    def __init__(self, values):
        super(DictExpression, self).__init__()
        self.values = values

class ListExpression(Expression):
    def __init__(self, values):
        super(ListExpression, self).__init__()
        self.values = values

    def resolve_bindings_and_types(self, function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        for expr in self.values:
            expr.resolve_bindings_and_types(function, context)

        # TODO - Unify the types of child expressions and find the tightest type here Damn It!!!
        any_typeref = tlcore.SymbolRef("any")
        function.resolve_binding(any_typeref)
        initializer = tlcore.TypeInitializer(context.ArrayType, any_typeref)
        self._evaluated_typeexpr = tlcore.TypeExpression(initializer)

class TupleExpression(Expression):
    def __init__(self, values):
        super(TupleExpression, self).__init__()
        self.values = values or []

class IfExpression(Expression):
    """ Conditional expressions are used to represent if-else expressions. """
    def __init__(self, cases, default_expression):
        super(IfExpression, self).__init__()
        self.cases = cases or []
        self.default_expression = default_expression or []

    def __repr__(self):
        return "<CondExp - ID: 0x%x>" % (id(self))

    def set_evaluated_typeexpr(self, vartype):
        assert False, "cannot set evaluted type of an If expression (yet)"

    def resolve_bindings_and_types(self, function, context):
        """ Resolves bindings and types in all child expressions. """
        assert self._evaluated_typeexpr == None, "Type has already been resolved, should not have been called twice."
        from onering.core.resolvers import resolve_path_from_record

        for condition, stmt_block in self.cases:
            condition.resolve_bindings_and_types(function, context)
            for stmt in stmt_block:
                stmt.resolve_bindings_and_types(function, context)

        for stmt in self.default_expression:
            stmt.resolve_bindings_and_types(function, context)
        self._evaluated_typeexpr = tlcore.TypeExpression(tlcore.VoidType)

