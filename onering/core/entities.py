
from collections import defaultdict
import ipdb
from typelib import errors as tlerrors
from typelib.annotations import Annotatable

class Entity(Annotatable):
    """Base class of all onering entities."""
    def __init__(self, name, parent = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self._name = name
        self._parent = parent 
        self.entity_map = {}
        self._symbol_refs = {}
        self.child_entities = []
        self.aliases = {}

    def set_tag(self, tag):
        self.tag = tag
        return self

    def set_alias(self, name, fqn):
        """Sets the alias of a particular name to an FQN."""
        self.aliases[name] = self.add_symbol_ref(fqn)
        return self

    @property
    def tag(self): return self.__class__.TAG 

    @tag.setter
    def tag(self, value): self.TAG = value

    @property
    def fqn(self):
        out = self.name
        if self.parent and self.parent.fqn:
            if out is None:
                ipdb.set_trace()
            out = self.parent.fqn + "." + out
        return out or ""

    def add_symbol_ref(self, fqn):
        if fqn not in self._symbol_refs:
            # Ensure symbol refs dont have a parent as they are not bound to the parent but
            # to some arbitrary scope that is using them to refer to the FQN
            self._symbol_refs[fqn] = SymbolRef(fqn)
        return self._symbol_refs[fqn]

    def add(self, name, entity):
        """ Adds a new child entity. """
        assert name and name not in self.entity_map, "Entity '%s' already exists" % name
        self.entity_map[name] = entity
        self.child_entities.append(entity)

    def get(self, fqn_or_parts):
        """ Given a list of key path parts, tries to resolve the descendant entity that matchies this part prefix. """
        parts = fqn_or_parts
        if type(fqn_or_parts) in (unicode, str):
            parts = fqn_or_parts.split(".")
        curr = self
        for part in parts:
            if part not in curr.entity_map:
                return None
            curr = curr.entity_map[part]
        return curr

    def find_fqn(self, fqn):
        """Looks for a FQN in either the aliases or child entities or recursively in the parent."""
        out = None
        curr = self
        while curr and not out:
            out = curr.aliases.get(fqn, None)
            if not out:
                out = curr.get(fqn)
            if not out:
                curr = curr.parent
        return out

    def ensure_key(self, fqn_or_name_or_parts):
        """Ensures that a descendant hierarchy of Entities or EntityRefs exists given the key path parts."""
        parts = fqn_or_name_or_parts
        if type(parts) in (str, unicode):
            parts = parts.split(".")
        curr = self
        for part in parts:
            if part not in curr.entity_map:
                curr.entity_map[part] = EntityRef(None, part, parent = curr)
            curr = curr.entity_map[part]
        return curr

    def resolve_binding(self, typeref):
        from resolver import resolve_entity
        return resolve_entity(typeref, self)

    @property
    def name(self): return self._name

    @property
    def parent(self): return self._parent

    """
    @name.setter
    def name(self, value):
        self._set_name(value)

    def _set_name(self, value):
        self._name = value
    """

class EntityRef(Entity):
    """
    A named reference to an entity.
    """
    TAG = "REF"
    def __init__(self, entry, name, parent, annotations = None, docs = ""):
        Entity.__init__(self, name, parent, annotations, docs)
        if name and type(name) not in (str, unicode):
            ipdb.set_trace()
            assert False, "Name for an reference must be string or none"

        self._categorise_target(entry)
        self._target = entry

    def __json__(self, **kwargs):
        target = self._target.__json__(**kwargs) if self._target else None
        out = {}
        if kwargs.get("include_docs", False) and self.docs:
            out["docs"] = self.docs
        if self.name:
            # return self.name
            out["name"] = self.name
        elif target and len(target) > 0:
            return target
            # out["target"] = target
        return out

    def _categorise_target(self, entry):
        self._is_ref = issubclass(entry.__class__, EntityRef)
        self._is_entity = isinstance(entry, Entity)
        if not (self._is_entity or self._is_ref or entry is None):
            ipdb.set_trace()
            assert False, "Referred target must be a Entity or a EntityRef or None"
        return entry

    @property
    def is_unresolved(self):
        return self._target is None

    @property
    def is_resolved(self):
        return self._target is not None

    @property
    def is_reference(self):
        return self._is_ref

    @property
    def is_entity(self):
        return self._is_entity

    @property
    def last_unresolved(self):
        curr = self
        while curr.target:
            curr = curr.target
            if not issubclass(curr.__class__, EntityRef): return None
        return curr

    @property
    def target(self):
        return self._target

    @property
    def first_entity(self):
        """
        Return the first type in this chain that is an actual entity and not an entity ref.
        """
        curr = self._target
        while curr and not issubclass(curr.__class__, EntityRef):
            curr = curr._target
        return curr

    @property
    def final_entity(self):
        """
        The final type transitively referenced by this ref.
        """
        # TODO - Memoize the result
        curr = self._target
        while curr and issubclass(curr.__class__, EntityRef):
            curr = curr._target
        return curr

    @target.setter
    def target(self, newentity):
        self._categorise_target(newentity)
        self.set_target(newentity)

    def set_target(self, newentity):
        # TODO - Check for cyclic references
        self._target = newentity

class SymbolRef(EntityRef):
    TAG = "SYM"
    def __init__(self, fqn):
        EntityRef.__init__(self, None, fqn, None)

    @property
    def fqn(self):
        return self.name

class Module(Entity):
    TAG = "MODULE"
