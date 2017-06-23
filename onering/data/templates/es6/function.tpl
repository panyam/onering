{% import "es6/macros.tpl" as macros %}

{{ function.fqn }} = function(
{% for typearg in function.source_typeargs %}{% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}{%endfor%}) {
    {# The constructor for output #}
    {% if not function.returns_void %}
    var {{ function.dest_typearg.name }} = {{ gen_constructor(function.dest_typearg.type_expr, resolver_stack, importer) }};
    {% endif %}

    {%if view.symtable.declarations %}
    var {% for varname, vartyperef in view.symtable.declarations %}{% if loop.index0 > 0 %}, {%endif%}{{ varname }}{% endfor %};
    {%endif%}
    {% for instruction in view.instructions %}
    {{ macros.render_instruction(instruction) }}
    {% endfor %}

    {# Return output var if required #}
    {% if not function.returns_void %}
    return {{ function.dest_typearg.name }};
    {% endif %}
}
