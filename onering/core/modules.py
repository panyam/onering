
from collections import defaultdict
import ipdb
from typecube import errors as tlerrors
from typecube import core as tlcore
from typecube.annotations import Annotatable

class Module(Annotatable, tlcore.NameResolver):
    def __init__(self, name, parent = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self._name = name
        self._parent = parent 
        self.entity_map = {}
        self.child_entities = []
        self.aliases = {}

    def set_alias(self, name, fqn):
        """Sets the alias of a particular name to an FQN."""
        self.aliases[name] = fqn
        return self

    @property
    def fqn(self):
        out = self.name
        if self.parent and self.parent.fqn:
            if out is None:
                ipdb.set_trace()
            out = self.parent.fqn + "." + out
        return out or ""

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

    def _resolve_name(self, name, condition = None):
        # TODO - handle conditions here
        entry = self.find_fqn(name)
        while entry and type(entry) in (str, unicode):
            entry = self.find_fqn(entry)
        return entry

    def add(self, name, entity):
        """ Adds a new child entity. """
        assert name and name not in self.entity_map, "Child entity '%s' already exists" % name
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

    @property
    def name(self): return self._name

    @property
    def parent(self): return self._parent

    def __json__(self, **kwargs):
        out = {}
        if self.fqn:
            # return self.name
            out["fqn"] = self.fqn
        return out

    def ensure_parents(self):
        for entity in self.entity_map.itervalues():
            if type(entity) is Module:
                entity._parent = self
            else:
                entity.parent = self
            entity.ensure_parents()

    def debug_show(self, level = 0):
        print ("  " * (level)) + "Module:"
        print ("  " * (level + 1)) + "Children:"
        for key,value in self.entity_map.iteritems():
            print ("  " * (level + 2)) + ("%s: %s" % (key, value))
        print ("  " * (level + 1)) + "Aliases:"
        for key,value in self.aliases.iteritems():
            print ("  " * (level + 2)) + ("%s: %s" % (key, value))
