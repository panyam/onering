import ipdb
from enum import Enum
from typelib import core as tlcore
from onering import core as orcore
from typelib.annotations import Annotatable
from typelib import unifier as tlunifier
from typelib.exprs import Expression
from typelib.utils import FieldPath
from onering import errors
from onering.utils.misc import ResolutionStatus

class LiteralExpression(Expression):
    """
    An expression that contains a literal value like a number, string, boolean, array, or map.
    """
    def __init__(self, value, value_type = None):
        super(LiteralExpression, self).__init__()
        self.value = value
        self.value_type = value_type
        self._evaluated_typeexpr = self.value_type

    def __repr__(self):
        return "<Literal - ID: 0x%x, Value: %s>" % (id(self), str(self.value))

class DictExpression(Expression):
    def __init__(self, values):
        super(DictExpression, self).__init__()
        self.values = values

    def set_resolver(self, resolver):
        Expression.set_resolver(resolver)
        for key,value in self.values.iteritems():
            key.set_resolver(resolver)
            value.set_resolver(resolver)

class ListExpression(Expression):
    def __init__(self, values):
        super(ListExpression, self).__init__()
        self.values = values

    def set_resolver(self, resolver):
        Expression.set_resolver(self, resolver)
        for value in self.values:
            value.set_resolver(resolver)

    def resolve_bindings_and_types(self, parent_function, sym_resolver):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        for expr in self.values:
            expr.resolve_bindings_and_types(parent_function, sym_resolver)

        # TODO - Unify the types of child expressions and find the tightest type here Damn It!!!
        self._evaluated_typeexpr = tlcore.TypeInitializer(orcore.ArrayType, tlcore.AnyType)

class TupleExpression(Expression):
    def __init__(self, values):
        super(TupleExpression, self).__init__()
        self.values = values or []

    def set_resolver(self, resolver):
        Expression.set_resolver(resolver)
        for value in self.values:
            value.set_resolver(resolver)

class IfExpression(Expression):
    """ Conditional expressions are used to represent if-else expressions. """
    def __init__(self, cases, default_expression):
        super(IfExpression, self).__init__()
        self.cases = cases or []
        self.default_expression = default_expression or []

    def set_resolver(self, resolver):
        Expression.set_resolver(self, resolver)
        for stmt in self.default_expression:
            stmt.set_resolver(resolver)

        for condition, stmt_block in self.cases:
            condition.set_resolver(resolver)
            for stmt in stmt_block:
                stmt.set_resolver(resolver)

    def __repr__(self):
        return "<CondExp - ID: 0x%x>" % (id(self))

    def set_evaluated_typeexpr(self, vartype):
        assert False, "cannot set evaluted type of an If expression (yet)"

    def resolve_bindings_and_types(self, parent_function):
        """ Resolves bindings and types in all child expressions. """
        assert self._evaluated_typeexpr == None, "Type has already been resolved, should not have been called twice."
        from onering.core.resolvers import resolve_path_from_record

        for condition, stmt_block in self.cases:
            condition.resolve_bindings_and_types(parent_function)
            for stmt in stmt_block:
                stmt.resolve_bindings_and_types(parent_function)

        for stmt in self.default_expression:
            stmt.resolve_bindings_and_types(parent_function)
        self._evaluated_typeexpr = tlcore.VoidType

