
import collections
import json
import os
import pprint
from typelib import registry
import transformers
import graph
import backends

class OneRing(object):
    """
    The main one ring registry that manages all schemas for this session.
    """
    DEFAULT_OUTPUT_PATH = "./gen"
    def __init__(self):
        self.artifact = {}
        self.type_registry = registry.TypeRegistry()
        self.field_graph = graph.FieldGraph()
        self.output_path = OneRing.DEFAULT_OUTPUT_PATH
        self.root_models = []

        # Mapping from (SourceType/TargetType) -> InstanceTransformer
        self.default_transformers = {}


        # Mapping from (SourceType/TargetType) -> [ InstanceTransformer ]
        # If the default transformer is not found then this list is inspected
        self.transformer_map = collections.defaultdict(list)

    def reset(self):
        """
        Reset the state of onering
        """
        self.thering.reset()

    def print_state(self):
        """
        Print out the ring's current state regarding its knowledge of all the models and transformers!
        """
        print "TypeRegistry: "
        for key,value in self.schema_registry.type_cache.iteritems():
            print "%s -> " % key, json.dumps(value.to_json(), indent = 4, sort_keys = True)
            print

        self.field_graph.print_graph()

    def load_from_manifest(self, manifest_path):
        """
        Loads fields, models and transformations from a manifest file that is provided the user.
        The manifest file contains a list of schema and instance transformers.

        Any model referred from these transformers are implicitly loaded into onering and will be 
        included in the final snapshot.
        """
        manifest_path = os.path.abspath(manifest_path)
        manifest_dir = os.path.dirname(manifest_path)
        manifest = json.load(open(manifest_path))
        schema_transformers = manifest["schemaTransformers"]
        instance_transformers = manifest["instanceTransformers"]

        print "Manifest: ", manifest
        # Step 1: Generate the output models for each of the transformations
        for transformer_path in schema_transformers:
            self.load_schema_transformer(transformer_path, manifest_dir)
            
        # Step 2: Generate the instance transformers
        for transformer_path in instance_transformers:
            self.load_instance_transformer(transformer_path, manifest_dir)

    def load_schema_transformer(self, transformer_path, root_dir = "."):
        """
        Loads a schema transformer.

        Any model referred from these transformers are implicitly loaded into onering and will be 
        included in the final snapshot.
        """
        schema_transformer = self.schema_registry.load_schema_from_path_or_fqn(transformer_path, registry.SCHEMA_CLASS_ST, root_dir)
        if not schema_transformer.is_anonymous():
            schema_transformer.apply(self)

        # Step 2: Now write these models back!
        self.generate_schema(schema_transformer, self.output_path)

        # Step 3: Also generate the "default" instance transformer based on this.
        # A type can only have a default transformer if all fields are just value mappings
        # OR if there already exists a mapping (default or otherwise) for the fields
        if schema_transformer.default_transformer:
            key = self.transformer_key(schema_transformer.source_type, schema_transformer.target_type)
            self.default_transformers[key] = schema_transformer.default_transformer

        return schema_transformer

    def load_instance_transformer(self, transformer_path, root_dir = "."):
        """
        Loads an instance transformer.

        Any model referred from these transformers are implicitly loaded into onering and will be 
        included in the final snapshot.
        """
        instance_transformer = self.schema_registry.load_schema_from_path_or_fqn(transformer_path, registry.SCHEMA_CLASS_IT, root_dir)
        if not instance_transformer.is_anonymous():
            instance_transformer.apply(self)

        key = self.transformer_key(instance_transformer.source_type, instance_transformer.target_type)
        value = instance_transformer.fqn
        if value not in self.transformer_map[key]:
            self.transformer_map[key].append(value)

        # Step 2: Now write transformer code
        self.generate_transformer(instance_transformer, self.output_path)

        return instance_transformer

    def transformer_key(self, source_type, target_type):
        return source_type.fqn + "/" + target_type.fqn

    def add_default_transformer(self, source_type, target_type, transformer):
        key = self.transformer_key(source_type, target_type)
        if key not in self.default_transformers:
            self.default_transformers[key] = []
        return self.default_transformers[key].append(transformer)

    def find_instance_transformer(self, source_type, target_type):
        key = self.transformer_key(source_type, target_type)
        if key in self.default_transformers:
            return self.default_transformers[key]
        elif key in self.transformer_map:
            return self.transformer_map[key][0]
        else:
            return None

    def generate_transformer(self, instance_transformer, output_target, backend = None):
        """
        Writes the transformer class for converting an instance of the source type and to an instance of the target type the given output stream

        The target to which the generated transformer is sent depends on output_target variable and its type.

        If output_target == None, then the transformer is dumped to stdout
        If output_target is a string and the path is a directory, the backend treats this as a path to write the transformer to (the path could be a file or a directory).
        otherwise if output_target is a writer object then the writer is written to.
        """
        if not backend:
            from backends import java
            backend = backend or java.JavaTargetBackend()
        backend.generate_transformer(self, instance_transformer, output_target)

    def generate_schema(self, schema_transformer, output_target, backend = None):
        """
        Writes the target model for this schema transformer into the given output writer.

        The target to which the generated schema is sent depends on output_target variable and its type.

        If output_target == None, then the transformer is dumped to stdout
        If output_target is a string and the path is a directory, the backend treats this as a path to write the schema to (the path could be a file or a directory).
        otherwise if output_target is a writer object then the writer is written to.
        """
        if not backend:
            from backends import schema_backends
            backend = backend or schema_backends.SchemaBackend()
        backend.generate_schema(self, schema_transformer, output_target)
