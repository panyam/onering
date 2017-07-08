{% import "es6/macros.tpl" as macros %}

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

    static __typeinfo__ = null;
    static typeinfo() {
        if (__typeinfo__ == null) {
            __typeinfo__ = {{macros.render_type(record.thetype, record.thetype.default_resolver_stack)}};
        }
        return __typeinfo__;
    }
}
exports.{{record.fqn.fqn}} = {{record.fqn.fqn}};
