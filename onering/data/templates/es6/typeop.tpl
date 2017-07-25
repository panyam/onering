
{{ typeop.fqn }} = function({% for param in typeop.params %}
                            {% if loop.index0 > 0 %}, {%endif%}{{param}}
                       {%endfor%}) {
    return {{render_type(typeop.expr, importer)}};
}
