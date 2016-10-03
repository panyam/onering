

import ipdb
import fnmatch
from typelib import registry 
from onering import resolver
from onering import errors

class OneringContext(object):
    def __init__(self):
        self.type_registry = registry.TypeRegistry()
        self.entity_resolver = resolver.EntityResolver("pdsc")
        self._derivations = {}
        self._functions = {}
        self._transformer_groups = {}

        self.output_dir = "./gen"
        self.platform_aliases = {
            "java": "onering.generator.backends.java.JavaTargetBackend"
        }
        self.template_dirs = []

        from onering.templates import loader as tplloader
        self.template_loader = tplloader.TemplateLoader(self.template_dirs)

    def get_derivation(self, fqn):
        return self._derivations.get(fqn, None)

    @property
    def all_derivations(self):
        return self._derivations.values()


    def register_derivation(self, derivation):
        if derivation.fqn in self._derivations:
            raise errors.OneringException("Duplicate derivation found: %s" % derivation.fqn)
        self._derivations[derivation.fqn] = derivation

    @property
    def all_transformer_groups(self):
        return self._transformer_groups.values()

    def register_transformer_group(self, transformer_group):
        if transformer_group.fqn in self._transformer_groups:
            raise errors.OneringException("Duplicate transformer_group found: %s" % transformer_group.fqn)
        self._transformer_groups[transformer_group.fqn] = transformer_group

    def get_transformer_group(self, fqn):
        return self._transformer_groups.get(fqn, None)

    def find_common_ancestor(self, record1, record2):
        """
        Finds the common ancestor record for two given records (ie a common ancestor record from which 
        both record1 and record2 have transitively derived from).  It is possible that one of the records
        is an ancestor of the other in which case this one is returned.
        """
        # Go through derivation1 and get a list of all parents 
        d1set = set(self.parents_for_type(record1.fqn))

        for d2parent_fqn in self.parents_for_type(record2.fqn):
            if d2parent_fqn in d1set:
                return self.type_registry.get_typeref(d2parent_fqn)
        return None

    def derived_from_type(self, record_fqn):
        """
        Given a fqn of a record, returns the record from this record could have been derived from (if any)
        """
        if record_fqn:
            deriv = self.get_derivation(record_fqn)
            if not deriv or not deriv.has_sources:
                return None
            return self.type_registry.get_typeref(deriv.source_aliases.values()[0])

    def parents_for_type(self, record_fqn):
        """
        Iterates and generates the parents of a given record (including itself)
        """
        while record_fqn:
            yield record_fqn
            record_fqn = self.derived_from_type(record_fqn)
            if record_fqn:
                record_fqn = record_fqn.fqn

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
            # Now resolve all derivations
            for derivation in self.all_derivations:
                if fnmatch.fnmatch(derivation.fqn, tw):
                    source_derivations.add(derivation.fqn)
        return source_derivations

    def transformer_groups_for_wildcards(self, wildcards):
        """
        Return all transformer groups that match any of the given wildcards.
        """
        if type(wildcards) in (str, unicode): wildcards = [wildcards]

        out = set()
        for tw in wildcards:
            # Now resolve all derivations
            for tg in self.all_transformer_groups:
                if fnmatch.fnmatch(tg.fqn, tw):
                    out.add(tg.fqn)
        return out

    def get_function(self, fqn):
        """
        Get a function by its fqn.
        """
        return self._functions[fqn]

    def register_function(self, function):
        """
        Get a function by its fqn.
        """
        if function.fqn in self._functions:
            raise errors.OneringException("Duplicate function found: %s" % function.fqn)
        self._functions[function.fqn] = function
