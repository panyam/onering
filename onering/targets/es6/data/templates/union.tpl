
{{union.fqn.fqn}} = class {
    constructor(valuetype, value) {
        this.valuetype = valuetype;
        this.value = value;
    }

    {% for arg in union.thetype.args %}
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
}
exports.{{union.fqn.fqn}} = {{union.fqn.fqn}};
{{union.fqn.fqn}}.__properties__ = [{% for arg in union.thetype.args %}
        {% if loop.index0 > 0 %}, {% endif %}
        "{{arg.name}}"
        {% endfor %}
];
