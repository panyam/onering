
from __future__ import absolute_import
import fnmatch, pprint
import os
from ipdb import set_trace
import json
from onering.utils.misc import collect_files
from onering.utils import dirutils

class Loader(object):
    """ Takes care of loading pegasus schemas. """
    def __init__(self, context, *args, **kwargs):
        """ Instantiates a new Espresso schema loader.

        Arguments:
            List of files (or wildcards of files) to be loaded.

        Keyword Arguments:
            None
        """
        self.context = context
        self.entries = list(args)
        self.found_entities = {}
        self.schema_initializers = {
            "fixed": self.fixed_schema_initializer,
            "bytes": self.bytes_schema_initializer,
            "record": self.record_schema_initializer,
            "array": self.array_schema_initializer,
            "set": self.set_schema_initializer,
            "map": self.map_schema_initializer,
            "union": self.union_schema_initializer,
            "enum": self.enum_schema_initializer,
            "typeref": self.typeref_schema_initializer
        }

    def load(self):
        """
        Loads a type given its fqn or all types at a particular path.
        """
        for entry in self.entries:
            entry_dir = entry["dir"]
            entry_files = entry["files"]
            for f in collect_files(os.path.join(self.context.curdir, entry_dir)):
                if fnmatch.fnmatch(f, entry_files):
                    self.load_from_path(f)
        return self.found_entities

    def load_from_path(self, file_path):
        """
        Reads one or more schemas from the given the absolute path and registers it into the schema registry.
        """
        print("Reading schemas from: %s" % file_path)
        contents = json.loads(open(file_path).read())
        assert contents is not None, "Contents ?"
        return self.load_from_data(contents)

    def load_by_name(self, name, namespace = ""):
        name,namespace,fqn = utils.normalize_name_and_ns(name, namespace, ensure_namespaces_are_equal = False)
        # Search for this type if it doesnt exist so we can resolve from file
        # If the type exists then just return a reference to it
        typeexpr = self.context.global_module.find_fqn(fqn)
        if typeexpr:
            # return tccore.make_ref(fqn)
            return typeexpr
        else:
            typeexpr = self.context.global_module.find_fqn(name)
            if typeexpr:
                return typeexpr
                # return tccore.make_ref(name)

        # otherwise load it from where it is
        contents = self.context.entity_resolver.resolve_schema(fqn, "pdsc", "st")
        if not contents:
            raise errors.TypesNotFoundException(fqn)
        # Now we have a schema dictionary that we can process for its fields etc
        schema = self.load_from_data(contents, namespace)
        """
        if schema.fqn:
            namespace = ".".join(schema.fqn.split(".")[:-1])
            return tccore.make_ref(schema.fqn)
        else:
            set_trace()
            return schema
        """
        return schema

    def load_from_data(self, schema_data, current_namespace = ""):
        if type(schema_data) in (str, unicode):
            name,namespace,fqn = utils.normalize_name_and_ns(schema_data, current_namespace, ensure_namespaces_are_equal = False)
            # Load it up by looking up resolvers
            return self.load_by_name(fqn)
        elif isinstance(schema_data, list):
            # Anonymous Union type so cannot be saved in registry - extract and return as is
            return self.union_schema_initializer(None, schema_data, current_namespace)
        elif not isinstance(schema_data, dict):
            ipdb.set_trace()
            raise Exception("schema_data can only be a string, list or a dictionary")

        # based on type do the load!
        return self._create_new_schema(schema_data, current_namespace)

    def _create_new_schema(self, schema_data, current_namespace = None):
        # It MUST have a type property
        schema_type = schema_data.get("type", None)
        schema_namespace = current_namespace
        if isinstance(schema_type, list):  # Union types
            schema_type = "union"
        else:
            schema_name, schema_namespace, schema_fqn = utils.normalize_name_and_ns(schema_data.get("name", None),
                                                                                    schema_data.get("namespace", current_namespace), 
                                                                                    ensure_namespaces_are_equal = False)

        if schema_type not in self.schema_initializers:
            raise Exception("Invalid type: %s" % schema_type, schema_data)

        assert schema_namespace
        current_module = self.context.ensure_module(schema_namespace)
        newtype = self.schema_initializers[schema_type](schema_fqn, schema_data, schema_namespace)
        newtype.docs = schema_data.get("doc", "")
        if newtype.name:
            newtype.parent = current_module
            current_module.add(newtype.name, newtype)
            self.found_entities[newtype.fqn] = newtype
        return newtype

    def fixed_schema_initializer(self, fqn, schema_data, type_namespace):
        return tccore.FixedType(schema_data["size"])

    def bytes_schema_initializer(self, fqn, schema_data, type_name, type_namespace):
        tccore.FixedType(schema_data["size"])

    def union_schema_initializer(self, fqn, schema_data, type_fqn):
        typeargs = [self.load_from_data(data, type_namespace) for data in schema_data]
        return tccore.make_sum_type("union", type_fqn, typeargs, None)

    def record_schema_initializer(self, fqn, schema_data, type_namespace):
        name,namespace,fqn = utils.normalize_name_and_ns(schema_data["name"], schema_data.get("namespace", ""))
        typeargs = []
        for field_dict in schema_data.get("fields", []):
            field_name = field_dict["name"]
            field_docs = field_dict.get("doc", "")
            field_is_optional = field_dict.get("optional", False)
            field_default = field_dict.get("default", None)
            field_annotations = field_dict.get("annotations", None)
            field_type = field_dict.get("type", None)
            if field_type:
                field_type = self.load_from_data(field_type, type_namespace)
                field_type = tccore.make_ref(field_type.fqn)
            else:
                raise errors.TLException("Field must either have a type")
            typeargs.append(tccore.TypeArg(field_name, field_type, field_is_optional, field_default, field_annotations, field_docs))

        # Now resolve included models
        for included_model in schema_data.get("include", []):
            print "Loading included model: %s, from: %s" % (included_model, fqn)
            included_record = self.load_from_data(included_model, type_namespace)
            if included_record.is_typeref:
                included_record = included_record.final_type
            assert included_record.is_product_type

            # add all fields to this record
            for typearg in included_record.args:
                # copy the field and set the record to ourselves!
                typeargs.append(typearg.deepcopy(None))
        return tccore.make_product_type("record", fqn, typeargs, None)

    def array_schema_initializer(self, fqn, schema_data, type_namespace):
        newtype.copy_from(tccore.ArrayType(self.load_from_data(schema_data["items"], type_namespace)))

    def set_schema_initializer(self, fqn, schema_data, type_namespace):
        newtype.copy_from(tccore.SetType(self.load_from_data(schema_data["items"], type_namespace)))

    def map_schema_initializer(self, fqn, schema_data, type_namespace):
        key_type = tccore.StringType
        if "keys" in schema_data:
            key_type = self.load_from_data(schema_data["keys"], type_namespace)
        value_type = self.load_from_data(schema_data["values"], type_namespace)
        newtype.copy_from(tccore.MapType(key_type, value_type))

    def enum_schema_initializer(self, fqn, schema_data, type_namespace):
        symbolNames = schema_data["symbols"]
        symbolDocs = schema_data["symbolDocs"]
        symbols = [(sym,index,None,doc) for index,(sym,doc) in enumerate(zip(symbolNames, symbolDocs))]
        return tccore.make_enum_type(fqn, symbols, None, None, schema_data.get("docs", ""))

    def typeref_schema_initializer(self, fqn, schema_data, type_namespace):
        current_module = self.context.ensure_module(type_namespace)
        out = self.load_from_data(schema_data["ref"], type_namespace)
        fqn = ".".join([type_namespace, schema_data["name"]])
        alias = tccore.make_alias(fqn, out, current_module, None, schema_data.get("docs", ""))
        return alias
