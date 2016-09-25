
import ipdb
from enum import Enum
from onering import errors
from onering.utils import ResolutionStatus
from onering.core.utils import FieldPath
from onering.core import exprs as orexprs
from typelib.annotations import Annotatable

class TransformerGroup(Annotatable):
    """
    A transformer group enables a set of transformers to be logically grouped.  This group and its
    data are available for all transformers within this group.   The group also determins how the
    """
    def __init__(self, fqn, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.fqn = fqn
        self._transformer_names = set()
        self._transformers = []

    def __repr__(self):
        return "<TG - ID: 0x%x, FQN: %s>" % (id(self), self.fqn)

    @property
    def all_transformers(self):
        return self._transformers[:]

    def add_transformer(self, transformer):
        if transformer.fqn in self._transformer_names:
            raise errors.OneringException("Duplicate transformer found: " % transformer.fqn)
        self._transformer_names.add(transformer.fqn)
        self._transformers.append(transformer)

    def resolve(self, context):
        """
        Kicks of resolutions of all dependencies.  This must only be called after all derivations that produce records
        have been resolved otherwise those records that are only derived will not be visible in the type_registry.
        """
        for transformer in self._transformers:
            transformer.resolve(context)

class Transformer(Annotatable):
    """
    Transformers define how an instance of one type can be transformed to an instance of another.
    """
    def __init__(self, fqn, src_fqn, dest_fqn, group = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.resolution = ResolutionStatus()
        self.fqn = fqn
        self.src_fqn = src_fqn
        self.dest_fqn = dest_fqn
        self.group = group
        self.temp_var_names = set()
        # explicit transformer rules
        self._implicit_statements = []
        self._explicit_statements = []

        # Keeps track of the counts of each type of auto-generated variable.
        self._vartable = {}

    def __repr__(self):
        return "<Transformer - ID: 0x%x, Name: %s (%s -> %s)>" % (id(self), self.fqn, self.src_fqn, self.dest_fqn)

    def is_temp_variable(self, varname):
        return varname in self.temp_var_names

    @property
    def all_statements(self):
        return self._implicit_statements + self._explicit_statements

    def add_statement(self, stmt):
        if not isinstance(stmt, orexprs.Statement):
            raise errors.OneringException("Transformer rule must be a let statement or a statement, Found: %s" % str(type(stmt)))
        if stmt.is_temporary:
            varname = stmt.target_variable.value
            if self.is_temp_variable(varname):
                raise errors.OneringException("Duplicate temporary variable declared: '%s'" % varname)
            self.temp_var_names.add(varname)
        self._explicit_statements.append(stmt)


    def resolve(self, context):
        """
        Kicks of resolutions of all dependencies.  This must only be called after all derivations that produce records
        have been resolved otherwise those records that are only derived will not be visible in the type_registry.
        """
        def resolver_method():
            self._resolve(context)
        self.resolution.perform_once(resolver_method)


    def _resolve(self, context):
        """
        The main resolver method.  This should take care of the following:

            1. Ensure field paths are correct
            2. All expressions have their evaluated types set
        """
        type_registry = context.type_registry
        self.src_typeref = type_registry.get_typeref(self.src_fqn)
        self.dest_typeref = type_registry.get_typeref(self.dest_fqn)

        # First make sure we have implicit rules taken from the derivations if any
        self._implicit_statements = self._evaluate_implicit_statements(context)

        # Now resolve all field paths appropriately
        for statement in self.all_statements:
            statement.resolve_types(self, context)

    def _evaluate_implicit_statements(self, context):
        """
        Given the source and dest types, evaluates all "get/set" rules that can be 
        inferred for shared types.   This is only possible if both src and dest types 
        share a common ancestor (or may be even at atmost 1 level).
        """

        return []

        # Step 1: Find common "ancestor" of each of the records
        ancestor = context.find_common_ancestor(self.src_typeref, self.dest_typeref)
        if ancestor is not None:
            # If the two types have no common ancestor then we cannot have auto rules
            pass

            # Variables are "locations" - a location is either a temp variable, or a (record + field_path)
            # Expressions are functions of locations:
            #   Function(multiple locations) results in locations being set
            #   Compound blocks are a collection of expressions that also get/set variables at a function scope
        return []

