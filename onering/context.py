
from typelib import registry 
from onering import resolver

class OneringContext(object):
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
            raise errors.TLException("Duplicate derivation found: " % derivation.fqn)
        self._derivations[derivation.fqn] = derivation

    @property
    def all_transformer_groups(self):
        return self._transformer_groups.values()

    def register_transformer_group(self, transformer_group):
        if transformer_group.fqn in self._transformer_groups:
            raise errors.TLException("Duplicate transformer_group found: " % transformer_group.fqn)
        self._transformer_groups[transformer_group.fqn] = transformer_group
