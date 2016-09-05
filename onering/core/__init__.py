
from typelib import registry 
from onering import resolver
from onering import errors

class Onering(object):
    def __init__(self):
        self.type_registry = registry.TypeRegistry()
        self.entity_resolver = resolver.EntityResolver("pdsc")
        self._derivations = {}
        self._transformer_groups = {}

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
