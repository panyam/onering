
{{ typefun.fqn }} = function({% for param in typefun.type_params %}
                            {% if loop.index0 > 0 %}, {%endif%}{{param}}
                       {%endfor%}) {
    return {{render_type(typefun.expr, importer)}};
}
