
import instructions
import StringIO
import os
import ipdb
import json
from onering import utils
import base
from onering import datatypes

from jinja2 import nodes
from jinja2.ext import Extension, contextfunction

class JavaTargetBackend(base.TargetBackend):
    """
    For generating avro espresso schemas of a given type.
    """
    def generate_transformer(self, onering, instance_transformer, output_target, **kwargs):
        source_type = instance_transformer.source_type
        target_type = instance_transformer.target_type

        schema_registry = onering.schema_registry
        field_graph = onering.field_graph

        outstream, should_close = self.normalize_output_stream(instance_transformer, output_target)

        # Step 0: Write preamble and headers
        templ = utils.load_template("transformers/java", [ InvokeGetterExtension ])
        templ.globals["camel_case"] = camel_case
        templ.globals["invoke_getter"] = invoke_getter
        templ.globals["invoke_checker"] = invoke_checker
        templ.globals["apply_transformer"] = create_transform_applier(onering)
        templ.globals["transform_field"] = create_field_transformer(onering)
        templ.globals["generate_rule_code"] = create_rule_code_generator(onering, instance_transformer)
        templ.globals['debug'] = debug_print
        # import ipdb ; ipdb.set_trace()
        # path_comps = utils.parse_field_path("name.value")
        # instructions.generate_getter_instructions(onering, source_type, "source", path_comps)
        outstream.write(templ.render(source_type = source_type,
                                     target_type = target_type, 
                                     field_graph = field_graph,
                                     schema_registry = schema_registry,
                                     transformer = instance_transformer,
                                     backend = self))
        if should_close: outstream.close()

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

def apply_transformer(onering, source_type, target_type, source_var):
    trans = onering.find_instance_transformer(source_type, target_type)
    if not trans:
        if target_type == datatypes.StringType:
            return "%s.toString()" % source_var

        ipdb.set_trace()
        raise Exception("Unable to find an instance transformer between %s and %s" % (source_type.fqn, target_type.fqn))
    return "%s.transform(%s)" % (trans, source_var)

def create_transform_applier(onering):
    def apply_transformer_func(source_type, target_type):
        return apply_transformer(onering, source_type, target_type)
    return apply_transformer_func

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

"""
{% macro invoke_setter(field) %}set{{camel_case(field.name)}}({{caller()}});{% endmacro %}

{% macro generate_rule_code(rule, sourceType) %}
    // Stored values for all the source fields
    {% for source_field in rule.source_fields %}
    {{ source_field.field_type.fqn }} inval{{rule.index}} = null;
    {% set source_field_path = rule.source_field_paths[loop.index0] %}
    {{ call_nested_getter("source", sourceType, rule, "inval", 0, source_field_path) }}
    {% endfor %}
{% endmacro %}


{% macro call_nested_getter(source, sourceType, rule, varprefix, level, source_field_path) %}
    Type: {{ source_field_path[level] }}
    {% set field_name = source_field_path[level].name %}
    if ({{source}}.{{invoke_checker(field_name)}}) {
        {{ sourceType.fields[field_name].field_type.fqn }} var{{level}} = {{source}}.{{invoke_getter(field_name)}});
    }
{% endmacro %}
"""

def signature(thetype):
    """
    Return the language specific signature string denoting a type used as a variable type identifier.
    """
    if thetype.is_basic_type():
        return thetype.signature
    elif thetype.is_record_type():
        return thetype.signature

def create_field_transformer(onering):
    def transform_field_func(source_var, source_field, target_var, target_field):
        lines = [ ]
        preamble = "if ( %s ) {" % invoke_checker(source_var, source_field)
        if target_field.field_type.is_list_type:
            target_list_type = target_field.field_type.type_data.value_type.list_type
            lines.extend([
                "if ( ! %s ) {" % invoke_checker(target_var, target_field),
                "    %s.set%s(new %s());" % (target_var, camel_case(target_field.name), target_list_type),
                "}",
                "%s target_list = %s;" % (target_list_type, invoke_getter(target_var, target_field)),
            ])

        if source_field.field_type.is_list_type and target_field.field_type.is_list_type:
            # We have two lists we need to copy from and to.
            # When two things arent lists we are good 
            transformer_code = apply_transformer(onering, source_field.field_type.type_data.value_type, target_field.field_type.type_data.value_type, "entry")
            lines.extend([
                "for (%s entry : %s)" % (source_field.field_type.type_data.value_type.list_type, invoke_getter(source_var, source_field)),
                "{",
                "    target_list.add(%s);" % transformer_code,
                "}"
            ])
        elif target_field.field_type.is_list_type:
            # copy source into target[0]
            transformer_code = apply_transformer(onering, source_field.field_type, target_field.field_type.type_data.value_type, source_var)
            lines.extend([
                "%s.add(%s)" % (target_var, transformer_code)
            ])
        elif source_field.field_type.is_list_type:
            getter = "%s.get(0)" % invoke_getter(source_var, source_field)
            transformer_code = apply_transformer(onering, source_field.field_type.type_data.value_type, target_field.field_type, getter)
            lines.extend([
                "%s.set%s(%s);" % (target_var, camel_case(target_field.name), transformer_code)
            ])
        else:
            # Best case - we have to "un" lists so just transform and copy
            transformer_code = apply_transformer(onering, source_field.field_type, target_field.field_type, source_var)
            lines.extend([
                "%s.set%s(%s);" % (target_var, camel_case(target_field.name), transformer_code)
            ])
        return "\n".join(["", preamble] + ["    " + l for l in lines] + ["}"])
    return transform_field_func

def create_rule_code_generator(onering, instance_transformer):
    def generate_rule_code_func(rule, source_var = "source", target_var = "target"):
        """
        Convert a rule of the type a.b.c.d -> x.y.z into getters of a, b, c, d, x, y and a setter for z.
        We need to make a decision on what to do it if any of the getter values does not exist.  

        For each of the getters, it has to be surrounded by a hasX check.  If the value does *not* exist
        then a copy of the default should be used for the value.  If the default does not exist and
        is not optional - an error can be thrown.  If the value is optional, then we can do 1 of two things:

            1. Break out of the rule
            2. Pass null to the transformer.   Passing null will work only for non basic types.  Or we could
            enforce that transformers only take in Ref versions of the type?  For now let us pass null to see
            where this fails. 
        """
        return ""
    return generate_rule_code_func
