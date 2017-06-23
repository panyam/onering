
{{record.fqn.fqn}} = class {
    constructor(argmap) {
        argmap = argmap || {};
        {% for arg in record.thetype.args %}
        this.{{arg.name}} = argmap.{{arg.name}} || null;
        {% endfor %}
    }
    {% for arg in record.thetype.args %}

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
}
exports.{{record.fqn.fqn}} = {{record.fqn.fqn}};
{{record.fqn.fqn}}.__properties__ = [{% for arg in record.thetype.args %}
        {% if loop.index0 > 0 %}, {% endif %}
        "{{arg.name}}"
        {% endfor %}
];
