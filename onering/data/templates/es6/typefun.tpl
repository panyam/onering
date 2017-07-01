
{% import "es6/macros.tpl" as macros %}

{{ function.fqn }} = function(
{% for typearg in function.source_typeargs %}{% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}{%endfor%}) {
    // basically a type function is a function that returns an expression - so render the expression?
    // something gets returned here
    return
    {% if view.returns_function %}
    {{macros.render_function(function.expr)}};
    {% else %}
    // Render the type
    {% endif %}
}
