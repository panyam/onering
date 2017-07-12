
import ipdb
from collections import defaultdict, deque
from typecube import unifier as tlunifier

class FunGraph(object):
    def __init__(self):
        self.function_edges = defaultdict(set)
        self.all_functions = []

    def register(self, function):
        """ Registers a new function. """
        self.all_functions.append(function)

    def get_function_chain(self, source_typeexprs, target_typeexpr):
        """
        Given two types, finds the shortest set of transformers that can 
        result in type1 -> ... -> type2

        1. First how to find all transformers that can take source_name_or_exprs as an input?
        """
        if type(source_typeexprs) is not list:
            source_typeexprs = [source_typeexprs]

        queue = deque([])
        queue.append((source_typeexprs, []))
        visited = set()

        while queue:
            source_typeexprs, sofar = queue.popleft()

            # Find all transformers that start with the given source_typeexprs 
            # (or source_typeexprs + dest_typexpr for mutable functions)
            for func in self.all_functions:
                # See if any of the transformers can accept this set of
                # source typeexprs
                if func.matches_input(source_typeexprs):
                    # see if this function's output matches the target type
                    # if so we have a match
                    if func.matches_output(target_typeexpr):
                        return sofar + [func]
                    elif func not in visited:
                        visited.add(func)
                        func_source_typeexprs = [t.type_expr for t in func.source_typeargs]
                        queue.append((func_source_typeexprs, sofar + [func]))
                if func.matches_input(source_typeexprs + [target_typeexpr]):
                    return sofar + [func]
        return []
