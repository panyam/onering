{% import "java/macros.tpl" as macros %}

{{record.fqn.fqn}} = {{macros.render_record(record.thetype)}};
exports.{{record.fqn.fqn}} = {{record.fqn.fqn}};
