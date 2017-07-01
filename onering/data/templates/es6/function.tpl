{% import "es6/macros.tpl" as macros %}

{% if with_variable %} {{ function.fqn }} = {% endif %}
{{ macros.render_function(function, view) }}
