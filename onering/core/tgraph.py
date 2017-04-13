
import ipdb
from collections import defaultdict, deque
from typelib import unifier as tlunifier

class TransformerGraph(object):
    def __init__(self, context):
        self.context = context
        self.transformer_edges = defaultdict(set)

    def register_transformer_edge(self, input_types_or_refs, output_type_or_ref):
        context = self.context
        insigs = [context.type_registry.get_final_type(i).signature for i in input_types_or_refs]
        outsig = context.type_registry.get_final_type(output_type_or_ref).signature

    def get_transformer_chain(self, source_typerefs, target_typeref):
        """
        Given two types, finds the shortest set of transformers that can 
        result in type1 -> ... -> type2

        1. First how to find all transformers that can take source_typerefs as an input?
        """
        context = self.context
        if type(source_typerefs) is not list:
            source_typerefs = [source_typerefs]
        source_types = map(context.type_registry.get_final_type, source_typerefs)
        target_type = context.type_registry.get_final_type(target_typeref)

        queue = deque([])
        queue.append((source_types, []))
        visited = set()

        while queue:
            source_types, sofar = queue.popleft()

            # Find all transformers that start with the given source_types
            for tg in context.all_transformer_groups:
                for transformer in tg.all_transformers:
                    # See if any of the transformers can accept this set of
                    # source types
                    if transformer.matches_input(context, source_types):
                        # see if this transformer's output matches the target type
                        # if so we have a match
                        if transformer.matches_output(context, target_type):
                            return sofar + [transformer]
                        elif transformer not in visited:
                            visited.add(transformer)
                            trans_source_types = map(context.type_registry.get_final_type, transformer.src_fqns)
                            queue.append((trans_source_types, sofar + [transformer]))
        return []
