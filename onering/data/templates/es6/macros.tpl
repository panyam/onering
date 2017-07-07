
{% macro render_type(thetype, importer) -%}
onering.core.Type({"fqn": "{{thetype.fqn}}", "clazz": "{{thetype.fqn}}", "category": "{{thetype.category}}", "args": [
    {% for arg in thetype.args %}
    {
        {% if arg.name %}'name': "{{arg.name}}",{% endif %}
        'optional': {{arg.is_optional}},
        {% with typeval = arg.type_expr.resolve(thetype.default_resolver_stack) %}
        {% if typeval.name %}
            'type': onering.core.TypeRef("{{typeval.name}}"),
        {% else %}
            'type': render_type(gonering.core.TypeRef("{{typeval.name}}"), importer),
        {% endif %}
        {% endwith %}
    },
    {% endfor %}
]});
{%- endmacro %}

{% macro render_new_instruction(instruction) -%}
{{instruction.target_register.label}} = {{gen_constructor(instruction.value_typearg.type_expr, resolver_stack, importer)}};
{%- endmacro %}

{% macro render_function(function, view) -%}
function({% for typearg in function.source_typeargs %}{% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}{%endfor%}) {
    {# The constructor for output #}
    {% if not function.returns_void %}
    var {{ function.dest_typearg.name }} = {{ gen_constructor(function.dest_typearg.type_expr, resolver_stack, importer) }};
    {% endif %}

    {{render_expr(function.expr, resolver_stack)}}

    {# Return output var if required #}
    {% if not function.returns_void %}
    return {{ function.dest_typearg.name }};
    {% endif %}
}
{%- endmacro %}
