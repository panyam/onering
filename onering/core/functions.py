
from typelib.annotations import Annotatable

class PlatformBinding(Annotatable):
    def __init__(self, platform, native_fqn, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.platform = platform
        self.native_fqn = native_fqn

class Function(Annotatable):
    """
    Defines a function binding along with the mappings to each of the 
    specific backends.
    """
    def __init__(self, fqn, typeref, type_inferred, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.fqn = fqn
        self.type_inferred = type_inferred
        self.typeref = typeref
        self.platform_bindings = {}

    def add_platform(self, platform_binding):
        self.platform_bindings[platform_binding.platform] = platform_binding

    @property
    def final_type(self):
        return self.typeref.final_type
