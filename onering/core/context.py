
from __future__ import absolute_import
import ipdb
import pkgutil
from typelib import core as tlcore
from typelib import ext as tlext
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
            self.global_module.add(t.name, t)

    def load_template(self, template_name):
        return self.template_loader.load_template(template_name)

    def load_core_schemas(self):
        from onering import dsl
        source = pkgutil.get_data("onering", "data/schemas/core.schema").decode('utf-8')
        parser = dsl.parser.Parser(source, self)
        parser.parse()
        ipdb.set_trace()
