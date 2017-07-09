

{################################################################################################
 #
 #                                  Macros for rendering expressions
 #
 ################################################################################################}

{% macro render_function(function, view) -%}
    {%- if function.fun_type.is_type_function -%}
    function({% for param in function.fun_type.type_params %} {% if loop.index0 > 0 %}, {%endif%}{{param}} {%endfor%}) { 
        return 
    {%- endif %}
        function({% for typearg in view.real_fun_type.source_typeargs %}{% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}{%endfor%}) {

            {# we are at the lowest level! So go ahead and render the function's expression #}
            {# The constructor for output #}
            {% if view.return_typearg %}
            var {{ view.return_typearg.name }} = {{ make_constructor(view.return_typearg.type_expr, importer) }};
            {% endif %}

            {{render_expr(function.expr)}}

            {# Return output var if required #}
            {% if view.return_typearg %}
            return {{ view.return_typearg.name }};
            {% endif %}
        }
    {% if function.fun_type.is_type_function %}
    }
    {% endif %}
{%- endmacro %}

{% macro render_exprlist(exprlist) %}
    {% for expr in exprlist.children %}
        {{render_expr(expr)}} ;
    {% endfor %}
{%- endmacro %}

{% macro render_funapp(funapp) %}
    {% with func_expr = funapp.resolve_function() %}
        {% if func_expr.fqn %}
            {{func_expr.fqn}}({% for expr in funapp.func_args %}
                {% if loop.index0 > 0 %}, {% endif %} {{render_expr(expr)}}
            {% endfor %})
        {% else %}
            {{render_function(func_expr)}}({% for expr in funapp.func_args %}
                {% if loop.index0 > 0 %}, {% endif %} {{render_expr(expr)}}
            {% endfor %})
        {% endif %}
    {% endwith %}
{%- endmacro %}

{% macro render_literal(literal) %} {{literal.value}} {%- endmacro %}

{% macro render_assignment(assignment) %}
    {% if assignment.target_variable.field_path.length == 1 %}
        {{assignment.target_variable.field_path.get(0)}} = 
    {% else %}
        {% with last, beginning = assignment.target_variable.field_path.poptail() %}
            ensure_field_path({{beginning.get(0)}}.__class__, "{{beginning}}").{{last}} = 
        {% endwith %}
    {% endif %}
    {{render_expr(assignment.expr)}}
{%- endmacro %}

{% macro render_var(var) -%}
    {% with first, rest = var.field_path.pop() %}
        get_field_path({{first}}, {{first}}.__class__, "{{rest}}")
    {% endwith %}
{%- endmacro %}

{% macro render_listexpr(listexpr) -%}
    [
    {% for expr in listexpr.values %}
        {% if loop.index0 > 0 %}, {% endif %} {{render_expr(expr) }}
    {% endfor %}
    ]
{%- endmacro %}

{% macro render_dictexpr(dictexpr) -%}
    {
    {% for key,value in zip(dictexpr.keys, dictexpr.values) %}
        {% if loop.index0 > 0 %}, {% endif %}
        {{render_expr(key) }}: {{render_expr(value)}}
    {% endfor %}
    }
{%- endmacro %}

{% macro render_ifexpr(ifexpr) -%}
    {% for index,(cond,body) in enumerate(ifexpr.cases) %}
        {% if loop.index0 > 0 %} else {% endif %}
        if ({{render_expr(cond)}}) {
            {{render_expr(body)}}
        }
    {% endfor %}
    {% if ifexpr.default_expr %}
        else {
            {{render_expr(ifexpr.default_expr) }}
        }
    {% endif %}
{%- endmacro %}


{################################################################################################
 #
 #                                  Macros for rendering types
 #
 ################################################################################################}

{% macro render_basic_type(thetype) -%}
    {% if thetype.tag == "record" %}
        {{render_record(thetype)}}
    {% endif %}
    {% if thetype.tag == "union" %}
        {{render_union(thetype)}}
    {% endif %}
    {% if thetype.tag == "enum" %}
        {{render_enum(thetype)}}
    {% endif %}
{%- endmacro %}

{% macro render_record(record_type) -%}
    class {
        constructor(argmap) {
            argmap = argmap || {};
            {% for arg in record_type.args %}
            this.{{arg.name}} = argmap.{{arg.name}} || null;
            {% endfor %}
        }
        {% for arg in record_type.args %}

        get {{arg.name}}() {
            return this._{{arg.name}};
        }

        set {{arg.name}}(value) {
            // TODO: Apply validators
            this._{{arg.name}} = value;
            return this;
        }

        get has{{camel_case(arg.name)}}() {
            return typeof(this._{{arg.name}}) !== "undefined";
        }
        {% endfor %}

        static typeinfo() { return {{render_typeinfo(record_type)}}; }
    }
{%- endmacro %}

{% macro render_union(union_type) -%}
    class {
        constructor(valuetype, value) {
            this.valuetype = valuetype;
            this.value = value;
        }

        {% for arg in union_type.args %}
        get is{{camel_case(arg.name)}}() {
            return "{{arg.name}}" == this.valuetype;
        }

        get {{arg.name}}() {
            return "{{arg.name}}" == this.valuetype ? this.value : null;
        }

        set {{arg.name}}(value) {
            // TODO: Apply validators
            this.valuetype = "{{arg.name}}";
            this.value = value;
            return this;
        }
        {% endfor %}

        static typeinfo() { return {{render_typeinfo(union_type)}}; }
    }
{%- endmacro %}

{% macro render_typeinfo(thetype) -%}
onering.core.Type({"fqn": "{{thetype.fqn}}", "clazz": "{{thetype.fqn}}", "args": [
    {% for arg in thetype.args %}
    {
        {% if arg.name %}'name': "{{arg.name}}",{% endif %}
        'optional': {{arg.is_optional}},
        {% with typeval = arg.type_expr.resolve() %}
        {% if typeval.fqn %}
            'type': onering.core.TypeRef("{{typeval.fqn}}"),
        {% else %}
            'type': render_typeinfo(gonering.core.TypeRef("{{typeval.fqn}}")),
        {% endif %}
        {% endwith %}
    },
    {% endfor %}
]});
{%- endmacro %}
