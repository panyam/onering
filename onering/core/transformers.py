
import errors


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
        self._rules = []

    def add_rule(self, rule):
        self._rules.append(rule)

class Rule(object):
    """
    A rule for specifying the source to dest field transformation.
    """
    def __init__(self, expression, target, temporary = False, annotations = None, docs = ""):
        self.annotations = annotations or []
        self.docs = docs or ""
        # Is the rule setting a temporary var?
        self.is_temporary = temporary

        # Dest being set
        self.target = target

        # The source spec (including any transformer method calls)
        self.expression = expression
        if type(expression) in (str, unicode, int, long, float, bool, dict, list):
            self.expression = Expression(None, expression)
        elif type(expression) is not Expression:
            raise errors.OneringException("expression must be a literal type or a Expression.  Found: %s" % str(type(expression)))

class Expression(object):
    """
    Specifies the expression that will be the source 

    The source can be a literal:

        string, int, bool, map, list

    or a function:

        func_fqn + func_args, where func_args = list of SourceValues

    or a field path:
        a/b/c/d

    If source is None, then the arguments form a literal of a tuple type!
    """ 
    def __init__(self, source, args = None):
        self.source = source
        self.args = args
