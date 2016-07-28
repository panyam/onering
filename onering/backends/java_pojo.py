
import instructions
import StringIO
import os
import ipdb
import json
from onering import utils
import base

from jinja2 import nodes
from jinja2.ext import Extension, contextfunction

class JavaPojoTargetBackend(base.TargetBackend):
    """
    For generating java pojos for a given type
    """
    def generate(self, type_name, thetype, type_registry, output_dir, **kwargs):
        n,ns,fqn = utils.normalize_name_and_ns(type_name, "")
        if "namespace" in kwargs:
            ns = kwargs["namespace"]
            fqn = ".".join([ns, n])
        record = {
            "name": n,
            "namespace": ns,
            "import_types": [],
            "fields": [ {'field_name': fname, 
                    'field_type': ftype} for (fname, ftype) in thetype.children]
        }
        templ = utils.load_template("backends/java_pojo")
        templ.globals["camel_case"] = camel_case
        templ.globals["signature"] = get_type_signature
        templ.globals['debug'] = debug_print
        print templ.render(record = record)

        output_path = os.path.join(output_dir, *fqn.split("."))
        if not os.path.isdir(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))
        outstream = open(output_path + ".java", "w")
        outstream.write(templ.render(record = record, backend = self))
        outstream.close()

    def normalize_output_stream(self, instance_transformer, output_target = None):
        if output_target == None:
            return sys.stdout, False
        elif type(output_target) not in (str, unicode):
            return output_target, False
        elif os.path.isfile(output_target):
            return open(output_target, "w"), True
        else:
            folder = os.path.join(output_target, instance_transformer.namespace.replace(".", os.sep))
            if not os.path.isdir(folder):
                os.makedirs(folder)
            path = os.path.join(folder, instance_transformer.name) + ".java"
            return open(path, "w"), True

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
    
def get_type_signature(thetype):
    if thetype.constructor == "record":
        return thetype.fqn
    if thetype.constructor == "string":
        return "String"
    if thetype.constructor == "double":
        return "Double"
    if thetype.constructor == "list":
        value_type = get_type_signature(thetype.child_type_at(0))
        if value_type is None:
            ipdb.set_trace()
        return "List<" + value_type + ">" 
    if thetype.constructor == "map":
        key_type = get_type_signature(thetype.child_type_at(0))
        value_type = get_type_signature(thetype.child_type_at(1))
        if value_type is None or key_type is None:
            ipdb.set_trace()
        return "Map<" + key_type + ", " + value_type + ">"
    if thetype.constructor == "set":
        value_type = get_type_signature(thetype.child_type_at(0))
        if value_type is None:
            ipdb.set_trace()
        return "Set<" + value_type + ">" 
    if len(thetype.children) == 0:
        return thetype.fqn
    assert False

