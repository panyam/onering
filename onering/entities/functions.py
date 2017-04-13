
from typelib.annotations import Annotatable

class Function(Entity):
    """
    Defines a function binding along with the mappings to each of the 
    specific backends.
    """
    def __init__(self, name, container,
                 typeref,
                 inputs_need_inference,
                 output_needs_inference,
                 annotations = None,
                 docs = ""):
        Entity.__init__(self, name, container, annotations, docs)
        self.inputs_need_inference = inputs_need_inference
        self.output_needs_inference = output_needs_inference
        self.inputs_known = not inputs_need_inference
        self.output_known = not output_needs_inference
        self.typeref = typeref

    @property
    def final_type(self):
        return self.typeref.final_type
