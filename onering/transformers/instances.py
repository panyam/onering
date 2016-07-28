
from onering import datatypes
from onering import fields
from onering import mapper
from onering import utils
from onering import errors
from itertools import izip
import os, json

# When a mapper is not specified in the instance transformer, the source field is copied
# as is to the target field.  This requires that:
# 
# 1. There is a single sourceField
# 2. The sourceField and targetField types are the same.
DEFAULT_FIELD_TRANSFORMER = "transformers.Copier"

class Rule(object):
    def __init__(self, sourceFields, targetField, mapper = None):
        self.target_field_path = fields.FieldPath(targetField)
        self.source_field_paths = map(fields.FieldPath, sourceFields)
        self.mapper = mapper or DEFAULT_FIELD_TRANSFORMER

    def copy(self):
        newrule = Rule(self.source_field_paths, self.target_field_path, self.mapper)
        newrule.index = -1
        newrule.sourceFields = None
        newrule.targetField = None
        return newrule

    def resolve_fields(self, sourceType, targetType):
        # now field spec could be of the form: a.b.c  (or a.b[X].c) and so on
        # In this case this is really equivalent to if the dev had a custom rule
        # for the type of B explicitly but since we want to simplify this we can
        # evaluate this instead of forcing the dev to specify multiple transformers
        # at each level
        self.source_fields = map(sourceType.resolve_field_from_path, self.source_field_paths)
        self.target_field = targetType.resolve_field_from_path(self.target_field_path)

class InstanceTransformer(object):
    """
    Instance transformers convert an instance of one schema to the instance of another.
    """
    def load_schema_from_data(self, transformer_dict, schema_registry):
        self.source_name, self.source_namespace, self.source_fqn = utils.normalize_name_and_ns(transformer_dict.get("source", None),
                                                                                       transformer_dict.get("namespace", ""),
                                                                                       ensure_namespaces_are_equal = False)
        self.target_name, self.target_namespace, self.target_fqn = utils.normalize_name_and_ns(transformer_dict.get("target", None),
                                                                                       transformer_dict.get("namespace", ""),
                                                                                       ensure_namespaces_are_equal = False)
        self.name, self.namespace, self.fqn = utils.normalize_name_and_ns(transformer_dict.get("name", None),
                                                                                 transformer_dict.get("namespace", ""),
                                                                                 ensure_namespaces_are_equal = False)
        self.source_type = schema_registry.get_schema(self.source_fqn)
        self.target_type = schema_registry.get_schema(self.target_fqn)
        self.includes = transformer_dict.get("include", [])
        self.rules = []
        ruleCount = 0

        for transformer_name in self.includes:
            # Note these can be included models *or* transformers
            transformer = schema_registry.get_schema(transformer_name, registry.SCHEMA_CLASS_IT)
            for rule in transformer.rules:
                newrule = rule.copy()
                newrule.index = ruleCount
                ruleCount += 1
                self.rules.extend(transformer.rules)

        for index,rule in enumerate(transformer_dict.get("rules", [])):
            sourceFields = []
            if "sourceFields" in rule:
                sourceFields = rule["sourceFields"]
            elif "sourceField" in rule:
                sourceFields = [rule["sourceField"]]
            mapper = rule.get("mapper", None)
            if len(sourceFields) > 1:
                if not mapper:
                    raise errors.OneringException("A mapper MUST be specified when multiple source fields are used in a rule")
            newrule = Rule(sourceFields, rule["targetField"], mapper)
            newrule.index = ruleCount
            ruleCount += 1
            self.rules.append(newrule)

    def is_anonymous(self):
        return not self.source_fqn or not self.target_fqn

    def apply(self, onering):
        schema_registry = onering.schema_registry
        field_graph = onering.field_graph
        # Step 1: First load the source and target types - these MUST exist otherwise 
        # we are possibly missing out on fields or do an invalid transformation
        print "Transformer Source, Targe Types: ", self.source_type.fqn, self.target_type.fqn

        # now go through the rules and update extra dependency edges
        for rule in self.rules:
            rule.resolve_fields(self.source_type, self.target_type)
            for source_field in rule.source_fields:
                # add an edge!
                field_graph.add_field_edge(source_field, rule.target_field, self.fqn)

