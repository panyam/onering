
from __future__ import absolute_import
import sys
import ipdb
from onering import errors
from typelib import errors as tlerrors
from typelib import core as tlcore
from typelib.annotations import Annotatable
from typelib import records
from onering.utils import FQN, ResolutionStatus
from onering.core.utils import FieldPath

class Projection(Annotatable):
    """
    Projection is anything that results in the creation of a type.
    This could be named like a field or a named derived type (like a record, union, enum)
    or an unnamed type like the argument to a type constructor (eg key type of a map)
    """
    def __init__(self, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.resolution = ResolutionStatus()

    def resolve(self, type_registry, resolver):
        def resolver_method():
            self._resolve(type_registry, resolver)
        self.resolution.perform_once(resolver_method)

    @property
    def resolved_typerefs(self):
        raise Exception("Not yet implemented")


class RecordDerivation(Projection):
    """
    Describes the components of a record derivation.  
    A record derivation can have a source record and field projections.
    Upon resolution, the derivation will have a valid "resolved_recordref" property
    that will be of type Record.
    """
    def __init__(self, fqn, annotations = None, docs = ""):
        """Creates a new Record derivation.
        Arguments:
            fqn     Fully qualified name of the record.  Records should have names unless they are inline derivations where names will be derived.
        """
        super(RecordDerivation, self).__init__(annotations, docs)
        self.source_aliases = {}
        self.source_types = {}
        self.field_projections = []
        self.fqn = fqn
        self._resolved_recordref = None

    def __json__(self):
        out = super(RecordDerivation, self).__json__()
        out["fqn"] = self.fqn
        return out

    @property
    def name(self):
        return FQN(self.fqn, "").name

    @property
    def namespace(self):
        return FQN(self.fqn, "").namespace
    
    @property
    def fqn(self):
        return self._fqn
    
    @fqn.setter
    def fqn(self, value):
        self._fqn = value

    @property
    def resolved_typerefs(self):
        return [self.resolved_recordref]

    @property
    def resolved_recordref(self):
        return self._resolved_recordref

    def add_projection(self, projection):
        """
        Add a field projection.
        """
        self._resolved = False
        self.field_projections.append(projection)

    def add_source(self, source_fqn, alias = None):
        """
        Add a new source record that this record derives from.
        """
        fqn = FQN(source_fqn, None)
        alias = alias or fqn.name
        self.source_aliases[alias] = fqn.fqn

    def has_source(self, source_fqn):
        return source_fqn in self.source_aliases.values()

    @property
    def has_sources(self):
        return self.source_count > 0

    @property
    def source_count(self):
        return len(self.source_aliases)

    def _resolve(self, type_registry, resolver):
        """
        Resolves the derivation by:
            1. Register a new type ref as whether the FQN was provided by user or auto generated,
               it should not be registered until resolution begins.
            2. Resolving all source fields
            3. Creating a resolver that takes into account the source fields,
            4. Resolving all field projections with the new resolver
        """
        # Step 1: Register a new record type for the FQN
        if not self.fqn:
            ipdb.set_trace()
            assert False
        self._resolved_recordref = type_registry.register_type(self.fqn, records.RecordType(None, self.annotations, self.docs))

        # Step 2
        self._resolve_sources(type_registry)

        # Step 3: TODO - Create the Resolver to take into account this derivation's source record(s) if any (eg in a type stream, the derivation wont have sources)
        if self.source_aliases:
            # TODO - create new resolver
            from onering.core.resolvers import DerivationPathResolver
            resolver = DerivationPathResolver(resolver, self, type_registry)
        else:
            pass

        # Step 4: Resolve field projections
        self._resolve_projections(type_registry, resolver)


    def _resolve_sources(self, registry):
        unresolved_types = set()
        for (alias,fqn) in self.source_aliases.iteritems():
            source_rec_typeref = registry.get_typeref(fqn)
            if source_rec_typeref is None:
                # TODO - Is this another derivation that needs resolution first?
                ipdb.set_trace()
                unresolved_types.add(fqn)
            elif source_rec_typeref.is_unresolved:
                unresolved_types.add(source_rec_ref.record_fqn)
            else:
                # save resolved type
                self.source_types[alias] = source_rec_typeref

        if len(unresolved_types) > 0:
            raise tlerrors.TypesNotFoundException(*list(unresolved_types))

    def _resolve_projections(self, registry, resolver):
        unresolved_types = set()
        for proj in self.field_projections:
            try:
                proj.resolve(registry, resolver)
            except tlerrors.TypesNotFoundException, exc:
                ipdb.set_trace()
                unresolved_types.add(exc.missing_types)

        if len(unresolved_types) > 0:
            raise tlerrors.TypesNotFoundException(*list(unresolved_types))

        # otherwise all of these are resolved so create our field list from these
        for proj in self.field_projections:
            for field in proj.projected_fields:
                self.resolved_recordref.final_type.add_arg(field)

class FieldProjection(Projection):
    """
    A projection that simply takes a source field and returns it as is with a possibly new type.
    """
    def __init__(self, parent_derivation, source_field_path, annotations = None, docs = ""):
        super(FieldProjection, self).__init__(annotations, docs)

        # Every field projection needs a source field path that it derives from
        self._source_field_path = source_field_path

        self._parent_derivation = parent_derivation

        self._resolved_fields = []
        self.field_path_resolution = None

    def __json__(self):
        out = super(FieldProjection, self).__json__()
        out["src"] = repr(self.source_field_path)
        return out

    @property
    def resolved_typerefs(self):
        return [f.typeref for f in self._resolved_fields]

    @property
    def source_field_path(self):
        return self._source_field_path

    @property
    def parent_derivation(self):
        """
        Return the derivation into which this projection belongs.
        If null then this projection belongs in an anonymous projection
        as an argument for a type constructor.
        """
        return self._parent_derivation


    @property
    def projected_fields(self):
        """
        Return the list of fields returned as part of the resolution process
        """
        if not self.resolution.succeeded:
            raise errors.OneringException("Resolution has not completed yet")
        return self._resolved_fields


    def _resolve(self, registry, resolver):
        """
        Resolves a projection.  This should be implemented by child projection 
        types.
        """
        # if str(self.source_field_path) == "name": ipdb.set_trace()
        self.field_path_resolution = resolver.resolve_path(self._source_field_path)

        # Let child classes handle this
        if not self.field_path_resolution or not self.field_path_resolution.is_valid:
            self._field_path_resolution_failed()
        else:
            self._field_path_resolved(registry, resolver)

    def _field_path_resolution_failed(self):
        """
        Called after the intial field path resolution and if final field data was not found.
        """
        raise errors.OneringException("Final data was not found for field path (%s).  Possible new field" % self.source_field_path)


    def _field_path_resolved(self, registry, resolver):
        """
        Called after the intial field path resolution and if final field data was found.
        """
        raise errors.OneringException("Not implemented")


    def _add_field(self, newfield):
        """
        Adds a new field to the list of resolved fields.
        Should only be called by child classes as projections are resolved
        and result in new fields
        """
        self._resolved_fields.append(newfield)

    def _include_child_fields(self, starting_type, field_path):
        """
        Add all fields starting from the starting_type indexed by the
        source_field_path.
        """
        if not field_path.all_fields_selected:
            field_names = [a.name for a in starting_type.args]
            missing_fields = set(field_path.selected_children) - set(field_names)
            if len(missing_fields) > 0:
                raise errors.OneringException("Invalid fields in selection: '%s'" % ", ".join(list(missing_fields)))

        selected_fields = field_path.get_selected_fields(starting_type)
        for field_name in selected_fields:
            arg = starting_type.arg_for(field_name)
            newfield = Field(field_name,
                             starting_type.arg_for(field_name).typeref,
                             projection = self,
                             field_path = self.source_field_path.with_child(field_name),
                             is_optional = arg.is_optional,
                             default_value = arg.default_value,
                             docs = arg.docs,
                             annotations = arg.annotations)
            self._add_field(newfield)



def _auto_generate_projected_typeref_name(registry, derivation_or_typeref, parent_derivation, field_path_resolution):
    if derivation_or_typeref and parent_derivation:
        if derivation_or_typeref.fqn is None:
            parent_fqn = parent_derivation.fqn
            field_name = field_path_resolution.field_name
            parent_fqn = FQN(parent_fqn, None).fqn
            derivation_or_typeref.fqn = parent_fqn + "_" + field_name


class SingleFieldProjection(FieldProjection):
    """
    Base class of all projections that deal with single source fields.
    """
    def __init__(self, parent_derivation, source_field_path, annotations = None, docs = ""):
        super(SingleFieldProjection, self).__init__(parent_derivation, source_field_path, annotations, docs)

        # Whether the field that is projected is optional,
        # None => inherit from source field path
        self.is_optional = None

        # Whether the field that is projected has a default value
        self.default_value = None

        # The new name of the field after the projection
        self.projected_name = None

    @property
    def projected_is_optional(self):
        if self.is_optional is not None:
            return self.is_optional

        if self.field_path_resolution.parent_type.constructor == "record":
            key = self.field_path_resolution.child_key
            child_data = self.field_path_resolution.parent_type.arg_for(key)
            if child_data.is_optional is not None:
                return child_data.is_optional
        return None

    @property
    def projected_default_value(self):
        default_value = None
        if self.default_value is not None:
            return self.default_value

        if self.field_path_resolution.parent_type.constructor == "record":
            key = self.field_path_resolution.child_key
            child_data = self.field_path_resolution.parent_type.arg_for(key)
            if child_data.default_value is not None:
                return child_data.default_value
        return None


class SimpleFieldProjection(SingleFieldProjection):
    """
    A simple projection that maps a single field path into a single target type.
    """
    def __init__(self, parent_derivation, source_field_path, projected_typeref = None):
        super(SimpleFieldProjection, self).__init__(parent_derivation, source_field_path)
        self._projected_typeref = projected_typeref

        if projected_typeref and not isinstance(projected_typeref, tlcore.TypeRef):
            raise errors.OneringException("Projected type must be a TypeRef instance")

    def __json__(self):
        out = super(SimpleFieldProjection, self).__json__()
        if self.projected_typeref:
            out["ptype"] = self.projected_typeref.json()
        return out

    @property
    def projected_typeref(self):
        return self._projected_typeref

    def _field_path_resolution_failed(self):
        """
        Called after the intial field path resolution and if final field data was not found.
        """
        # Means we are creating a "new" field so there
        # must not be a projected name and there MUST be a type
        if self.projected_name is not None:
            raise errors.OneringException("New Field '%s' in '%s' should not have a target_name" % (self.source_field_path, self.parent_derivation.fqn))
        elif self.projected_typeref is None:
            if self.source_field_path.is_absolute:
                raise errors.OneringException("Projection '%s' (for new field) in '%s' cannot be absolute" % (self.source_field_path, self.parent_derivation.resolved_record.fqn))
            else:
                raise errors.OneringException("New Field '%s' in '%s' does not have a target_type" % (self.source_field_path, self.parent_derivation.fqn))
        elif self.source_field_path.length > 1:
            raise errors.OneringException("New Field '%s' in '%s' must not be a field path" % (self.source_field_path, self.parent_derivation.fqn))
        else:
            newfield = Field(self.source_field_path.get(0),
                             self.projected_typeref,
                             projection = self,
                             field_path = self.source_field_path,
                             is_optional = self.is_optional,
                             default_value = self.default_value,
                             docs = "",
                             annotations = self.annotations)
            self._add_field(newfield)


    def _field_path_resolved(self, registry, resolver):
        """
        Called after the intial field path resolution and if final field data was found.
        """
        # If the projected name is new record that is unnamed then give it an autogenerated name
        _auto_generate_projected_typeref_name(registry, self.projected_typeref,
                                              self.parent_derivation, self.field_path_resolution)

        if self.projected_typeref and self.projected_typeref.is_unresolved:
            # TODO: Dont do anything here as even though the projected type is unresolved
            # It is only being referenced and not dereferenced.  Only fail on an unresolved
            # type if it is being unpacked for its fields.
            print >> sys.stderr, "Unresolved Type: "
            print >> sys.stderr,  self.projected_typeref

        projected_typeref = self.projected_typeref or self.field_path_resolution.resolved_typeref

        newfield = Field(self.projected_name or self.field_path_resolution.field_name,
                         projected_typeref,
                         projection = self,
                         field_path = self.source_field_path,
                         is_optional = self.projected_is_optional,
                         default_value = self.projected_default_value,
                         docs = self.field_path_resolution.docs,
                         annotations = self.annotations or self.field_path_resolution.annotations)
        self._add_field(newfield)

class InlineDerivation(SingleFieldProjection):
    """
    A type of field projection that results in a new record being derived.
    """
    def __init__(self, parent_derivation, source_field_path, derivation):
        super(InlineDerivation, self).__init__(parent_derivation, source_field_path)
        self.child_derivation = derivation
        if derivation is None or not isinstance(derivation, RecordDerivation):
            raise errors.OneringException("derivation must be of type Derivation")

    def __json__(self):
        out = super(InlineDerivation, self).__json__()
        out["target"] = self.child_derivation.json()
        return out

    def _field_path_resolved(self, registry, resolver):
        """
        Called after the intial field path resolution and if final field data was found.
        """
        # If the inline derivation is unnamed then give it a generated name
        _auto_generate_projected_typeref_name(registry, self.child_derivation,
                                              self.parent_derivation, self.field_path_resolution)

        # Resolve the child derivation here, but first make sure the child derivation has 
        # a source set that is the same as the type of the source field!
        source_fqn = self.field_path_resolution.resolved_typeref.fqn
        if not self.child_derivation.has_source(source_fqn):
            self.child_derivation.add_source(source_fqn)

        self.child_derivation.resolve(registry, resolver)

        newfield = Field(self.projected_name or self.field_path_resolution.field_name,
                         self.child_derivation.resolved_recordref,
                         projection = self,
                         field_path = self.source_field_path,
                         is_optional = self.projected_is_optional,
                         default_value = self.projected_default_value,
                         docs = self.field_path_resolution.docs,
                         annotations = self.annotations or self.field_path_resolution.annotations)
        self._add_field(newfield)
        

class TypeStream(SingleFieldProjection):
    """
    A type of field projection that results in container types being created.
    """
    def __init__(self, parent_derivation, source_field_path, param_names, constructor_fqn, children, annotations = None, docs = ""):
        """
        Creates a type stream projection.
        The children could be either projections or derivations (which will result in records).
        """
        super(TypeStream, self).__init__(parent_derivation, source_field_path, annotations, docs)
        self.constructor = constructor_fqn
        self.param_names = param_names or []
        self.child_projections = children


    def _field_path_resolved(self, registry, resolver):
        """
        Called after the intial field path resolution and if final field data was found.
        """
        if self.param_names:
            from onering.core.resolvers import TypeStreamPathResolver
            resolver = TypeStreamPathResolver(resolver, self, registry)
        else:
            ipdb.set_trace()

        # TODO: Check if the source type can actually be streamed?
        # Hacky way is to see if it is a map or array or set (or a specific monadic type)
        # But this needs to be generalized so we dont end up checking every type

        parent_fqn = self.parent_derivation.fqn
        field_name = self.projected_name or self.field_path_resolution.field_name
        for index,proj in enumerate(self.child_projections):
            if type(proj) is RecordDerivation and not proj.fqn:
                # If we have a derivation as a child then it will have to be provided a name.
                # A way to get a unique name deterministically is by:
                # parent_record + projected_field_name + param_index
                proj.fqn = "%s_%s_%d" % (parent_fqn, field_name, index)
            proj.resolve(registry, resolver)
            # each resolution should have exactly 1 resolved field
            if len(proj.resolved_typerefs) != 1:
                raise errors.OneringException("Exactly one resolved type must be present in the arguments of a constructor to a type stream.")

        # Now we create the field that is of the type of the constructor provided to us
        type_args = [cp.resolved_typerefs[0] for cp in self.child_projections]
        field_typeref = tlcore.TypeRef(tlcore.Type(None, self.constructor, type_args), None)

        newfield = Field(self.projected_name or self.field_path_resolution.field_name,
                         field_typeref,
                         projection = self,
                         field_path = self.source_field_path,
                         is_optional = self.projected_is_optional,
                         default_value = self.projected_default_value,
                         docs = self.field_path_resolution.docs,
                         annotations = self.annotations or self.field_path_resolution.annotations)
        self._add_field(newfield)


class MultiFieldProjection(FieldProjection):
    """
    A field projection that picks multiple fields.
    """
    def __init__(self, parent_derivation, source_field_path, annotations = None, docs = ""):
        super(MultiFieldProjection, self).__init__(parent_derivation, source_field_path, annotations, docs)
        if not source_field_path.has_children:
            raise errors.OneringException("Field path must have children for a multi field projection.  Use a SingleFieldProject derivative instead.")

    def _field_path_resolution_failed(self):
        """
        Called after the intial field path resolution and if final field data was not found.
        """
        if self.source_field_path.length == 0 and self.field_path_resolution.parent_type != None:
            # then we are starting from the root itself of the starting record 
            # as "multiple" entries
            self._include_child_fields(self.field_path_resolution.parent_type, self.source_field_path)
        else:
            raise errors.OneringException("New Field '%s' must not have child selections" % self.source_field_path)

    def _field_path_resolved(self, registry, resolver):
        """
        Called after the intial field path resolution and if final field data was not found.
        """
        self._include_child_fields(self.field_path_resolution.resolved_typeref.final_type, self.source_field_path)

    def __repr__(self):
        return "<MultiFieldProjection ID: 0x%x, Path: '%s'>" % (id(self), self.source_field_path)


class Field(records.FieldTypeArg):
    """
    Holds all information about a field within a record.
    """
    def __init__(self, name, field_typeref, field_path, projection,
                 is_optional = False, default_value = None, docs = "", annotations = None):
        """
        Creates a new Field as the result of a projection.

        Parameters:

            name            -   Name of the field to be created
            field_type      -   Type of the field to be created
            field_path      -   If the field is a result of a projection then this stores the field path (either relative or absolute)
            projection      -   The projection with which this Field is being created
            optional        -   Whether the field is optional
            default         -   Whether the field has a default value
            docs            -   Documentation for the field
            annotations     -   Extra annotations for the field.
        """
        records.FieldTypeArg.__init__(self, name, field_typeref, is_optional, default_value, annotations, docs)
        assert not field_path.has_children, "Field path of a single derived field cannot have children"
        assert projection is not None
        self.field_path = field_path
        self.projection = projection

    def __json__(self):
        out = super(Field, self).__json__()
        out["fpath"] = repr(self.field_path)
        return out
