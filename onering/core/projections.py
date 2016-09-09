
import ipdb
from onering import errors
from typelib import errors as tlerrors
from typelib import core as tlcore
from typelib import records
from onering.utils import normalize_name_and_ns
from utils import FieldPath

class PathResolver(object):
    """
    An interface that helps in the resolution of a field path.  This is hierarchical in nature.
    """
    def __init__(self, parent_resolver = None):
        self.parent_resolver = parent_resolver

    def resolve_path(self, field_path):
        if field_path.is_absolute:
            # resolve it with reference to this level if we have no other parent
            pass

class ResolutionStatus(object):
    def __init__(self):
        self._resolved = False
        self._resolving = False

    @property
    def succeeded(self):
        return self._resolved

    @property
    def in_progress(self):
        return self._resolving

    def _mark_in_progress(self, value):
        self._resolving = value

    def _mark_resolved(self, value):
        self._resolved = value

    def perform_once(self, action):
        result = None
        if not self._resolved:
            if self._resolving:
                raise errors.OneringException("Action already in progress.   Possible circular dependency found")

            self._resolving = True

            result = action()

            self._resolving = False
            self._resolved = True
        return result

class Projection(object):
    """
    Projection is anything that results in the creation of a type.
    This could be named like a field or a named derived type (like a record, union, enum)
    or an unnamed type like the argument to a type constructor (eg key type of a map)
    """
    def __init__(self):
        self.resolution = ResolutionStatus()

    def resolve(self, type_registry, resolver):
        def resolver_method():
            self._resolve(type_registry, resolver)
        self.resolution.perform_once(resolver_method)


class RecordDerivation(Projection):
    """
    Describes the components of a record derivation.  
    A record derivation can have a source record and field projections.
    Upon resolution, the derivation will have a valid "resolved_record" property
    that will be of type Record.
    """
    def __init__(self, fqn, annotations = None, docs = ""):
        """Creates a new Record derivation.
        Arguments:
            fqn     Fully qualified name of the record.  Records should have names unless they are inline derivations where names will be derived.
        """
        self.annotations = annotations or []
        self.source_aliases = {}
        self.docs = docs or ""
        self.field_projections = []
        self._resolution = ResolutionStatus()
        self.fqn = fqn

    def __repr__(self):
        return "<ID: 0x%x, Name: '%s'>" % (id(self), self.fqn)

    @property
    def resolution(self):
        return self._resolution

    @property
    def name(self):
        return normalize_name_and_ns(self.fqn, "")[0]

    @property
    def namespace(self):
        return normalize_name_and_ns(self.fqn, "")[1]
    
    @property
    def fqn(self):
        return self._fqn
    
    @fqn.setter
    def fqn(self, value):
        self._fqn = value
        self._resolved_record = records.RecordType(None, self.annotations, self.docs)
        self._resolved_record.type_data.fqn = value

    @property
    def resolved_type(self):
        return self._resolved_type

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
        n,ns,fqn = normalize_name_and_ns(source_fqn, None)
        alias = alias or n
        self.source_aliases[alias] = fqn

    def find_source(self, alias):
        """
        Find a source by a given alias.
        """
        return self.source_aliases.get(alias, None)

    @property
    def has_sources(self):
        return self.source_count > 0

    @property
    def source_count(self):
        return len(self.source_aliases)

    def _resolve(self, type_registry, resolver):
        """
        Resolves the derivation by:
            1. Resolving all source fields
            2. Creating a resolver that takes into account the source fields,
            3. Resolving all field projections with the new resolver
        """
        # Step 1
        self._resolve_sources(type_registry)

        # Step 2: TODO - Create the Resolver to take into account this derivation's source record(s) if any (eg in a type stream, the derivation wont have sources)
        if self.source_aliases:
            # TODO - create new resolver
            pass

        # Step 3: Resolve field projections
        self._resolve_projections(type_registry, resolver)

        # Register the type into the registry
        type_registry.register_type(self.fqn, self.resolved_record)

    def _resolve_sources(self, registry):
        unresolved_types = set()
        for (alias,fqn) in self.source_aliases.iteritems():
            source_rec_type = registry.get_type(fqn)
            if source_rec_type is None:
                # TODO - Is this another derivation that needs resolution first?
                ipdb.set_trace()
                unresolved_types.add(fqn)
            elif source_rec_type.is_unresolved:
                source_rec_type.resolve(registry)
                if source_rec_type.is_unresolved:
                    unresolved_types.add(source_rec_ref.record_fqn)

        if len(unresolved_types) > 0:
            raise tlerrors.TypesNotFoundException(*list(unresolved_types))

    def _resolve_projections(self, registry, resolver):
        unresolved_types = set()
        for proj in self.field_projections:
            try:
                proj.resolve(registry, resolver)
            except tlerrors.TypesNotFoundException, exc:
                unresolved_types.add(exc.missing_types)

        if len(unresolved_types) > 0:
            raise tlerrors.TypesNotFoundException(*list(unresolved_types))

        # otherwise all of these are resolved so create our field list from these
        for proj in self.field_projections:
            for field in proj.projected_fields:
                self.resolved_record.add_child(field.field_type, field.field_name,
                                             field.docs, field.annotations,
                                             records.FieldData(field.field_name,
                                                               self.resolved_record,
                                                               field.is_optional,
                                                               field.default_value))

class FieldProjection(Projection):
    """
    A projection that simply takes a source field and returns it as is with a possibly new type.
    """
    def __init__(self, parent_derivation, source_field_path):
        super(FieldProjection, self).__init__()

        # Every field projection needs a source field path that it derives from
        self._source_field_path = source_field_path

        self._parent_derivation = parent_derivation

        self._resolved_fields = []

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
        if not resolution.succeeded:
            raise errors.OneringException("Resolution has not completed yet")
        return self._resolved_fields


    def _resolve(self, registry, resolver):
        """
        Resolves a projection.  This should be implemented by child projection 
        types.
        """
        self._starting_record, self._final_field_data, self._final_field_path = resolver.resolve_path(self.source_field_path)

        # Let child classes handle this
        if not self._final_field_data:
            self._final_field_data_not_found()
        else:
            self._final_field_data_found()

    def _final_field_data_not_found(self):
        """
        Called after the intial field path resolution and if final field data was not found.
        """
        raise errors.OneringException("Final data was not found for field path (%s).  Possible new field" % self.source_field_path)


    def _final_field_data_found(self):
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


class SingleFieldProjection(FieldProjection):
    """
    Base class of all projections that deal with single source fields.
    """
    def __init__(self, parent_derivation, source_field_path):
        super(SingleFieldProjection, self).__init__(parent_derivation, source_field_path)

        # Whether the field that is projected is optional,
        # None => inherit from source field path
        self.is_optional = None

        # Whether the field that is projected has a default value
        self.default_value = None

        # The new name of the field after the projection
        self.projected_name = None

    @property
    def projected_default_value(self):
        default_value = None
        if self.default_value is not None:
            return self.default_value

        if self._final_field_data:
            if self._final_field_data.default_value is not None:
                return self._final_field_data.default_value
        return None

class SimpleFieldProjection(SingleFieldProjection):
    """
    A simple projection that maps a single field path into a single target type.
    """
    def __init__(self, parent_derivation, source_field_path, projected_type = None):
        super(SimpleFieldProjection, self).__init__(parent_derivation, source_field_path)
        self._projected_type = projected_type

        if projected_type and not isinstance(projected_type, tlcore.Type):
            raise errors.OneringException("Projected type must be a Type instance")

    @property
    def projected_type(self):
        return self._projected_type

    def _final_field_data_not_found(self):
        """
        Called after the intial field path resolution and if final field data was not found.
        """
        # Means we are creating a "new" field so there
        # must not be a projected name and there MUST be a type
        if self.projected_name is not None:
            raise errors.OneringException("New Field '%s' in '%s' should not have a target_name" % (self.source_field_path, self.parent_derivation.type_data.fqn))
        elif self.projected_type is None:
            raise errors.OneringException("New Field '%s' in '%s' does not have a target_type" % (self.source_field_path, self.parent_derivation.type_data.fqn))
        elif self.source_field_path.length > 1:
            raise errors.OneringException("New Field '%s' in '%s' must not be a field path" % (self.source_field_path, self.parent_derivation.type_data.fqn))
        else:
            newfield = Field(self.source_field_path.get(0),
                             self.projected_type,
                             self.parent_derivation,
                             self.is_optional,
                             self.default_value,
                             "",
                             self.annotations)
            self._add_field(newfield)


    def _final_field_data_found(self):
        """
        Called after the intial field path resolution and if final field data was found.
        """
        final_field_data = self._final_field_data
        projected_type = self.projected_type or final_field_data.field_type

        # Assign target_type name from parent and field name if it is missing
        _auto_generate_projected_type_name(registry, projected_type,
                                           parent_derivation, final_field_data)

        newfield = Field(self.projected_name or final_field_data.field_name,
                         projected_type,
                         self.parent_entity,
                         self.projected_is_optional,
                         self.projected_default_value,
                         final_field_data.docs,
                         self.annotations or final_field_data.annotations)
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


    def _final_field_data_found(self):
        """
        Called after the intial field path resolution and if final field data was found.
        """
        final_field_data = self._final_field_data
        projected_type = self.projected_type or final_field_data.field_type

        # Assign target_type name from parent and field name if it is missing
        _auto_generate_projected_type_name(registry, projected_type, parent_derivation, final_field_data)

        newfield = Field(self.projected_name or final_field_data.field_name,
                         projected_type,
                         self.parent_entity,
                         is_optional,
                         default_value,
                         final_field_data.docs,
                         self.annotations or final_field_data.annotations)
        self._add_field(newfield)
        

class TypeStream(SingleFieldProjection):
    """
    A type of field projection that results in container types being created.
    """
    def __init__(self, parent_derivation, source_field_path, param_names, constructor_fqn, children):
        """
        Creates a type stream projection.
        The children could be either projections or derivations (which will result in records).
        """
        super(TypeStream, self).__init__(parent_derivation, source_field_path)
        self.constructor = constructor_fqn
        self.param_names = param_names or []
        self.projections = children


    def _final_field_data_found(self):
        """
        Called after the intial field path resolution and if final field data was found.
        """
        raise errors.OneringException("Not implemented")


class MultiFieldProjection(FieldProjection):
    """
    A field projection that picks multiple fields.
    """
    def __init__(self, parent_derivation, source_field_path):
        super(MultiFieldProjection, self).__init__(parent_derivation, source_field_path)
        if not source_field_path.has_children:
            raise errors.OneringException("Field path must have children for a multi field projection.  Use a SingleFieldProject derivative instead.")

    def _final_field_data_not_found(self):
        """
        Called after the intial field path resolution and if final field data was not found.
        """
        if self.field_path.length == 0 and self._starting_record != None:
            # then we are starting from the root itself of the starting record 
            # as "multiple" entries
            self._include_child_fields(self._starting_record)
        else:
            raise errors.OneringException("New Field '%s' must not have child selections" % self.source_field_path)

    def _final_field_data_found(self):
        """
        Called after the intial field path resolution and if final field data was not found.
        """
        self._include_child_fields(self._final_field_data.field_type)

    def _include_child_fields(self, starting_record):
        """
        Add all fields starting from the starting_record indexed by the
        source_field_path.
        """
        if not self.source_field_path.all_fields_selected:
            missing_fields = set(self.source_field_path.selected_children) - set(starting_record.child_names)
            if len(missing_fields) > 0:
                raise errors.OneringException("Invalid fields in selection: '%s'" % ", ".join(list(missing_fields)))
        selected_fields = self.source_field_path.get_selected_fields(starting_record)
        for field_name in selected_fields:
            newfield = Field(field_name,
                             starting_record.child_type_for(field_name),
                             self.parent_entity,
                             starting_record.child_data_for(field_name).is_optional,
                             starting_record.child_data_for(field_name).default_value,
                             starting_record.docs_for(field_name),
                             starting_record.annotations_for(field_name))
            self._add_field(newfield)



def _auto_generate_projected_type_name(registry, projected_type, parent_derivation, final_field_data):
    if projected_type and projected_type.fqn is None and parent_derivation:
        parent_fqn = parent_derivation.fqn
        field_name = final_field_data.field_name
        parent_name,ns,parent_fqn = normalize_name_and_ns(parent_fqn, None)
        projected_type.type_data.fqn = parent_fqn + "_" + field_name
        assert projected_type.type_data.parent_entity is not None
        if final_field_data:
            if final_field_data.field_type.constructor != "record" or not final_field_data.field_type.type_data:
                raise errors.OneringException("'%s' is not of a record type but is being using in a mutation for field '%s'" % (final_field_data.field_type.fqn, field_name))

            projected_type.type_data.add_source(final_field_data.field_type.type_data.fqn, final_field_data.field_type)
        if not projected_type.resolve(registry):
            raise errors.OneringException("Could not resolve record mutation for field '%s' in record '%s'" % (field_name, parent_fqn))
