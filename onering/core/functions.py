
from typelib.annotations import Annotatable

class Parameter(Annotatble):
    def __init__(self, param_name, param_type):
        self.param_name = param_name
        self.param_type = param_type
        self.needs_inference = True

class Signature(object):
    def __init__(self, input_params = None, output_param = None):
        self.input_params = input_params or []
        self.output_param = output_param

class Function(Annotatable):
    """
    Defines a function binding along with the mappings to each of the 
    specific backends.
    """
    def __init__(self, fqn, typeref,
                 inputs_need_inference,
                 output_needs_inference,
                 annotations = None,
                 docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.fqn = fqn
        self.inputs_need_inference = inputs_need_inference
        self.output_needs_inference = output_needs_inference
        self.inputs_known = not inputs_need_inference
        self.output_known = not output_needs_inference
        self.typeref = typeref

    @property
    def final_type(self):
        return self.typeref.final_type
