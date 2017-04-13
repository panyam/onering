
import ipdb
from typelib.core import Entity

class Module(Entity):
    TAG = "MODULE"
    def __init__(self, name, parent = None, annotations = None, docs = ""):
        Entity.__init__(self, name, parent, annotations, docs)
        self.imports = []
