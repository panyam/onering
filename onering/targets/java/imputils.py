
import os
import fnmatch
from ipdb import set_trace
from onering.packaging.utils import is_type_entity, is_typeop_entity, is_fun_entity, is_function_mapping_entity

class Importer(object):
    """ The purpose of this is give a method that takes a type reference/FQN and does two things:

        1. Ensures that the right "imports" for that FQN exists based on the language.
        2. After the imports are done, the final "signature" of the type is used.
    """
    def __init__(self, platform_config):
        self.platform_config = platform_config
        self._imported_fqns = set()

    def render_imports(self):
        return "\n".join("import %s;" % fqn for fqn in self._imported_fqns)
            
    def ensure(self, fqn):
        if "." in fqn:
            self._imported_fqns.add(fqn)
        return fqn
