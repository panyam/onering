
from __future__ import absolute_import
from ipdb import set_trace
import pkgutil
import os
from typecube import core as tlcore
from typecube import ext as tlext
from onering.utils import dirutils
from onering.core import errors
from onering.core import fgraph
from onering.core import modules as ormods

class OneringContext(dirutils.DirPointer):
    def __init__(self):
        dirutils.DirPointer.__init__(self)
        self.global_module = ormods.Module(None, None)
        self.fgraph = fgraph.FunGraph()
        self.register_default_types()
        self.template_dirs = []
        self.packages = {}
        from onering.loaders import resolver
        self.entity_resolver = resolver.EntityResolver()

        from onering.core import templates as tplloader
        self.template_loader = tplloader.TemplateLoader(self.template_dirs)

        # Load all onering "core" schemas
        # self.load_core_schemas()

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
                  tlext.ListType,
                  tlext.MapType]:
            t.parent = self.global_module
            self.global_module.add(t.fqn, t)

    def load_template(self, template_name):
        return self.template_loader.load_template(template_name)

    def load_core_schemas(self):
        from onering import dsl
        source = pkgutil.get_data("onering", "data/schemas/core.schema").decode('utf-8')
        parser = dsl.parser.Parser(source, self)
        parser.parse()
        set_trace()

    def ensure_module(self, fqn):
        """ Ensures that the module given by FQN exists and is a Module object. """
        parts = fqn.split(".")
        curr = self.global_module
        for part in parts:
            if part not in curr.entity_map:
                curr.add(part, ormods.Module(part, curr))
            curr = curr.get(part)
            assert type(curr) is ormods.Module
        return curr

    def ensure_package(self, package_name, package_spec_path = None):
        if package_name not in self.packages:
            return self.load_package(package_spec_path)
        return self.packages[package_name]

    def load_package(self, package_spec_path):
        from onering.packaging import packages
        package = packages.Package(package_spec_path)

        # Now check if it exists already
        if package.name not in self.packages:
            package.load_entities(self)
            self.packages[package.name] = package
        return self.packages[package.name]
