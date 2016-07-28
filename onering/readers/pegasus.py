
import os
import ipdb
import json
from typelib import core as tlcore
from typelib import records as tlrecords
from typelib import enums as tlenums
from typelib import utils
from typelib import errors

class PegasusSchemaLoader(object):
    """
    Takes care of loading pegasus schemas.
    """
    def __init__(self, type_registry, entity_resolver):
        self.schema_initializers = SCHEMA_INITIALIZERS
        self.entity_resolver = entity_resolver
        self.type_registry = type_registry

    def load(self, fqn_or_path, root_dir = "."):
        """
        Loads a type given its fqn or all types at a particular path.
        """
        if os.sep in fqn_or_path:
            root_dir = os.path.abspath(root_dir)
            if not fqn_or_path.startswith("/"):
                fqn_or_path = os.path.abspath(os.path.join(root_dir, fqn_or_path))
            return self.load_from_path(fqn_or_path, schema_class, root_dir)
        else:
            return self.load_by_name(fqn_or_path, return_cached = True)

    def load_from_path(self, file_path):
        """
        Reads one or more schemas from the given the absolute path and registers it into the schema registry.

        Reads the given file path and all records defined in it and inserts it into the type registry passed
        in the constructor.
        As far as this method is concerned only the entries found in the type registry should be used 
        (unless it can load others it can find).
        """
        print("Reading schemas from: %s" % file_path)
        contents = json.loads(open(file_path).read())
        assert contents is not None, "Contents ?"
        return self.load_from_data(contents)

    def load_by_name(self, name, namespace = "", return_cached = False):
        name,namespace,fqn = utils.normalize_name_and_ns(name, namespace, ensure_namespaces_are_equal = False)
        # Search for this type if it doesnt exist so we can resolve from file
        parts = fqn.split(".")
        namespace = None if len(parts) <= 1 else ".".join(parts[:-1])
        if self.type_registry.has_type(fqn) and return_cached:
            out = self.type_registry.get_type(fqn)
            if out.is_resolved:
                return out

        # otherwise load it again
        contents = self.entity_resolver.resolve_schema(fqn, "pdsc", "st")
        if not contents:
            ipdb.set_trace()
            raise errors.TypesNotFoundException(fqn)
        # Now we have a schema dictionary that we can process for its fields etc
        return self.load_from_data(contents, namespace)

    def load_from_data(self, schema_data, current_namespace = ""):
        if isinstance(schema_data, str) or isinstance(schema_data, unicode):
            # Load this first without the namespace
            if self.type_registry.has_type(schema_data):
                return self.type_registry.get_type(schema_data)
            else:
                # otherwise use the fqn
                name,namespace,fqn = utils.normalize_name_and_ns(schema_data, current_namespace, ensure_namespaces_are_equal = False)
                if self.type_registry.has_type(fqn):
                    return self.type_registry.get_type(fqn)
                else:
                    # Load it up by looking up resolvers
                    return self.load_by_name(fqn, return_cached = True)
        elif isinstance(schema_data, list):
            # Anonymous Union type so cannot be saved in registry - extract and return as is
            return union_schema_initializer(schema, schema_data, pegasus_loader, current_namespace)
        elif not isinstance(schema_data, dict):
            ipdb.set_trace()
            raise Exception("schema_data can only be a string, list or a dictionary")

        # based on type do the load!
        return self._create_new_schema(schema_data, current_namespace)

    def _create_new_schema(self, schema_data, current_namespace = None):
        # It MUST have a type property
        schema_type = schema_data.get("type", None)
        if isinstance(schema_type, list):  # Union types
            new_schema = tlcore.UnionType(None, None)
            schema_type = "union"
        else:
            if schema_type not in self.schema_initializers:
                ipdb.set_trace()
                raise Exception("Invalid type: %s" % schema_type, schema_data)
            else:
                new_schema = tlcore.Type(None)

        schema_name, schema_namespace, schema_fqn = utils.normalize_name_and_ns(schema_data.get("name", None),
                                                                                schema_data.get("namespace", current_namespace), 
                                                                                ensure_namespaces_are_equal = False)


        if schema_type == "typeref":
            # Dont store typerefs as new types, just give them an alias into an existing type
            target_type = self.load_from_data(schema_data["ref"], schema_namespace)
            self.type_registry.register_type(schema_fqn, target_type)
            return target_type
        else:
            new_schema.documentation = schema_data.get("doc", "")
            new_schema._fqn = ""
            if schema_name:
                new_schema._fqn = schema_fqn
                # TODO: if a type has already been registered, should we load again?
                new_schema = self.type_registry.register_type(schema_fqn, new_schema)
            self.schema_initializers[schema_type](new_schema, schema_data, self, schema_namespace)
        return new_schema

def fixed_schema_initializer(newtype, schema_data, pegasus_loader, type_namespace):
    newtype.copy_from(tlcore.FixedType(schema_data["size"]))

def bytes_schema_initializer(newtype, schema_data, pegasus_loader, type_namespace):
    newtype.copy_from(tlcore.FixedType(schema_data["size"]))

def union_schema_initializer(newtype, schema_data, pegasus_loader, type_namespace):
    child_types = [pegasus_loader.load_from_data(thetype, type_namespace, newtype, index) for thetype in schema_data]
    newtype.copy_from(tlcore.UnionType(*child_types))

def record_schema_initializer(newtype, schema_data, pegasus_loader, type_namespace):
    name,namespace,fqn = utils.normalize_name_and_ns(schema_data["name"], schema_data.get("namespace", ""))
    newtype.copy_from(tlrecords.RecordType(tlrecords.Record(fqn, newtype, None)))
    newtype.type_data.thetype = newtype
    record_data = newtype.type_data

    for field_dict in schema_data.get("fields", []):
        field_name = field_dict["name"]
        field_docs = field_dict.get("doc", "")
        field_is_optional = field_dict.get("optional", False)
        field_default = field_dict.get("default", None)
        field_annotations = field_dict.get("annotations", None)
        field_type = field_dict.get("type", None)
        if field_type:
            field_type = pegasus_loader.load_from_data(field_type, type_namespace)
        else:
            raise errors.TLException("Field must either have a type")
        newtype.add_child(field_type, field_name, field_docs, field_annotations,
                          tlrecords.FieldData(field_name, newtype, field_is_optional, field_default))

    # Now resolve included models
    for included_model in schema_data.get("include", []):
        print "Loading included model: %s, from: %s" % (included_model, newtype._fqn)
        included_record = pegasus_loader.load_from_data(included_model, type_namespace)
        # add all fields to this record
        for field in included_record.type_data.fields.itervalues():
            # copy the field and set the record to ourselves!
            field = field.copy()
            field.record = newtype
            record_data.add_field(field)

def array_schema_initializer(newtype, schema_data, pegasus_loader, type_namespace):
    newtype.copy_from(tlcore.ListType(pegasus_loader.load_from_data(schema_data["items"], type_namespace)))

def set_schema_initializer(newtype, schema_data, pegasus_loader, type_namespace):
    newtype.copy_from(tlcore.SetType(pegasus_loader.load_from_data(schema_data["items"], type_namespace)))

def map_schema_initializer(newtype, schema_data, pegasus_loader, type_namespace):
    key_type = tlcore.StringType
    if "keys" in schema_data:
        key_type = pegasus_loader.load_from_data(schema_data["keys"], type_namespace)
    value_type = pegasus_loader.load_from_data(schema_data["values"], type_namespace)
    newtype.copy_from(tlcore.MapType(key_type, value_type))

def enum_schema_initializer(newtype, schema_data, pegasus_loader, type_namespace):
    newtype.copy_from(tlenums.EnumType(tlenums.EnumData(schema_data["symbols"])))

def typeref_schema_initializer(newtype, schema_data, pegasus_loader, type_namespace):
    assert False, "Should not be called."

SCHEMA_INITIALIZERS = {
    "fixed": fixed_schema_initializer,
    "bytes": bytes_schema_initializer,
    "record": record_schema_initializer,
    "array": array_schema_initializer,
    "set": set_schema_initializer,
    "map": map_schema_initializer,
    "union": union_schema_initializer,
    "enum": enum_schema_initializer,
    "typeref": typeref_schema_initializer
}
