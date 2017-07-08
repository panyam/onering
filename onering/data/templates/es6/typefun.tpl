
{% import "es6/macros.tpl" as macros %}

{{ typefun.fqn }} = function(
{% for typearg in typefun.source_typeargs %}{% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}{%endfor%}) {
    return {{macros.render_type(typefun.return_typearg.type_expr, resolver_stack.push(typefun))}};
}
