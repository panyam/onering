
{% macro render_instruction(instruction) -%}
{% if instruction.__class__.__name__ == "IfStatement" -%}
    {{ render_if_instruction(instruction) }}
{%- elif instruction.__class__.__name__ == "SetFieldInstruction" -%}
    {{ render_setfield_instruction(instruction) }}
{%- elif instruction.__class__.__name__ == "GetFieldInstruction" -%}
    {{ render_getfield_instruction(instruction) }}
{%- elif instruction.__class__.__name__ == "CopyVarInstruction" -%}
    {{ render_copyvar_instruction(instruction) }}
{%- elif instruction.__class__.__name__ == "FunAppInstruction" -%}
    {{ render_funccall_instruction(instruction) }}
{%- elif instruction.__class__.__name__ == "ContainsInstruction" -%}
    {{ render_contains_instruction(instruction) }}
{%- elif instruction.__class__.__name__ == "NewInstruction" -%}
    {{ render_new_instruction(instruction) }}
{%- elif instruction.__class__.__name__ == "ValueOrVar" -%}
    {{str(instruction)}}
{%- endif %}
{%- endmacro %}

{% macro render_if_instruction(if_instruction) %}
    if ({%if if_instruction.negate -%}!{% endif -%}{{render_instruction(if_instruction.condition_expr)}})
    {
        {% for instruction in if_instruction.body %}
        {{ render_instruction(instruction) }}
        {% endfor %}
    }
    {% if if_instruction.otherwise -%}
    else {
        {% for instruction in if_instruction.otherwise -%}
        {{ render_instruction(instruction) }}
        {%- endfor %}
    }
    {%- endif %}
{% endmacro %}

{% macro render_getfield_instruction(instruction) %}
    {{instruction.target_register.label}} = {{instruction.source_register.label}}.{{instruction.field_key}};
{% endmacro %}

{% macro render_copyvar_instruction(instruction) -%}
{{instruction.target_register.label}} = {{instruction.source_register.label}};
{%- endmacro %}

{% macro render_setfield_instruction(instr) -%}
{{instr.target_register.label}}.{{instr.field_key}} = {{instr.source_register.label}};
{%- endmacro %}

{% macro render_funccall_instruction(funcinst) -%}
{% if funcinst.output_register %}
    {{funcinst.output_register.label}} = 
{% endif %}
    {{importer.ensure(funcinst.func_fqn)}}({{ ", ".join(map(str, funcinst.input_registers)) }});
{%- endmacro %}

{% macro render_contains_instruction(instruction) -%}
{{instruction.source_register.label}}.has{{camel_case(instruction.field_name)}}
{%- endmacro %}

{% macro render_new_instruction(instruction) -%}
{{instruction.target_register.label}} = {{gen_constructor(instruction.value_typearg.type_expr, resolver_stack, importer)}};
{%- endmacro %}

{% macro render_function(function, view) -%}
function({% for typearg in function.source_typeargs %}{% if loop.index0 > 0 %}, {%endif%}{{typearg.name}}{%endfor%}) {
    {# The constructor for output #}
    {% if not function.returns_void %}
    var {{ function.dest_typearg.name }} = {{ gen_constructor(function.dest_typearg.type_expr, resolver_stack, importer) }};
    {% endif %}

    {%if view.symtable.declarations %}
    var {% for varname, vartyperef in view.symtable.declarations %}{% if loop.index0 > 0 %}, {%endif%}{{ varname }}{% endfor %};
    {%endif%}
    {% for instruction in view.instructions %}
    {{ render_instruction(instruction) }}
    {% endfor %}

    {# Return output var if required #}
    {% if not function.returns_void %}
    return {{ function.dest_typearg.name }};
    {% endif %}
}
{%- endmacro %}
