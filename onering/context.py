
from __future__ import absolute_import
import ipdb
from collections import defaultdict
import fnmatch
from typelib import registry 
from typelib import core as tlcore
from onering import resolver
from onering import errors
from onering.utils import dirutils
from onering.core import tgraph
from onering.entities.modules import Module

class OneringContext(dirutils.DirPointer):
    def __init__(self):
        dirutils.DirPointer.__init__(self)
        self.type_registry = registry.TypeRegistry()
        self.entity_resolver = resolver.EntityResolver("pdsc")
        self.global_module = Module(None, None)
        self.tgraph = tgraph.TransformerGraph(self)
        self._derivations = {}
        self._functions = {}
        self._platforms = {}
        self._transformer_groups = {}
        self._interfaces = {}
        self.register_default_types()

        self.output_dir = "./gen"
        self.platform_aliases = {
            "java": "onering.generator.backends.java.JavaTargetBackend"
        }
        self.default_platform = "java"
        self.template_dirs = []

        from onering.templates import loader as tplloader
        self.template_loader = tplloader.TemplateLoader(self.template_dirs)

    def register_default_types(self):
        # register references to default types.
        tlcore.EntityRef(tlcore.AnyType, "any", self.global_module)
        tlcore.EntityRef(tlcore.BooleanType, "boolean", self.global_module)
        tlcore.EntityRef(tlcore.ByteType, "byte", self.global_module)
        tlcore.EntityRef(tlcore.IntType, "int", self.global_module)
        tlcore.EntityRef(tlcore.LongType, "long", self.global_module)
        tlcore.EntityRef(tlcore.FloatType, "float", self.global_module)
        tlcore.EntityRef(tlcore.DoubleType, "double", self.global_module)
        tlcore.EntityRef(tlcore.StringType, "string", self.global_module)

    def ensure_module(self, fqn):
        """ Ensures that a given module hierarchy exists. """
        curr = self.global_module
        parts = fqn.split(".")
        for part in parts:
            if not curr.has_entity(part):
                child = Module(part, curr)
                curr.add_entity(child)
                curr = child
        return curr

    def get_derivation(self, fqn):
        return self._derivations.get(fqn, None)

    @property
    def all_derivations(self):
        return self._derivations.values()


    def register_derivation(self, derivation):
        if derivation.fqn in self._derivations:
            raise errors.OneringException("Duplicate derivation found: %s" % derivation.fqn)
        self._derivations[derivation.fqn] = derivation

    def get_transformer_group(self, fqn):
        return self._transformer_groups.get(fqn, None)

    @property
    def all_transformer_groups(self):
        return self._transformer_groups.values()

    def register_transformer_group(self, transformer_group):
        if transformer_group.fqn in self._transformer_groups:
            raise errors.OneringException("Duplicate transformer_group found: %s" % transformer_group.fqn)
        self._transformer_groups[transformer_group.fqn] = transformer_group

    def get_interface(self, fqn):
        return self._interfaces.get(fqn, None)

    @property
    def all_interfaces(self):
        return self._interfaces.values()

    def register_interface(self, interface):
        if interface.fqn in self._interfaces:
            raise errors.OneringException("Duplicate interface found: %s" % interface.fqn)
        self._interfaces[interface.fqn] = interface

    def derivations_for_wildcards(self, wildcards):
        """
        Return all derivations that match any of the given wildcards.
        """
        if type(wildcards) in (str, unicode): wildcards = [wildcards]
        for tw in wildcards:
            # Now resolve all derivations
            for derivation in self.all_derivations:
                if fnmatch.fnmatch(derivation.fqn, tw):
                    derivation.resolve(self.type_registry, None)

        source_derivations = set()
        for tw in wildcards:
            for derivation in self.all_derivations:
                if fnmatch.fnmatch(derivation.fqn, tw):
                    source_derivations.add(derivation.fqn)
        return source_derivations

    def interfaces_for_wildcards(self, wildcards):
        """
        Return all interfaces that match any of the given wildcards.
        """
        if type(wildcards) in (str, unicode): wildcards = [wildcards]

        out = set()
        for tw in wildcards:
            for tg in self.all_interfaces:
                if fnmatch.fnmatch(tg.fqn, tw):
                    out.add(tg.fqn)
        return out

    def transformer_groups_for_wildcards(self, wildcards):
        """
        Return all transformer groups that match any of the given wildcards.
        """
        if type(wildcards) in (str, unicode): wildcards = [wildcards]

        out = set()
        for tw in wildcards:
            for tg in self.all_transformer_groups:
                if fnmatch.fnmatch(tg.fqn, tw):
                    out.add(tg.fqn)
        return out

    def get_platform(self, name, register = False, annotations = None, docs = ""):
        """
        Get a platform binding container by its name.
        """
        if register:
            if name not in self._platforms:
                from onering.core import platforms
                self._platforms[name] = platforms.Platform(name, annotations, docs)
        return self._platforms[name]

    def get_function(self, fqn, ignore_missing = False):
        """
        Get a function by its fqn.
        """
        if ignore_missing:
            return self._functions.get(fqn, None)
        else:
            return self._functions[fqn]

    def register_function(self, function):
        """
        Get a function by its fqn.
        """
        if function.fqn in self._functions:
            raise errors.OneringException("Duplicate function found: %s" % function.fqn)
        self._functions[function.fqn] = function




    def find_common_ancestor(self, record1, record2):
        """
        Finds the common ancestor record for two given records (ie a common ancestor record from which 
        both record1 and record2 have transitively derived from).  It is possible that one of the records
        is an ancestor of the other in which case this one is returned.
        """
        # Go through derivation1 and get a list of all parents 
        d1list = list(self.parents_for_type(record1.fqn))
        d1set = set(d1list)

        path2 = []
        for index,d2parent_fqn in enumerate(self.parents_for_type(record2.fqn)):
            if d2parent_fqn in d1set:
                path1 = d1list[:d1list.index(d2parent_fqn)]
                path1.reverse() ; path2.reverse()
                ancestor = self.type_registry.get_typeref(d2parent_fqn)
                return ancestor, path1, path2
            else:
                path2.append(d2parent_fqn)
        return None, None, None

    def surviving_fields_from_root_to_child(self, ancestor, path_to_child):
        remaining_fields = dict([(arg.name, [arg]) for arg in ancestor.final_type.args])

        # now as we we go down each derivation for source drop off fields that are 
        # not present in each derivation (when "negation" is implemented this will be richer)
        for fqn in path_to_child:
            curr = self.type_registry.get_typeref(fqn)
            curr_args = curr.final_type.args
            args2 = defaultdict(list)
            for field in curr_args:
                if field.projection is not None and field.projection.field_path_resolution.child_key in remaining_fields:
                    args2[field.projection.field_path_resolution.child_key].append(field)

            # Swap out remaining fields as it may have extraneous fields - also this way "new" fields wont make it through
            remaining_fields = args2

        return remaining_fields 

    def parents_for_type(self, record_fqn):
        """
        Iterates and generates the parents of a given record (including itself)
        """
        while record_fqn:
            yield record_fqn
            record_fqn = self.derived_from_type(record_fqn)
            if record_fqn:
                record_fqn = record_fqn.fqn

    def derived_from_type(self, record_fqn):
        """
        Given a fqn of a record, returns the record from this record could have been derived from (if any)
        """
        if record_fqn:
            deriv = self.get_derivation(record_fqn)
            if not deriv or not deriv.has_sources:
                return None
            return self.type_registry.get_typeref(deriv.source_fqn_at(0))
