
import ipdb
from onering import errors

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

class Transformer(object):
    """
    Transformers define how an instance of one type can be transformed to an instance of another.
    """
    def __init__(self, fqn, src_type, dest_type, group = None, annotations = None, docs = ""):
        self.annotations = annotations or []
        self.docs = docs or ""
        self.fqn = fqn
        self.src_type = src_type
        self.dest_type = dest_type
        self.group = group
        # explicit transformer rules
        self._statements = []

    def add(self, stmt):
        if isinstance(stmt, Expression) and stmt.next is None:
            # We dont have a stream expression, error
            raise errors.OneringException("Transformer rule must be a let statement or a stream exception")
        self._statements.append(stmt)

class Expression(object):
    """
    Parent of all expressions.  All expressions must have a value.  Expressions only appear in transformers
    (or in derivations during type streaming but type streaming is "kind of" a transformer anyway.
    """
    def __init__(self):
        # The next expression in a stream if any
        # Because the stream expression is the top most level expression you could have
        self._next = None

    @property
    def next(self):
        return self._next

    @next.setter
    def next(self, value):
        if type(value) is FunctionExpression:
            ipdb.set_trace()
            raise errors.OneringException("FunctionExpressions can only be at the start of an expression stream")
        self._next = value

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
    def __init__(self, value):
        super(TupleExpression, self).__init__()
        self.value = value

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
