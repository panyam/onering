
import os, sys
import json

class SchemaBackend(object):
    """
    Interface for all backends that can generate models
    """
    def generate_schema(self, onering, schema_transformer, output_target, **kwargs):
        outstream, should_close = self.normalize_output_stream(output_target)
        json.dump(schema_transformer.target_type.to_json(), outstream, indent = 4, sort_keys = True)
        if should_close: outstream.close()

    def normalize_output_stream(self, schema_transformer, output_target = None):
        if output_target == None:
            return sys.stdout, False
        elif type(output_target) not in (str, unicode):
            return output_target, False
        elif os.path.isfile(output_target):
            return open(output_target, "w"), True
        else:
            target_type = schema_transformer.target_type
            target_type_folder = os.path.join(output_target, target_type.namespace.replace(".", os.sep))
            if not os.path.isdir(target_type_folder):
                os.makedirs(target_type_folder)
            target_type_path = os.path.join(target_type_folder, target_type.name) + ".pdsc"
            return open(target_type_path, "w"), True


class AvroEspressoBackend(SchemaBackend):
    """
    For generating avro espresso schemas of a given type.
    """
    pass


class PegasusBackend(SchemaBackend):
    """
    For generating pegasus schemas of a given type.
    """
    pass
