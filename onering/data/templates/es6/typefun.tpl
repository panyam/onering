
{{ typefun.fqn }} = function({% for typearg in typefun.source_typeargs %}
                                {% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}
                           {%endfor%}) {
    return {{render_type(typefun.return_typearg.type_expr)}};
}
