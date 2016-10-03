
import ipdb
import os
import sys

from onering import utils
from onering.generator import models as orgenmodels
from typelib import annotations as tlannotations
from typelib import core as tlcore

from jinja2 import nodes
from jinja2.ext import Extension, contextfunction

class JavaTargetBackend(object):
    """
    For generating java pojos for a given type
    """
    def __init__(self, context, backend_annotation):
        self.context = context
        self.backend_annotation = backend_annotation 

    def generate_schema(self, type_name, thetype):
        """
        Generates the files for a particular type.
        """
        context, backend_annotation = self.context, self.backend_annotation
        n,ns,fqn = utils.normalize_name_and_ns(type_name, "")
        type_registry = context.type_registry
        record = orgenmodels.TypeViewModel(self, type_name, thetype, context, backend_annotation)
        templ = self.load_template(backend_annotation.first_value_of("template") or "backends/java/mutable_pojo")
        print templ.render(record = record, backend = self)

        with self.normalized_output_stream(context.output_dir, fqn) as outstream:
            outstream.write(templ.render(record = record, backend = self))

    def generate_transformer_group(self, tgroup):
        """
        Generates the files for a particular transformer utility class.
        """
        context, backend_annotation = self.context, self.backend_annotation
        type_registry = context.type_registry
        normalized_tgroup = orgenmodels.TransformerGroupViewModel(self, tgroup, context, backend_annotation)

        templ = self.load_template(backend_annotation.first_value_of("template") or "transformers/java/default_transformer_group")
        print templ.render(tgroup = normalized_tgroup, backend = self)
        with self.normalized_output_stream(context.output_dir, tgroup.fqn) as outstream:
            outstream.write(templ.render(tgroup = normalized_tgroup, backend = self))

    def load_template(self, template_name):
        templ = self.context.template_loader.load_template(template_name)
        templ.globals["camel_case"] = camel_case
        templ.globals["signature"] = get_type_signature
        templ.globals["default_value"] = default_value_for_typeref
        templ.globals['debug'] = debug_print
        return templ

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
                return self.outstream

            def __exit__(self, type, value, traceback):
                if self.output_path:
                    self.outstream.close()
        return JavaPathStream(output_dir, fqn)

def debug_print(*text):
    print "".join(map(str, list(text)))
    return ''

def camel_case(value):
    return value[0].upper() + value[1:]

def invoke_getter(target, field):
    return "%s.get%s()" % (target, camel_case(field.name))

def invoke_checker(target, field):
    return "%s.has%s()" % (target, camel_case(field.name))

class InvokeGetterExtension(Extension):
    tags = set(["invoke_getter"])

    def __init__(self, environment):
        super(InvokeGetterExtension, self).__init__(environment)

    def parse(self, parser):
        ipdb.set_trace()
        pass
    


def get_type_signature(thetyperef):
    if type(thetyperef) is not tlcore.TypeRef:
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
        value_type = get_type_signature(thetype.arg_at(0).typeref)
        if value_type is None:
            ipdb.set_trace()
        return "List<" + value_type + ">" 
    if thetype.constructor == "map":
        key_type = get_type_signature(thetype.arg_at(0).typeref)
        value_type = get_type_signature(thetype.arg_at(1).typeref)
        if value_type is None or key_type is None:
            ipdb.set_trace()
        return "Map<" + key_type + ", " + value_type + ">"
    if thetype.constructor == "set":
        value_type = get_type_signature(thetype.arg_at(0).typeref)
        if value_type is None:
            ipdb.set_trace()
        return "Set<" + value_type + ">" 
    ipdb.set_trace()
    assert False


def default_value_for_typeref(thetyperef):
    """
    Given a typeref return the default value for it.
    """
    if type(thetyperef) is not tlcore.TypeRef:
        ipdb.set_trace()

    thetype = thetyperef.final_type
    if thetyperef.fqn:
        if thetyperef.fqn == "string":
            return ""
        if thetyperef.fqn == "double":
            return "0.0"
        if thetyperef.fqn == "int":
            return "0"
        if thetyperef.fqn == "byte":
            return "0"
        if thetyperef.fqn == "float":
            return "0.0"
        if thetyperef.fqn == "bool":
            return "false"
        return "new %s()" % thetyperef.fqn

    if thetype.constructor == "string":
        return ""
    if thetype.constructor == "double":
        return "0"

    if thetype.constructor in ("record", "union"):
        ipdb.set_trace()
        return "new %s()" % thetype.constructor

    if thetype.constructor in ("list", "array"):
        value_type = get_type_signature(thetype.arg_at(0).typeref)
        if value_type is None:
            ipdb.set_trace()
        return "new List<" + value_type + ">()" 
    if thetype.constructor == "map":
        key_type = get_type_signature(thetype.arg_at(0).typeref)
        value_type = get_type_signature(thetype.arg_at(1).typeref)
        if value_type is None or key_type is None:
            ipdb.set_trace()
        return "new Map<" + key_type + ", " + value_type + ">()"
    if thetype.constructor == "set":
        value_type = get_type_signature(thetype.arg_at(0).typeref)
        if value_type is None:
            ipdb.set_trace()
        return "new Set<" + value_type + ">()"
    ipdb.set_trace()
    assert False
