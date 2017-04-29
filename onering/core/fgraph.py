
import ipdb
from collections import defaultdict, deque
from typelib import unifier as tlunifier

class FunctionGraph(object):
    def __init__(self, context):
        self.context = context
        self.function_edges = defaultdict(set)
        self.all_functions = []

    def register(self, function):
        """ Registers a new function. """
        self.all_functions.append(function)

    def get_function_chain(self, source_typerefs, target_typeref):
        """
        Given two types, finds the shortest set of transformers that can 
        result in type1 -> ... -> type2

        1. First how to find all transformers that can take source_typerefs as an input?
        """
        context = self.context
        if type(source_typerefs) is not list:
            source_typerefs = [source_typerefs]
        source_types = map(context.global_module.get, source_typerefs)
        target_type = target_typeref.final_entity

        queue = deque([])
        queue.append((source_types, []))
        visited = set()

        while queue:
            source_types, sofar = queue.popleft()

            # Find all transformers that start with the given source_types 
            # (or source_types + dest_typref for mutable functions)
            for func in self.all_functions:
                # See if any of the transformers can accept this set of
                # source types
                if func.matches_input(context, source_types):
                    # see if this function's output matches the target type
                    # if so we have a match
                    if func.matches_output(context, target_type):
                        return sofar + [func]
                    elif func not in visited:
                        visited.add(func)
                        ipdb.set_trace()
                        func_source_types = map(context.type_registry.get_final_type, function.src_fqns)
                        queue.append((func_source_types, sofar + [func]))
                if func.matches_input(context, source_types + [target_typeref]):
                    return sofar + [func]
        return []
