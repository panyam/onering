
{% macro apply_transformer(function, result, apicall) %}
    {% if function.returns_void %}
        {# with mutable transformer #}
        var temp = {{gen_constructor(function.source_typeargs[-1].type_expr, function.default_resolver_stack, importer)}}; 
        {{importer.ensure(function.fqn)}}(result, temp);
        result = temp;
    {% else %}
        {# with immutable transformer #}
        result = {{importer.ensure(function.fqn)}}(result);
    {% endif %}
{% endmacro %}

{{view.fqn.fqn}} = class {{view.fqn.fqn.replace(".", "_")}} extends agcutils.ApiCall {
    /**
     * Creates a request object for this call with the given parameters.
     */
    createRequest() {
        var http_request = new {{importer.ensure("apizen.common.models.HttpRequest")}}();
        http_request.method = "{{view.protocol.http.method}}";
        http_request.headers = {};
        http_request.contentType = "{{view.protocol.http.content_type}}";
        {% if "{{" in view.protocol.http.endpoint %}
            http_request.path = agcutils.render_template_string("{{view.protocol.http.endpoint}}", this.params);
        {% else %}
            http_request.path = "{{view.protocol.http.endpoint}}";
        {% endif %}

        http_request.args = {};
        {% if view.protocol.http.method != "GET" %}
            {# For now the top level body can only be a kv pair list - 
            later on we can see options to upload files or do raw content etc #}
            http_request.body = new {{importer.ensure("apizen.common.models.Payload")}}();
            http_request.body.kvPairs = {};
        {% endif %}

        {#
            Now apply transformers if any.  Transformers should be applied first because 
            this gives our code to remove/cleanup/process any arguments before it is set 
            to the request object.
        #}
        {% for name,function in view.protocol.http.transformers %}
            {{importer.ensure(function.fqn)}}(this.params, http_request);
        {% endfor %}

        // Now apply any args left behind
        {% for arg in view.args %}
            {% if arg.name not in view.protocol.http.header_args and arg.name not in view.protocol.http.ignore_args %}
                if (this.params["{{arg.name}}"] || null) {
                    {% if view.protocol.http.method == "GET" or arg.name in view.protocol.http.qp_args %}
                        http_request.args["{{arg.name}}"] = this.params["{{arg.name}}"];
                    {% else %}
                        http_request.body.kvPairs["{{arg.name}}"] = this.params["{{arg.name}}"];
                    {% endif %}
                }
            {% endif %}
        {% endfor %}
        return http_request;
    }

    decodeResponse(httpResponse) {
        var result = httpResponse;
        {% if view.protocol.http.decoders %}
            {% for fqn,function in view.protocol.http.decoders %}
                {{ apply_transformer(function, "result", view) }};
            {% endfor %}
        {% else %}
            {% for function in 
                context.fgraph.get_function_chain(typeexpr_for("apizen.common.models.HttpResponse"), function.dest_typearg.type_expr) %};
                {{ apply_transformer(function, "result", view) }};
            {% endfor %}
        {% endif %}
        return result;
    }
}
