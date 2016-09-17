
import ipdb
from onering import errors
from onering.utils import ResolutionStatus

class TransformerGroup(object):
    """
    A transformer group enables a set of transformers to be logically grouped.  This group and its
    data are available for all transformers within this group.   The group also determins how the
    """
    def __init__(self, fqn, annotations = None, docs = ""):
        self.fqn = fqn
        self._transformers = []
        self.annotations = annotations or []
        self.docs = docs or ""

    @property
    def all_transformers(self):
        return self._transformers[:]

    def add_transformer(self, transformer):
        self._transformers.append(transformer)
        """
        if transformer.fqn in self._transformers:
            raise errors.OneringException("Duplicate transformer found: " % transformer.fqn)
        self._transformers[transformer.fqn] = transformer
        """

    def resolve(self, context):
        """
        Kicks of resolutions of all dependencies.  This must only be called after all derivations that produce records
        have been resolved otherwise those records that are only derived will not be visible in the type_registry.
        """
        for transformer in self._transformers:
            transformer.resolve(context)

class Transformer(object):
    """
    Transformers define how an instance of one type can be transformed to an instance of another.
    """
    def __init__(self, fqn, src_fqn, dest_fqn, group = None, annotations = None, docs = ""):
        self.resolution = ResolutionStatus()
        self.annotations = annotations or []
        self.docs = docs or ""
        self.fqn = fqn
        self.src_fqn = src_fqn
        self.dest_fqn = dest_fqn
        self.group = group
        # explicit transformer rules
        self._statements = []

    def add_statement(self, stmt):
        if isinstance(stmt, Expression) and stmt.next is None:
            # We dont have a stream expression, error
            raise errors.OneringException("Transformer rule must be a let statement or a stream exception, Found: %s" % str(type(stmt)))
        self._statements.append(stmt)

    def resolve(self, context):
        """
        Kicks of resolutions of all dependencies.  This must only be called after all derivations that produce records
        have been resolved otherwise those records that are only derived will not be visible in the type_registry.
        """
        def resolver_method():
            self._resolve(context)
        self.resolution.perform_once(resolver_method)


    def _resolve(self, context):
        """
        The main resolver method.
        """
        type_registry = context.type_registry
        self.src_type = type_registry.get_type(self.src_fqn)
        self.dest_type = type_registry.get_type(self.dest_fqn)

        self._evaluate_auto_rules(context)

        temp_vars = {}
        for stmt in self._statements:
            self._evaluate_manual_rule(stmt, context, temp_vars)

    def _evaluate_auto_rules(self, context):
        """
        Given the source and dest types, evaluates all "get/set" rules that can be 
        inferred for shared types.   This is only possible if both src and dest types 
        share a common ancestor (or may be even at atmost 1 level).
        """

        # Step 1: Find common "ancestor" of each of the records
        ancestor = context.find_common_ancestor(self.src_type, self.dest_type)
        ipdb.set_trace()
        if ancestor is None:
            # If the two types have no common ancestor then we cannot have auto rules
            return 

    def _evaluate_manual_rule(self, rule, context, temp_vars):
        pass



class Expression(object):
    """
    Parent of all expressions.  All expressions must have a value.  Expressions only appear in transformers
    (or in derivations during type streaming but type streaming is "kind of" a transformer anyway.
    """
    def __init__(self):
        # The next expression in a stream if any
        # Because the stream expression is the top most level expression you could have
        self._next = None
        self._prev = None
        self.is_temporary = False

    @property
    def next(self):
        return self._next

    @next.setter
    def next(self, value):
        if type(value) is FunctionExpression:
            ipdb.set_trace()
            raise errors.OneringException("FunctionExpressions can only be at the start of an expression stream")

        if value._prev is not None:
            value._prev._next = None
        value._prev = self
        self._next = value

    @property
    def prev(self):
        return self._prev

    @property
    def last(self):
        temp = self
        while temp.next is not None:
            temp = temp.next
        return temp

class CompoundExpression(Expression):
    """
    A collection of expressions streams to be run in a particular order and each introducing their own variables or 
    modifying others.   A compound expression has no type but can be streamed "into" any other expression 
    whose input types can be anything else.  Similary any expression can stream into a compound expression.
    """
    def __init__(self, expressions):
        super(CompoundExpression, self).__init__()
        self.expressions = expressions[:]

class LiteralExpression(Expression):
    """
    An expression that contains a literal value like a number, string, boolean, array, or map.
    """
    def __init__(self, value):
        super(LiteralExpression, self).__init__()
        self.value = value

class VariableExpression(Expression):
    def __init__(self, var_or_field_path, from_source = True):
        super(VariableExpression, self).__init__()
        self.from_source = from_source
        self.value = var_or_field_path

    @property
    def is_field_path(self):
        return type(self.value) is FieldPath

class ListExpression(Expression):
    def __init__(self, value):
        super(ListExpression, self).__init__()
        self.value = value

class DictExpression(Expression):
    def __init__(self, value):
        super(DictExpression, self).__init__()
        self.value = value

class TupleExpression(Expression):
    def __init__(self, values):
        super(TupleExpression, self).__init__()
        self.values = values or []

class FunctionExpression(Expression):
    """
    An expression for denoting a function call.  Function calls can only be at the start of a expression stream, eg;

    f(x,y,z) => H => I => J

    but the following is invalid:

    H => f(x,y,z) -> J

    because f(x,y,z) must return an observable and observable returns are not supported (yet).
    """
    def __init__(self, func_name, func_args = None):
        super(FunctionExpression, self).__init__()
        self.func_name = func_name
        self.func_args = func_args
