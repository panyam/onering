
{% macro render_new_instruction(instruction) -%}
{{instruction.target_register.label}} = {{gen_constructor(instruction.value_typearg.type_expr, resolver_stack, importer)}};
{%- endmacro %}

{% macro render_function(function, view) -%}
function({% for typearg in function.source_typeargs %}{% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}{%endfor%}) {
    {# The constructor for output #}
    {% if not function.returns_void %}
    var {{ function.dest_typearg.name }} = {{ gen_constructor(function.dest_typearg.type_expr, resolver_stack, importer) }};
    {% endif %}

    {{render_expr(function.expr)}}

    {# Return output var if required #}
    {% if not function.returns_void %}
    return {{ function.dest_typearg.name }};
    {% endif %}
}
{%- endmacro %}
