
{% macro render_type(thetype, resolver_stack) -%}
onering.core.Type({"fqn": "{{thetype.fqn}}", "clazz": "{{thetype.fqn}}", "category": "{{thetype.category}}", "args": [
    {% for arg in thetype.args %}
    {
        {% if arg.name %}'name': "{{arg.name}}",{% endif %}
        'optional': {{arg.is_optional}},
        {% with typeval = arg.type_expr.resolve(resolver_stack) %}
        {% if typeval.fqn %}
            'type': onering.core.TypeRef("{{typeval.fqn}}"),
        {% else %}
            'type': render_type(gonering.core.TypeRef("{{typeval.fqn}}"), resolver_stack),
        {% endif %}
        {% endwith %}
    },
    {% endfor %}
]});
{%- endmacro %}

{% macro render_new_instruction(instruction) -%}
{{instruction.target_register.label}} = {{make_constructor(instruction.value_typearg.type_expr, resolver_stack)}};
{%- endmacro %}

{% macro render_function(function, view) -%}
function({% for typearg in function.fun_type.source_typeargs %}{% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}{%endfor%}) {
    {# The constructor for output #}
    {% if not function.fun_type.returns_void %}
    var {{ function.fun_type.return_typearg.name }} = {{ make_constructor(function.fun_type.return_typearg.type_expr, resolver_stack) }};
    {% endif %}

    {{render_expr(function.expr, resolver_stack)}}

    {# Return output var if required #}
    {% if not function.fun_type.returns_void %}
    return {{ function.fun_type.return_typearg.name }};
    {% endif %}
}
{%- endmacro %}

{% macro render_exprlist(exprlist, resolver_stack) %}
    {% for expr in exprlist.children %}
        {{render_expr(expr, resolver_stack)}} ;
    {% endfor %}
{%- endmacro %}

{% macro render_funapp(funapp, resolver_stack) %}
    {% with func_expr = funapp.resolve_function(resolver_stack) %}
        {% if func_expr.fqn %}
            {{func_expr.fqn}}({% for expr in funapp.func_args %}
                {% if loop.index0 > 0 %}, {% endif %} {{render_expr(expr, resolver_stack)}}
            {% endfor %})
        {% else %}
            {{render_function(func_expr)}}({% for expr in funapp.func_args %}
                {% if loop.index0 > 0 %}, {% endif %} {{render_expr(expr)}}
            {% endfor %})
        {% endif %}
    {% endwith %}
{%- endmacro %}

{% macro render_literal(literal, resolver_stack) %} {{literal.value}} {%- endmacro %}

{% macro render_assignment(assignment, resolver_stack) %}
    {% if assignment.target_variable.field_path.length == 1 %}
        {{assignment.target_variable.field_path.get(0)}} = 
    {% else %}
        {% with last, beginning = assignment.target_variable.field_path.poptail() %}
            ensure_field_path({{beginning.get(0)}}.__class__, "{{beginning}}").{{last}} = 
        {% endwith %}
    {% endif %}
    {{render_expr(assignment.expr, resolver_stack)}}
{%- endmacro %}

{% macro render_var(var, resolver_stack) -%}
    {% with first, rest = var.field_path.pop() %}
        get_field_path({{first}}, {{first}}.__class__, "{{rest}}")
    {% endwith %}
{%- endmacro %}

{% macro render_listexpr(listexpr, resolver_stack) -%}
    [
    {% for expr in listexpr.values %}
        {% if loop.index0 > 0 %}, {% endif %} {{render_expr(expr, resolver_stack) }}
    {% endfor %}
    ]
{%- endmacro %}

{% macro render_dictexpr(dictexpr, resolver_stack) -%}
    {
    {% for key,value in zip(dictexpr.keys, dictexpr.values) %}
        {% if loop.index0 > 0 %}, {% endif %}
        {{render_expr(key, resolver_stack) }}: {{render_expr(value, resolver_stack)}}
    {% endfor %}
    }
{%- endmacro %}

{% macro render_ifexpr(ifexpr, resolver_stack) -%}
    {% for index,(cond,body) in enumerate(ifexpr.cases) %}
        {% if loop.index0 > 0 %} else {% endif %}
        if ({{render_expr(cond, resolver_stack)}}) {
            {{render_expr(body, resolver_stack)}}
        }
    {% endfor %}
    {% if ifexpr.default_expr %}
        else {
            {{render_expr(ifexpr.default_expr, resolver_stack) }}
        }
    {% endif %}
{%- endmacro %}
