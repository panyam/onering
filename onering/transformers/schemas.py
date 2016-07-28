
from onering import datatypes
from onering import fields
from onering import mapper
from onering import utils
from onering import registry
from onering import errors
from itertools import izip
import ipdb
import os, json

class SchemaTransformer(object):
    """
    Schema transformers convert one schema to another.  No instance transformation is going on here.
    """
    def load_schema_from_data(self, transformer_dict, schema_registry):
        self.source_name, self.source_namespace, self.source_fqn = utils.normalize_name_and_ns(transformer_dict.get("source", None),
                                                                                       transformer_dict.get("namespace", ""),
                                                                                       ensure_namespaces_are_equal = False)
        self.target_name, self.target_namespace, self.target_fqn = utils.normalize_name_and_ns(transformer_dict.get("target", None),
                                                                                       transformer_dict.get("namespace", ""),
                                                                                       ensure_namespaces_are_equal = False)
        self.source_type = schema_registry.get_schema(self.source_fqn)
        self.field_mapped_from_source = {}
        self.field_mapped_to_target = {}
        self.mappers = []
        self.annotations = []
        self.excludes = []
        self.fields = []
        self.includes = transformer_dict.get("include", [])
        self.default_transformer = transformer_dict.get("default_transformer", None)

        for transformer_name in self.includes:
            # Note these can be included models *or* transformers
            try:
                transformer = schema_registry.get_schema(transformer_name, registry.SCHEMA_CLASS_ST)
                self.mappers.extend(transformer.mappers)
                self.annotations.extend(transformer.annotations)
                self.excludes.extend(transformer.excludes)
                self.fields.extend(transformer.fields)
            except errors.SchemaNotFoundException, exc:
                type_schema = schema_registry.get_schema(transformer_name, registry.SCHEMA_CLASS_TYPE)
                fields = type_schema.to_json().get("fields", [])
                self.fields.extend(fields)

        self.fields.extend(transformer_dict.get("fields", []))
        self.mappers.extend(transformer_dict.get("mappers", []))
        self.annotations.extend(transformer_dict.get("annotations", []))
        self.excludes.extend(transformer_dict.get("exclude", []))

    def is_anonymous(self):
        return not self.source_fqn or not self.target_fqn

    def apply(self, onering):
        """
        Applies the current transformer on the contents of a schema registry (creating new models in the process).

        The steps taken are:

          (Following to be done only the first time - ie when the source_type and target_type are None.)
            1. Copy all fields from source field into target field.  
            2. Annotations will also be copied as is for now (this is to be decided).

          (Following to be done every time).
            3. Apply all the mappers in the transformer for each field.  The mapper can change the field
               in anyway (ie name, type, doc, annotation etc).   With the mapping edges in the field graph 
               may be created or changed.
               Two caveats:
               * The field that is returned by the mapper must NOT exist already otherwise an error is raised.  
               * The fields on which the mapper is applied must be a field that is defined in the corresponding 
                 "source" model or any of its parents, but not its children.
            4. Create new fields defined in the "fields" section of the transformer.  This will override any fields 
               created by any mappers previously defined.
            5. Remove any fields listed in the "exclude" section.  Note the fields defined in the "exclude" section 
               are named as they are in the source type.  So the final mapped field in the target type is what is 
               deleted.

            Now for each transformer in the "transformers" entry, apply rules 4-6 recursively.
        """
        if self.is_anonymous():
            raise errors.TransformerException("Cannot apply an anonymous transformer as it does not have a source or target type")

        schema_registry = onering.schema_registry
        field_graph = onering.field_graph

        if self.includes:
            for transformer_fqn in self.includes:
                try:
                    schema_transformer = schema_registry.load_schema_from_path_or_fqn(transformer_fqn, registry.SCHEMA_CLASS_ST)
                    if not schema_transformer.is_anonymous():
                        schema_transformer.apply(onering)
                except:
                    # not a schema transformer so do nothing
                    pass

        if self.source_type.is_record_type:
            self._apply_to_record_type(onering)
        elif self.source_type.is_enum_type:
            self._apply_to_enum_type(onering)
        else:
            assert False, "Not sure how to deal with non record types just yet"
        self._generate_default_transformer(onering)

    def _apply_to_record_type(self, onering):
        schema_registry = onering.schema_registry
        field_graph = onering.field_graph
        self.target_type = datatypes.RecordType(self.target_name, self.target_namespace)
        schema_registry.register(self.target_type, registry.SCHEMA_CLASS_TYPE)

        source_fields = self.source_type.type_data.all_fields()
        target_fields = map(lambda x: x.copy(), source_fields)

        for f in target_fields:
            f.record = self.target_type

        # Now apply the following:
        # Step 1: Apply the mappers (if any)
        for mapper_data in self.mappers:
            mapper_name = mapper_data["name"]
            field_mapper = mapper.load_mapper(mapper_name)
            target_fields = mapper.transform_fields(field_mapper, target_fields[:])
        self.target_type.type_data.set_fields(target_fields)

        # mark field dependencies
        for (sf,tf) in izip(source_fields, target_fields):
            # check if types are same - then it is a plain mapping
            field_graph.add_field_edge(sf, tf, "mapping")
            field_graph.add_field_edge(tf, sf, "mapping")
            self.field_mapped_from_source[sf.name] = tf.name
            self.field_mapped_to_target[tf.name] = sf.name

        # Step 2: Set new annotations.
        # TODO: Should annotations in the source model be copied over?
        self.target_type.annotations = self.annotations
        self.target_type.type_data.derivedFrom = self.source_type.fqn

        # Step 3: Remove fields to be excluded
        for field_name in self.excludes:
            source_field = self.source_type.type_data.fields[field_name]
            mapped_fields = field_graph.get_field_edges(source_field, "mapping")
            if mapped_fields:
                self.target_type.type_data.remove_field(mapped_fields[0].field)
            field_graph.remove_field_edge(source_field, "mapping")

        # Step 4: Add the new fields (or fields that replace types)
        for field in self.fields:
            try:
                newfield = fields.create_field_from_dict(field, self.target_type, schema_registry, self.target_namespace)
            except errors.SchemaNotFoundException, exc:
                # try loading schema transformer corresponding this field type first
                schema_transformer = schema_registry.load_schema_from_path_or_fqn(exc.missing_type_fqn, registry.SCHEMA_CLASS_ST)
                if not schema_transformer.is_anonymous():
                    schema_transformer.apply(onering)

                # and try again now that schema transformer was loaded and applied
                newfield = fields.create_field_from_dict(field, self.target_type, schema_registry, self.target_namespace)

            # Here if the field already exists then replace the "mapping" edge between the 
            # fields with a "type_change"
            if self.target_type.type_data.contains_field(newfield.name):
                if newfield.name not in self.field_mapped_to_target:
                    # This means a "new" field is being added twice
                    # So throw an error
                    raise errors.DuplicateFieldException(newfield.name, self.target_type)
                old_source_field_name = self.field_mapped_to_target[newfield.name]
                old_target_field = self.target_type.type_data.get_field(newfield.name)
                old_source_field = self.source_type.type_data.get_field(old_source_field_name)
                field_graph.remove_field_edge(old_source_field, "mapping")
                field_graph.add_field_edge(old_source_field, newfield, "type_change")
            self.target_type.type_data.add_field(newfield, mode = datatypes.RecordTypeData.AddMode_Overwrite)

    def _apply_to_enum_type(self, onering):
        self.target_type = datatypes.EnumType(self.target_name, self.target_namespace, self.source_type.type_data.symbols)
        onering.schema_registry.register(self.target_type, registry.SCHEMA_CLASS_TYPE)

    def _generate_default_transformer(self, onering):
        schema_registry = onering.schema_registry
        field_graph = onering.field_graph
        if self.default_transformer:
            rules = []
            contents = {
                "source": self.source_type.fqn,
                "target": self.target_type.fqn,
                "name": self.target_type.fqn,
                "namespace": self.target_type.namespace,
                "type": "instance_transformer",
                "rules": rules
            }
            instance_transformer = schema_registry.load_schema_from_data(contents, registry.SCHEMA_CLASS_IT)
            onering.add_default_transformer(self.source_type, self.target_type, instance_transformer)

def transform_record_type(transformer_dict, schema_registry, field_graph, source_type = None, target_type = None):
    """
    Applies a schema transformer between a source and target type that are records.
    If the source type or target type is None then it is loaded from the values defined in the 
    transformer dict.  This is because it is possible to apply a transformer between one class onto 
    antoher class (due to includes as explained below).

    The steps taken are:

      (Following to be done only the first time - ie when the source_type and target_type are None.)
        1. Copy all fields from source field into target field.  
        2. Annotations will also be copied as is for now (this is to be decided).

      (Following to be done every time).
        3. Apply all the mappers in the transformer for each field.  The mapper can change the field
           in anyway (ie name, type, doc, annotation etc).   With the mapping edges in the field graph 
           may be created or changed.
           Two caveats:
           * The field that is returned by the mapper must NOT exist already otherwise an error is raised.  
           * The fields on which the mapper is applied must be a field that is defined in the corresponding 
             "source" model or any of its parents, but not its children.
        4. Create new fields defined in the "fields" section of the transformer.  This will override any fields 
           created by any mappers previously defined.
        5. Remove any fields listed in the "exclude" section.  Note the fields defined in the "exclude" section 
           are named as they are in the source type.  So the final mapped field in the target type is what is 
           deleted.

        Now for each transformer in the "transformers" entry, apply rules 4-6 recursively.
    """
    is_at_original_types = source_type is None or target_type is None

    curr_source_type = schema_registry.get_type(transformer_dict["source"], transformer_dict.get("namespace", ""))
    curr_target_name, curr_target_namespace = utils.normalize_name_and_ns(transformer_dict["target"], transformer_dict.get("namespace", ""))
    if is_at_original_types:
        curr_target_type = datatypes.RecordType(curr_target_name, target_namespace)
        schema_registry.register_type(curr_target_type)
        final_source_type = curr_source_type
        final_target_type = curr_target_type 

        # Step 1 and 2: One time copy of fields and annotations from source to target type
        copy_fields(final_source_type, final_target_type)
    else:
        curr_target_type = schema_registry.get_type(curr_target_name, curr_target_namespace)
        final_source_type = source_type
        final_target_type = target_type

    # Step 3: Apply mappers
    mappers = transformer_dict.get("mappers", [])
    apply_mappers(final_source_type, final_target_type,
                  [field.name for fiend in curr_source_type.all_fields()],
                  mappers, field_graph)

    return final_source_type, final_target_type

def copy_fields(source_type, target_type):
    # Step 1: Copy all fields from source field into target field.  
    source_fields = source_type.type_data.all_fields()
    target_fields = [x.copy() for x in source_fields]

    for f in target_fields:
        f.record = target_type

    # Step 2: Copy annotations
    # TODO: Should annotations in the source model be copied over?
    target_type.annotations = transformer_dict.get("annotations", [])
    target_type.type_data.derivedFrom = source_type.fqn
    target_type.type_data.set_fields(target_fields)

    # mark dependencies in field graph
    for (sf,tf) in izip(source_fields, target_fields):
        # this is a plain mapping
        field_graph.add_field_edge(sf, tf, "mapping")

def apply_mappers(source_type, target_type, field_names, mappers, field_graph):
    # Now apply the following:
    # Step 1: Apply the mappers (if any)
    for mapper_data in mappers:
        mapper_name = mapper_data["name"]
        field_mapper = mapper.load_mapper(mapper_name)
        target_fields = mapper.transform_fields(field_mapper, target_fields[:])
    target_type.type_data.set_fields(target_fields)

    # mark field dependencies
    for (sf,tf) in izip(source_fields, target_fields):
        # check if types are same - then it is a plain mapping
        field_graph.add_field_edge(sf, tf, "mapping")
