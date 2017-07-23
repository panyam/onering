

{################################################################################################
 #
 #                                  Macros for rendering expressions
 #
 ################################################################################################}

{% macro render_function(function, view) -%}
    {%- if function.fun_type.is_type_fun -%}
    function({% for param in function.fun_type.type_params %} {% if loop.index0 > 0 %}, {%endif%}{{param}} {%endfor%}) { 
        return 
    {%- endif %}
        function({% for typearg in view.real_fun_type.source_typeargs %}{% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}{%endfor%}) {

            {# we are at the lowest level! So go ahead and render the function's expression #}
            {# The constructor for output #}
            {% if view.return_typearg %}
            var {{ view.return_typearg.name }} = {{ make_constructor(view.return_typearg.expr, importer) }};
            {% endif %}

            {% if function.name == "Http2SlackChannelListResponse" %}
            {{breakpoint(function, view)}}
            {% endif %}

            {{render_expr(function.expr)}}

            {# Return output var if required #}
            {% if view.return_typearg %}
            return {{ view.return_typearg.name }};
            {% endif %}
        }
    {% if function.fun_type.is_type_fun %}
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
            {{func_expr.fqn}}({% for expr in funapp.args %}
                {% if loop.index0 > 0 %}, {% endif %} {{render_expr(expr)}}
            {% endfor %})
        {% else %}
            {{render_function(func_expr)}}({% for expr in funapp.args %}
                {% if loop.index0 > 0 %}, {% endif %} {{render_expr(expr)}}
            {% endfor %})
        {% endif %}
    {% endwith %}
{%- endmacro %}

{%- macro render_literal(literal) -%}
    {% if literal.value_type.fqn == "string" %} "{{literal.value}}" {% else %} {{literal.value}} {% endif %}
{%- endmacro -%}

{% macro render_assignment(assignment) %}
    {% if assignment.target_variable.field_path.length == 1 %}
        {{assignment.target_variable.field_path.get(0)}} = 
    {% else %}
        {% with beginning,last = assignment.target_variable.field_path.poptail() %}
            {{importer.ensure("onering.core.externs.ensure_field_path")}}(
                {{beginning.get(0)}},
                {{beginning.get(0)}}.typeinfo(),
                "{{beginning}}"
            ).{{last}} = 
        {% endwith %}
    {% endif %}
    {{render_expr(assignment.expr)}}
{%- endmacro %}

{% macro render_var(var) -%}
    {% with first, rest = var.field_path.pop() %}
        {{importer.ensure("onering.core.externs.get_field_path")}}({{first}}, {{first}}.typeinfo(), "{{rest}}".split("/"))
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

        typeinfo() {
            if (this.__proto__.__typeinfo__ == null) {
                this.__proto__.__typeinfo__ = {{render_typeinfo(record_type)}};
            }
            return this.__proto__.__typeinfo__;
        }
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

        typeinfo() {
            if (this.__proto__.__typeinfo__ == null) {
                this.__proto__.__typeinfo__ = {{render_typeinfo(union_type)}};
            }
            return this.__proto__.__typeinfo__;
        }
    }
{%- endmacro %}

{% macro render_typeinfo(thetype) -%}
    new {{importer.ensure("onering.core.Type")}}({
        {% if thetype.docs %}"docs": "{{thetype.docs}}", {% endif %}
        {% if thetype.fqn %}"fqn": "{{thetype.fqn}}", {% endif %}
        "value": new {{importer.ensure("onering.core.TypeValue")}}(
            {% if thetype.is_literal_type %}
                "literalType"
            {% endif %}
            {% if thetype.is_typeref %}
                "typeRef"
            {% endif %}
            {% if thetype.is_product_type or thetype.is_sum_type %}
                {% if thetype.is_product_type %}
                    "productType", new {{importer.ensure("onering.core.ProductType")}}
                {% else %}
                    "sumType", new {{importer.ensure("onering.core.SumType")}}
                {% endif %}
                ({
                    "tag": "{{thetype.tag}}",
                    "args": [
                        {% for arg in thetype.args %}
                            {% if loop.index0 > 0 %}, {% endif %}
                            new {{importer.ensure("onering.core.TypeArg")}}({
                                'name': "{{arg.name}}",
                                'argtype': {{render_typeinfo(arg.expr)}}
                            })
                        {% endfor %}
                    ]
                })
            {% endif %}
            {% if thetype.is_type_fun %}
                "typeFun", new {{importer.ensure("onering.core.TypeFun")}}({
                    "params": [{% for param in thetype.type_params %} {{param}}, {% endfor %}]
                    {% if thetype.expr %}
                    ,"result": {{render_typeinfo(thetype.expr)}}
                    {% endif %}
                })
            {% endif %}
            {% if thetype.is_type_app %}
                "typeApp", new {{importer.ensure("onering.core.TypeApp")}}({
                    "fun": {{render_typeinfo(thetype.expr)}},
                    'args': [
                        {% for arg in thetype.args %}
                            {% if loop.index0 > 0 %}, {% endif %}
                            {{render_typeinfo(arg)}}
                        {% endfor %}
                    ],
                })
            {% endif %}
        )
    })
{%- endmacro %}
