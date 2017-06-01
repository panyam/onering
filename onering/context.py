
from __future__ import absolute_import
import ipdb
from typelib import core as tlcore
from typelib import ext as tlext
from onering import resolver
from onering import errors
from onering.utils import dirutils
from onering.core import fgraph
from onering.core import entities as ore

class OneringContext(dirutils.DirPointer):
    def __init__(self):
        dirutils.DirPointer.__init__(self)
        self.entity_resolver = resolver.EntityResolver("pdsc")
        self.global_module = ore.Module(None, None)
        self.fgraph = fgraph.FunGraph()
        self.register_default_types()

        self.output_dir = "./gen"
        self.platform_aliases = {
            "java": "onering.generator.backends.java.JavaTargetBackend"
        }
        self.default_platform = "java"
        self.template_dirs = []

        from onering.templates import loader as tplloader
        self.template_loader = tplloader.TemplateLoader(self.template_dirs)

    def register_default_types(self):
        # register references to default types.
        for t in [tlcore.AnyType,
                  tlcore.VoidType,
                  tlext.BooleanType,
                  tlext.ByteType, 
                  tlext.IntType,
                  tlext.LongType,
                  tlext.FloatType, 
                  tlext.DoubleType,
                  tlext.StringType,
                  tlext.ArrayType,
                  tlext.MapType]:
            self.global_module.add(t.name, t)

    def ensure_module(self, fqn):
        """ Ensures that a given module hierarchy exists. """
        curr = self.global_module
        parts = fqn.split(".")
        for part in parts:
            if not curr.has_entity(part):
                child = ore.Module(part, curr)
                curr.add(child)
                curr = child
        return curr

    def get_platform(self, name, register = False, annotations = None, docs = ""):
        """
        Get a platform binding container by its name.
        """
        if register:
            if name not in self._platforms:
                from onering.core import platforms
                self._platforms[name] = platforms.Platform(name, annotations, docs)
        return self._platforms[name]
