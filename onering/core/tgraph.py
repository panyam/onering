
import ipdb
from collections import defaultdict

class TransformerGraph(object):
    def __init__(self, context):
        self.context = context
        self.transformer_edges = defaultdict(set)

    def register_transformer_edge(self, input_types_or_refs, output_type_or_ref):
        context = self.context
        insigs = [context.get_final_type(i).signature for i in input_types_or_refs]
        outsig = context.get_final_type(output_type_or_ref).signature
        ipdb.set_trace()

    def get_transformer_chain(self, source_typerefs, target_typeref):
        """
        Given two types, finds the shortest set of transformers that can 
        result in type1 -> ... -> type2

        1. First how to find all transformers that can take source_typerefs as an input?
        """
        context = self.context
        if type(source_typerefs) is not list:
            source_typerefs = [source_typerefs]
        source_types = map(context.get_final_type, source_typerefs)
        target_type = context.get_final_type(target_typeref)

        queue = []
        # TODO - Need a better way than this!
        for tg in context.all_transformer_groups:
            for transformer in tg.all_transformers:
                return [transformer]

        # TODO - Do the BFS to get the shortest Transformer list from source to target type
        parents = defaultdict(lambda x: None)

        # We need for each transformer that is encountered, an entry in our map
        # to find this.  The key would be "signature -> transformer fqn list"
        # signature would be: input1,input2,input3:output where each type is
        # referred by its signature.  Signature should be unique for a type
        # regardless of its "name" or name of arguments.  The constructor
        # ofcourse can make a difference.
        queue = deque([(source_type.fqn, None)])
        ipdb.set_trace()
        while queue:
            next_type_fqn, parent_type_fqn = queue.popleft()
            parents[next_type.fqn] = parent_type.fqn

        return []
