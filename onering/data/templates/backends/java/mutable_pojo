package {{record.namespace}};

{% for imp in record.import_types %}
import {{imp}};
{% endfor %}
import java.util.List;
import java.util.Map;

public class {{record.name}} {
    public {{record.name}}() {
    }

    {% for field in record.fields %}
    private {{signature(field)}} _{{field.field_name}};
    {% endfor %}

    {% for field in record.fields %}
    public {{signature(field)}} get{{camel_case(field.field_name)}}() {
      return _{{field.field_name}};
    }

    public void set{{camel_case(field.field_name)}}({{signature(field)}} {{field.field_name}}) {
      _{{field.field_name}} = {{field.field_name}};
    }
    {% endfor %}
}

