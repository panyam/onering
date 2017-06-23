
{% import "es6/macros.tpl" as macros %}

{{ function.fqn }} = function(
{% for typearg in function.source_typeargs %}{% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}{%endfor%}) {
}
