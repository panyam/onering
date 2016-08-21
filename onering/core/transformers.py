
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
    def __init__(self):
        # The next expression in a stream if any
        self.next = None

class LiteralExpression(Expression):
    def __init__(self, value):
        super(LiteralExpression, self).__init__()
        self.value = value

class VariableDeclaration(object):
    def __init__(self, varname, varvalue):
        self.varname = varname
        self.varvalue = varvalue

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
    def __init__(self, func_name, func_args = None):
        super(FunctionExpression, self).__init__()
        self.func_name = func_name
        self.func_args = func_args
