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

