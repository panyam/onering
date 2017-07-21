'use script'

{% for f in gen_files %}
exports.{{f.export_name}} = require("{{f.basename}}")
{% endfor %}
