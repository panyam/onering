
import ipdb
import os
import sys

from typelib import annotations as tlannotations
from typelib import core as tlcore
from typelib import records as tlrecords
from onering import utils
from onering.generator import models as orgenmodels
from onering.generator.backends import common as orgencommon

from jinja2 import nodes
from jinja2.ext import Extension, contextfunction

class JavaTargetBackend(object):
    """
    For generating java pojos.
    """
    def __init__(self, onering_context, backend_annotation):
        self.onering_context = onering_context
        self.backend_annotation = backend_annotation 
        self.platform_name = backend_annotation.first_value_of("platform")
        self.current_platform = self.onering_context.get_platform(self.platform_name)

    def generate_schema(self, type_name, thetype):
        """
        Generates the files for a particular type.
        """
        context, backend_annotation = self.onering_context, self.backend_annotation
        n,ns,fqn = utils.normalize_name_and_ns(type_name, "")
        type_registry = context.type_registry
        record = orgenmodels.TypeViewModel(self, type_name, thetype, context, backend_annotation)
        templ = self.load_template(backend_annotation.first_value_of("template") or "backends/java/mutable_pojo")

        with self.normalized_output_stream(context.output_dir, fqn) as output:
            print "Writing '%s'     ====>    '%s'" % (type_name, output.output_path)
            # print templ.render(record = record, backend = self)
            output.outstream.write(templ.render(record = record, backend = self))

    def generate_transformer_group(self, tgroup):
        """
        Generates the files for a particular transformer utility class.
        """
        context, backend_annotation = self.onering_context, self.backend_annotation
        type_registry = context.type_registry
        normalized_tgroup = orgenmodels.TransformerGroupViewModel(self, tgroup, context, backend_annotation)

        templ = self.load_template(backend_annotation.first_value_of("template") or "transformers/java/default_transformer_group")
        with self.normalized_output_stream(context.output_dir, tgroup.fqn) as output:
            print "Writing '%s'     ====>    '%s'" % (tgroup.fqn, output.output_path)
            # print templ.render(tgroup = normalized_tgroup, backend = self)
            output.outstream.write(templ.render(tgroup = normalized_tgroup, backend = self))

    def normalized_output_stream(self, output_dir, fqn):
        class JavaPathStream(object):
            def __init__(self, output_dir, fqn):
                self.output_dir = output_dir
                self.fqn = fqn
                self.output_path = None
                self.outstream = sys.stdout
                if self.output_dir:
                    self.output_path = os.path.join(output_dir, *fqn.split("."))
                    if not os.path.isdir(os.path.dirname(self.output_path)):
                        os.makedirs(os.path.dirname(self.output_path))
                    self.outstream = open(self.output_path + ".java", "w")

            def __enter__(self):
                return self

            def __exit__(self, type, value, traceback):
                if self.output_path:
                    self.outstream.close()
        return JavaPathStream(output_dir, fqn)


    def load_template(self, template_name):
        templ = self.onering_context.template_loader.load_template(template_name)
        templ.globals["camel_case"] = orgencommon.camel_case
        templ.globals['debug'] = orgencommon.debug_print
        templ.globals["signature"] = self.get_type_signature
        return templ


    def get_type_signature(self, target):
        """
        Given a target object returns a type signature that can be used for this object.  The target
        object itself can be a typeref or a field or something else that is platform specific.

        Typically the template will call this method when it needs to render the type signature of 
        a type reference at a given instance (eg field declaration, variable declaration etc).

        This method should return a String that indicates the signature of the type in the particular platform.
        """
        if isinstance(target, tlcore.TypeRef):
            thetyperef = target
        elif isinstance(target, orgenmodels.TypeArgViewModel):
            thetyperef = target.field_type
        else:
            ipdb.set_trace()

        if thetyperef.fqn:
            if thetyperef.fqn == "string":
                return "String"
            if thetyperef.fqn == "double":
                return "Double"
            if thetyperef.fqn == "int":
                return "Int"
            if thetyperef.fqn == "byte":
                return "Byte"
            if thetyperef.fqn == "boolean":
                return "Boolean"
            if thetyperef.fqn == "float":
                return "Float"
            return thetyperef.fqn

        thetype = thetyperef.final_type
        if thetype.constructor == "string":
            return "String"
        if thetype.constructor == "double":
            return "Double"
        if thetype.constructor in ("record", "union"):
            ipdb.set_trace()
            return thetype.fqn
        if thetype.constructor in ("list", "array"):
            value_type = self.get_type_signature(thetype.arg_at(0).typeref)
            if value_type is None:
                ipdb.set_trace()
            return "List<" + value_type + ">" 
        if thetype.constructor == "map":
            key_type = self.get_type_signature(thetype.arg_at(0).typeref)
            value_type = self.get_type_signature(thetype.arg_at(1).typeref)
            if value_type is None or key_type is None:
                ipdb.set_trace()
            return "Map<" + key_type + ", " + value_type + ">"
        if thetype.constructor == "set":
            value_type = self.get_type_signature(thetype.arg_at(0).typeref)
            if value_type is None:
                ipdb.set_trace()
            return "Set<" + value_type + ">" 
        ipdb.set_trace()
        assert False
