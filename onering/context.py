

import ipdb
from typelib import registry 
from onering import resolver
from onering import errors

class OneringContext(object):
    def __init__(self):
        self.type_registry = registry.TypeRegistry()
        self.entity_resolver = resolver.EntityResolver("pdsc")
        self._derivations = {}
        self._transformer_groups = {}

        self.output_dir = "./gen"
        self.platform_aliases = {
            "java": "onering.backends.java.JavaTargetBackend"
        }
        self.template_dirs = []

        from onering.templates import loader as tplloader
        self.template_loader = tplloader.TemplateLoader(self.template_dirs)

    def get_transformer_group(self, fqn):
        return self._transformer_groups.get(fqn, None)

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


    def find_common_ancestor(self, record1, record2):
        """
        Finds the common ancestor record for two given records (ie a common ancestor record from which 
        both record1 and record2 have transitively derived from).  It is possible that one of the records
        is an ancestor of the other in which case this one is returned.
        """
        derivation1 = self.get_derivation(record1.fqn)
        derivation2 = self.get_derivation(record2.fqn)
        if derivation1 is None and derivation2 is None:
            return None
        ipdb.set_trace()

        return None
