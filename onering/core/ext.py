
class CompoundExpression(Expression):
    """
    A collection of expressions streams to be run in a particular order and each introducing their own variables or 
    modifying others.   A compound expression has no type but can be streamed "into" any other expression 
    whose input types can be anything else.  Similary any expression can stream into a compound expression.
    """
    def __init__(self, expressions):
        super(CompoundExpression, self).__init__()
        self.expressions = expressions[:]

    def resolve_field_paths(self, starting_type, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        for expr in self.expressions:
            expr.resolve_field_paths(starting_type, context)

