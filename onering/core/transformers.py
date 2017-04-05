
from __future__ import absolute_import
import ipdb
from enum import Enum
from onering import errors
from onering.utils import ResolutionStatus
from onering.core.utils import FieldPath
from onering.core import exprs as orexprs
from onering.core.projections import SimpleFieldProjection
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
        self._function_refs = set()

    def __repr__(self):
        return "<TG - ID: 0x%x, FQN: %s>" % (id(self), self.fqn)

    @property
    def all_transformers(self):
        return iter(self._transformers)

    @property
    def function_references(self):
        return self._function_refs

    def add_function_ref(self, func_fqn):
        self._function_refs.add(func_fqn)

    def add_transformer(self, transformer):
        if transformer.fqn in self._transformer_names:
            raise errors.OneringException("Duplicate transformer found: " % transformer.fqn)
        self._transformer_names.add(transformer.fqn)
        self._transformers.append(transformer)

    def resolve(self, context):
        """Kicks of resolutions of all dependencies.
        
        This must only be called after all derivations that produce records
        have been resolved otherwise those records that are only derived will not be visible in the type_registry.
        """
        for transformer in self._transformers:
            transformer.resolve(context)

class Transformer(Annotatable):
    """
    Transformers define how an instance of one type can be transformed to an instance of another.
    """
    def __init__(self, fqn, source_variables, dest_fqn, dest_varname = None, group = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.resolution = ResolutionStatus()
        self.fqn = fqn
        self.src_varnames = [src_varname if src_varname else "src%d" % index for (index,(src_fqn,src_varname)) in enumerate(source_variables)]
        self.src_fqns = [src_fqn for (src_fqn,src_varname) in source_variables]
        self.dest_varname = dest_varname or "dest"
        self.dest_fqn = dest_fqn
        self.group = group
        self.temp_variables = {}
        # explicit transformer rules
        self._implicit_statements = []
        self._explicit_statements = []

        # Keeps track of the counts of each type of auto-generated variable.
        self._vartable = {}

    def __repr__(self):
        return "<Transformer - ID: 0x%x, Name: %s (%s -> %s)>" % (id(self), self.fqn, ",".join(self.src_fqns), self.dest_fqn)

    def local_variables(self, yield_src = True, yield_dest = True, yield_locals = True):
        if yield_src:
            for src_varname, src_typeref in self.source_variables:
                yield src_varname, src_typeref, orexprs.VarSource.SOURCE
        if yield_dest:
            yield self.dest_varname, self.dest_typeref, orexprs.VarSource.DEST
        if yield_locals:
            for vname, vtype in self.temp_variables.iteritems():
                yield vname, vtype, orexprs.VarSource.LOCAL

    def is_temp_variable(self, varname):
        return varname in self.temp_variables

    def temp_var_type(self, varname):
        return self.temp_variables[str(varname)]

    def register_temp_var(self, varname, vartype):
        assert type(varname) in (str, unicode)
        if varname in self.src_varnames:
            raise errors.OneringException("Duplicate temporary variable '%s'.  Same as source." % varname)
        elif varname == self.dest_varname:
            raise errors.OneringException("Duplicate temporary variable '%s'.  Same as target." % varname)
        elif self.is_temp_variable(varname) and self.temp_variables[varname] is not None:
            raise errors.OneringException("Duplicate temporary variable declared: '%s'" % varname)
        self.temp_variables[varname] = vartype

    @property
    def source_variables(self):
        from itertools import izip
        return izip(self.src_varnames, self.src_typerefs)

    @property
    def all_statements(self):
        return self._implicit_statements + self._explicit_statements

    def add_statement(self, stmt):
        if not isinstance(stmt, orexprs.Statement):
            raise errors.OneringException("Transformer rule must be a let statement or a statement, Found: %s" % str(type(stmt)))
        # Check types and variables in the statements
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
        self.src_typerefs = map(type_registry.get_typeref, self.src_fqns)
        self.dest_typeref = type_registry.get_typeref(self.dest_fqn)

        # First make sure we have implicit rules taken from the derivations if any
        self._implicit_statements = self._evaluate_implicit_statements(context)

        # Now resolve all field paths appropriately
        for index,statement in enumerate(self.all_statements):
            statement.resolve_bindings_and_types(self, context)

    def _evaluate_implicit_statements(self, context):
        """
        Given the source and dest types, evaluates all "get/set" rules that can be 
        inferred for shared types.   This is only possible if both src and dest types 
        share a common ancestor (or may be even at atmost 1 level).
        """

        if len(self.src_typerefs) > 1:
            # TODO - Checking for implicit statements when more than one sources are given requires 
            # that the "sources" of dest are all the ones provided here.  This is the case where
            # in the derivation itself a record derivation from more than one model
            ipdb.set_trace()
            return []

        implicit_statements = []
        # Step 1: Find common "ancestor" of each of the records
        ancestor, path1, path2 = context.find_common_ancestor(self.src_typerefs[0], self.dest_typeref)
        if ancestor is not None:
            # Here see which fields from the root still exist in the leaf (even if it has been retyped or renamed or streamed).
            remaining_fields1 = context.surviving_fields_from_root_to_child(ancestor, path1)
            remaining_fields2 = context.surviving_fields_from_root_to_child(ancestor, path2)

            # At this point:
            # RF1 contains all field that have gone from ancestor to src type
            # RF2 contains all field that have gone from ancestor to dest type
            # The fields of interest will be the intersection of these two
            src_fields = {key : value for (key,value) in remaining_fields1.iteritems() if key in remaining_fields2}
            dest_fields = {key : value for (key,value) in remaining_fields2.iteritems() if key in remaining_fields1}

            # Now the fun begins
            # It could be that a field in src maps to multiplel fields in dest
            # Here we can do a couple of things.
            # 1. Ignore all projections in src and dest types that are anything but simple renaming of fields and use only those
            # 2. Use "same" types from src and dest, mapping those and use each unique src type to map to equivalent ones in dest.
            #    Later is a lot more work and value is limited - so ignore for now
            for sfield_name, sfields in src_fields.iteritems():
                # find any field in src_field that is a simple mapping (ie only renaming allowed at most)
                source_field = None
                for sfield in sfields:
                    if type(sfield.projection) is SimpleFieldProjection and sfield.projection.projected_typeref is None:
                        source_field = sfield
                        break

                if source_field:
                    # we have a source field (that was derived from ancestor without any transformation) so it is
                    # a good candidate to copy from.  
                    #
                    # Now look for all destination fields this can be mapped and add implicit rules for these
                    dfields = dest_fields[sfield_name]
                    for dfield in dfields:
                        if type(dfield.projection) is SimpleFieldProjection and dfield.projection.projected_typeref is None:
                            src_field_path = FieldPath([source_field.field_name])
                            dest_field_path = FieldPath([dfield.field_name])
                            src_var = orexprs.VariableExpression(src_field_path, readonly = True, source_type = orexprs.VarSource.AUTO)
                            dest_var = orexprs.VariableExpression(dest_field_path, readonly = False, source_type = orexprs.VarSource.AUTO)
                            new_stmt = orexprs.Statement(self, [src_var], dest_var)
                            new_stmt.is_implicit = True
                            implicit_statements.append(new_stmt)
        return implicit_statements
