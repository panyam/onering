{% import "es6/macros.tpl" as macros %}

{{union.fqn.fqn}} = {{macros.render_union(union.thetype)}};
exports.{{union.fqn.fqn}} = {{union.fqn.fqn}};
