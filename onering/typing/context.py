
from __future__ import absolute_import
from ipdb import set_trace
import pkgutil
import os
from onering.utils import dirutils
from onering.core import errors
from onering.core import fgraph

class ORContext(dirutils.DirPointer):
    def __init__(self):
        dirutils.DirPointer.__init__(self)
        self.runtime = tcruntime.Runtime()
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

    @property
    def global_module(self):
        return self.runtime.global_module

    def register_default_types(self):
        # register references to default types.
        for t in [tccore.AnyType,
                  tccore.VoidType,
                  tcext.BooleanType,
                  tcext.ByteType, 
                  tcext.IntType,
                  tcext.LongType,
                  tcext.FloatType, 
                  tcext.DoubleType,
                  tcext.StringType,
                  tcext.ListType,
                  tcext.MapType]:
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
