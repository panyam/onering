
import utils
import errors
import core
import ipdb
import records

def is_derivation(obj):
    return type(obj) is Derivation

class Derivation(object):
    class SourceRecordRef(object):
        def __init__(self, record_fqn, record_type, alias):
            self.record_fqn = record_fqn
            self.alias = alias
            self.record_type = record_type

        def __repr__(self):
            return str(self)

        def __str__(self):
            return "<ID: 0x%x, %s as %s>" % (id(self), self.record_fqn, self.alias)

    def __init__(self, fqn, parent_entity, annotations = None, docs = ""):
        """Creates a new Record declaration.
        Arguments:
            fqn                     --  Fully qualified name of the record.  Records should have names.
            parent_entity           --  The parent record or projection inside which this record is declared 
                                        (as an inner declaration)
                                        If this is not provided then this record is being defined independantly 
                                        at the top level.
            field_projections       --  List of projections that describe field declarations.
        """
        self.annotations = annotations or []
        self.docs = docs or ""
        self.field_projections = []
        self.source_records = []
        self._resolved = True
        self._parent_entity = parent_entity
        self.fqn = fqn

    @property
    def name(self):
        return utils.normalize_name_and_ns(self.fqn, "")[0]

    @property
    def namespace(self):
        return utils.normalize_name_and_ns(self.fqn, "")[1]
    
    @property
    def fqn(self):
        return self._fqn
    
    @fqn.setter
    def fqn(self, value):
        self._fqn = value
        self._resolved_type = records.RecordType(None, self.annotations, self.docs)
        self._resolved_type.type_data.fqn = value

    @property
    def parent_entity(self):
        return self._parent_entity

    def __repr__(self):
        return "<ID: 0x%x, Name: '%s'>" % (id(self), self.fqn)

    @property
    def root_record(self):
        if self.parent_entity is None:
            return self
        if type(self.parent_entity) is core.Type:
            return self.parent_entity.type_data.root_record
        else:
            return self.parent_entity.root_record

    def get_binding(self, field_path):
        """
        Gets a particular binding by a given name.  For a record this will be a field name within this record.
        """
        name = field_path.get(0)
        if self.resolved_type.contains(name):
            return self.resolved_type, field_path
        return None, None

    def add_projection(self, projection):
        """
        Add a projection.
        """
        self._resolved = False
        self.field_projections.append(projection)

    def add_source_record(self, source_fqn, source_type, alias = None):
        """
        Add a new source record that this record derives from.
        """
        n,ns,fqn = utils.normalize_name_and_ns(source_fqn, None)
        alias = alias or n
        if self.find_source(alias) is not None:
            raise errors.TLException("A source by name '%s' already exists" % n)
        self.source_records.append(Derivation.SourceRecordRef(source_fqn, source_type, alias))

    def find_source(self, name):
        """
        Find a source by a given name.
        """
        for source_rec_ref in self.source_records:
            if source_rec_ref.alias == alias:
                return source_rec_ref.record_fqn
        return None

    @property
    def has_sources(self):
        return self.source_count > 0

    @property
    def source_count(self):
        return len(self.source_records)

    @property 
    def is_resolved(self):
        return self._resolved

    @property
    def resolved_type(self):
        return self._resolved_type

    def resolve(self, registry):
        """
        Tries to resolve all dependencies for this record.

        Resolution does the following:

            1. First check if registry has all the sources.  If any of the sources are missing 
               an UnresolvedType exception is thrown.
            2. 
        """
        # Step 1: Check if source records are resolved and if they are then throw unresolved types exception if sources are missing
        self._resolve_sources(registry)

        # Step 2: Now go through declarations and resolve into fields
        self._resolve_projections(registry)

        registry.register_type(self.fqn, self.resolved_type)

        self._resolved = True
        return True

    def _resolve_sources(self, registry):
        unresolved_types = set()
        for source_rec_ref in self.source_records:
            if source_rec_ref.record_type is None or source_rec_ref.record_type.is_unresolved:
                source_rec_type = registry.get_type(source_rec_ref.record_fqn)
                if source_rec_type is None:
                    unresolved_types.add(source_rec_ref.record_fqn)
                elif source_rec_type.is_unresolved:
                    source_rec_type.resolve(registry)
                    if source_rec_type.is_unresolved:
                        unresolved_types.add(source_rec_ref.record_fqn)
                else:
                    source_rec_ref.record_type = source_rec_type

        if len(unresolved_types) > 0:
            raise errors.TypesNotFoundException(*list(unresolved_types))

    def _resolve_projections(self, registry):
        unresolved_types = set()
        for proj in self.field_projections:
            try:
                proj.resolve(registry)
            except errors.TypesNotFoundException, exc:
                unresolved_types.add(exc.missing_types)

        if len(unresolved_types) > 0:
            raise errors.TypesNotFoundException(*list(unresolved_types))

        # otherwise all of these are resolved so create our field list from these
        for proj in self.field_projections:
            for field in proj.resolved_fields:
                self.resolved_type.add_child(field.field_type, field.field_name,
                                             field.docs, field.annotations,
                                             records.FieldData(field.field_name, self.resolved_type,
                                                               field.is_optional, field.default_value))


class FieldPath(object):
    def __init__(self, parts, selected_children = None):
        """
        Arguments:
        parts               --  The list of components denoting the field path.   If the first value is an empty 
                                string, then the field path indicates an absolute path.
        selected_children   --  The list of child fields that are selected in a single sweep.  If this field is 
                                specified then is_optional, default_value, target_name, and target_type are ignored 
                                and MUST NOT be specified.  If this value is the string "*" then ALL children all
                                selected.  When this is specified, the source field MUST be of a record type.
        """
        self.inverted = False
        parts = parts or []
        if type(parts) in (str, unicode):
            parts = parts.strip()
            parts = parts.split("/")
        self._parts = parts
        self.selected_children = selected_children or None

    def __repr__(self): 
        return str(self)

    def __str__(self):
        if self.all_fields_selected:
            return "%s/*" % "/".join(self._parts)
        elif self.has_children:
            return "%s/(%s)" % ("/".join(self._parts), ", ".join(self.selected_children))
        else:
            return "/".join(self._parts)

    @property
    def length(self):
        if self.is_absolute:
            return len(self._parts) - 1
        else:
            return len(self._parts)

    def get(self, index):
        """
        Gets the field path part at a given index taking into account whether the path is absolute or not.
        """
        if self.is_absolute:
            index += 1
        return self._parts[index]

    @property
    def is_blank(self):
        return len(self._parts) == 0

    @property
    def is_absolute(self):
        if len(self._parts) == 0:
            ipdb.set_trace()
        return self._parts[0] == ""

    @property
    def has_children(self):
        return self.selected_children is not None

    @property
    def all_fields_selected(self):
        return self.selected_children == "*"

    def get_selected_fields(self, starting_record):
        """
        Given a source field, return all child fields as per the selected_fields spec.
        """
        if self.all_fields_selected:
            return starting_record.child_names
        else:
            return [n for n in starting_record.child_names if n in self.selected_children]


PROJECTION_TYPE_PLAIN       = 0
PROJECTION_TYPE_RETYPE      = 1
PROJECTION_TYPE_MUTATION    = 2
PROJECTION_TYPE_STREAMING   = 3

class Projection(object):
    """
    Projections are a way of declaring a dependencies between fields in a record.
    """
    def __init__(self, parent_entity, field_path, target_name, target_type, annotations):
        """Creates a projection.
        Arguments:
        field_path      --  A FieldPath instance that contains the field path to the source field as well 
                            as any child field selectors if any.
        target_name     --  Specifies whether the field projected from the source path is to be renamed.  
                            If None then the same name as the source field path is used.
        target_type     --  Specifies whether the field is to be re-typed in the destination record.
        is_optional     --  Whether the field is optional.  
                                If True/False field is optional or required.
                                If None then this value is derived from the source field.
        default_value   --  Default value of the field.  If None, then the value is the default_value 
                            of the source field.
        """
        # Two issues to consider:
        # 1. Matter of scopes - ie how variables names or names in general are bound to?  Should scopes just be 
        #    dicts or should we have "scope providers" where records and projections all participate?
        # 2. Should any kind of type change just be a function that creates a new type given the current
        #    lexical scope?
        if field_path is None or field_path.is_blank:
            field_path = None
        self.field_path = field_path
        self.target_name = target_name
        self._resolved_type = None
        self.is_optional = None
        self.default_value = None
        self.target_type = target_type
        self.projection_type = PROJECTION_TYPE_PLAIN
        if target_type:
            self.projection_type = PROJECTION_TYPE_RETYPE
        self.annotations = annotations or []
        self.resolved_fields = []
        self._resolved = False
        self._parent_entity = parent_entity
        self.path_resolver = PathResolver(parent_entity)

    def __repr__(self):
        out = "<Proj, ID: 0x%x, Type: %d" % (id(self), self.projection_type)
        if self.field_path:
            out += ", Source: %s" % self.field_path
        out += ">"
        return out

    @property
    def parent_entity(self):
        return self._parent_entity

    @property
    def root_record(self):
        if type(self.parent_entity) is Projection:
            return self.parent_entity.root_record
        else:
            # must be a derivation otherwise
            return self.parent_entity.root_record

    def get_binding(self, field_path):
        """
        Gets a particular binding by a given name.  For a projection, this is the parameter
        by the given name if the projection type is streaming otherwise if the projection
        type is a mutation then the resolved value is the type of the field within the 
        record (from the source).
        """
        if self.projection_type == PROJECTION_TYPE_MUTATION:
            # Not much you can do with a type mutation as it has no bindings
            pass
        elif self.projection_type == PROJECTION_TYPE_STREAMING:
            assert self.target_type is not None
            first_part = field_path.get(0)
            for index,param in enumerate(self.target_type.param_names):
                if param == first_part:
                    type_arg = self.final_field_data.field_type.child_type_at(index)
                    return type_arg, FieldPath(field_path._parts[1:], field_path.selected_children)
        else:
            # Other projection types should NOT be called for bindings resolutions
            assert False
        return None, None

    @property
    def is_resolved(self):
        return self._resolved

    @property
    def resolved_type(self):
        if self.projection_type == PROJECTION_TYPE_STREAMING:
            assert type(self._resolved_type) is core.Type
            return self._resolved_type
        elif type(self.target_type) is core.Type:
            return self.target_type
        elif self.target_type:
            assert is_derivation(self.target_type)
            return self.target_type.resolved_type
        elif self.final_field_data:
            assert type(self.final_field_data.field_type) is core.Type
            return self.final_field_data.field_type
        else:
            assert False

    def resolve(self, registry):
        """
        Resolution of a projection is where the magic happens.  By the end of it the following need to fall in place:

            1. New fields must be created for each projection with name, type, optionality, default values (if any) set.
            2. MOST importantly, for every generated field that is not a new field (ie is projected from an existing 
               field in *some other* record), a dependency must be marked so that when given an instance of the 
               "source type" the target type can also be populated.  The second part is tricky.  How this dependency 
               is generated and stored requires the idea of scopes and bindings.   This is also especially trickier when 
               dealing with type streaming as scopes need to be created in each iteration of a stream.

        Resolution only deals with creation of all mutated records (including within type streams).  
        No field dependencies are generated yet.   This can be done in the next pass (and may not even be required
        since the projection data can be stored as part of the fields).
        """
        if self.is_resolved:
            return True

        if self.field_path and self.field_path.selected_children is not None:
            assert self.target_name is None and \
                   self.target_type is None and     \
                   self.is_optional is None and     \
                   self.default_value is None,     \
                   "When selected_children is specified, target_type, target_name, default_value and is_optional must all be None"

        self.final_field_data = None
        self.starting_record = None

        if self.field_path:
            self.resolve_source_fields(registry)

            # ensure that all the resolved fields have their types resolved otherwise 
            # we cannot load those types
            for resolved_field in self.resolved_fields:
                resolved_field.field_type.resolve(registry)
                if not resolved_field.field_type.is_resolved:
                    ipdb.set_trace()
                    raise errors.TLException("Unable to resolve type of field: %s.%s" % (resolved_field.record.fqn, resolved_field.field_name))

            final_field_data = self.final_field_data
            starting_record = self.starting_record
            # Once fields are created, check for the streaming and other field type constraints
            # If there are binding params, see whether the number match the final_field_data.field_type's type args
            if self.target_type and self.projection_type == PROJECTION_TYPE_STREAMING:
                if len(self.target_type.param_names) != final_field_data.field_type.arglimit:
                    raise errors.TLException("Number of streamed arguments does not match argument count of type")

        # Now that the source field has been resolved, we can start resolving target type for
        # mutations and streamings
        self.resolve_target(registry)

        self._resolved = True
        return self.is_resolved

    def resolve_source_fields(self, registry):
        # Find the source field given the field path and the parent record
        # This should give us the field that will be copied to here.
        self.starting_record, self.final_field_data, self.final_field_path = self.path_resolver.resolve_path(self, registry)

        print "Resolving FieldPath: ", self.field_path
        if self.final_field_data:
            final_field_data = self.final_field_data
            if self.field_path.has_children:
                self._include_child_fields(final_field_data.field_type)
            else:
                target_type = final_field_data.field_type
                is_optional = final_field_data.is_optional
                default_value = final_field_data.default_value

                if isinstance(self.target_type, core.Type):
                    target_type = self.target_type
                elif self._resolved_type is not None:
                    target_type = self.target_type
                else:
                    # defer field type selection to after target has been resolved
                    pass

                if self.is_optional:
                    is_optional = self.is_optional
                if self.default_value:
                    default_value = self.default_value

                # Assign target_type name from parent and field name if it is missing
                if target_type and target_type.fqn is None and target_type.constructor == "record":
                    parent_fqn = self.parent_entity.fqn
                    field_name = self.final_field_data.field_name
                    parent_name,ns,parent_fqn = utils.normalize_name_and_ns(parent_fqn, None)
                    self.target_type.type_data.fqn = parent_fqn + "_" + field_name
                    assert self.target_type.type_data.parent_entity is not None
                    if final_field_data:
                        if final_field_data.field_type.constructor != "record" or not final_field_data.field_type.type_data:
                            raise errors.TLException("'%s' is not of a record type but is being using in a mutation for field '%s'" % (final_field_data.field_type.fqn, field_name))
                        self.target_type.type_data.add_source_record(final_field_data.field_type.type_data.fqn, final_field_data.field_type)
                    if not self.target_type.resolve(registry):
                        raise errors.TLException("Could not resolve record mutation for field '%s' in record '%s'" % (field_name, parent_fqn))

                newfield = Field(self.target_name or self.final_field_data.field_name,
                                 target_type,
                                 self.parent_entity,
                                 is_optional,
                                 default_value,
                                 self.final_field_data.docs,
                                 self.annotations or self.final_field_data.annotations)
                self._add_field(newfield)
        else:
            starting_record = self.starting_record
            # The Interesting case.  source field could not be found or resolved.
            # There is a chance that this is a "new" field.  That will only be the case if field path has a single entry
            # and target name is not provided and we are not a type stream
            if self.field_path.has_children:
                if self.field_path.length == 0 and starting_record != None:
                    # then we are starting from the root itself of the starting record as "multiple" entries
                    self._include_child_fields(starting_record)
                else:
                    raise errors.TLException("New Field '%s' in '%s' must not have child selections" % (self.field_path, self.parent_entity.type_data.fqn))
            elif self.target_name is not None:
                raise errors.TLException("New Field '%s' in '%s' should not have a target_name" % (self.field_path, self.parent_entity.type_data.fqn))
            elif self.target_type is None:
                ipdb.set_trace()
                raise errors.TLException("New Field '%s' in '%s' does not have a target_type" % (self.field_path, self.parent_entity.type_data.fqn))
            elif self.field_path.length > 1:
                raise errors.TLException("New Field '%s' in '%s' must not be a field path" % (self.field_path, self.parent_entity.type_data.fqn))
            else:
                newfield = Field(self.field_path.get(0),
                                        self.target_type,
                                        self.parent_entity,
                                        self.is_optional if self.is_optional is not None else False,
                                        self.default_value,
                                        "",
                                        self.annotations)
                self._add_field(newfield)

    def resolve_target(self, registry):
        field_path = self.field_path
        final_field_data = self.final_field_data
        parent_entity = self.parent_entity

        if self.projection_type == PROJECTION_TYPE_MUTATION:
            if self.target_type is None:
                raise errors.TLException("Record MUST be specified on a mutation")

            if field_path and field_path.has_children or len(self.resolved_fields) > 1:
                raise errors.TLException("Record mutation cannot be applied when selecting multiple fields")

            # The parent fqn is required because the new record name is based on that.
            # The projection can be in two forms:
            if is_derivation(parent_entity):
                # 1. Inside a record or another type
                parent_fqn = parent_entity.fqn
            else:
                # 2. Inside another projection - ie within a type streaming declaration
                assert parent_entity.projection_type == PROJECTION_TYPE_STREAMING
                assert is_derivation(parent_entity.parent_entity)
                field_name = parent_entity.target_name or parent_entity.final_field_data.field_name
                parent_fqn = parent_entity.parent_entity.fqn + "_" + field_name

            if not parent_fqn:
                # Parent name MUST be set otherwise it means parent resolution would have failed!
                raise errors.TLException("Parent record name not set.  May be it is not yet resolved?")

            if self.resolved_fields:
                field_name = self.resolved_fields[0].field_name
                if not field_name:
                    raise errors.TLException("Source field name is not set.  May be it is not yet resolved?")

                field_type = self.resolved_fields[0].field_type
                if not field_type:
                    raise errors.TLException("Source field name is not set.  May be it is not yet resolved?")

                if field_type.constructor != "record":
                    raise errors.TLException("Cannot mutate a type that is not a record.  Yet")
            else:
                assert self.parent_entity.projection_type == PROJECTION_TYPE_STREAMING
                proj_index = parent_entity.target_type.projections.index(self)
                field_name = "_ta__%d" % proj_index

            if is_derivation(self.target_type) and self.target_type.fqn is None:
                # Should we ever be here?
                parent_name,ns,parent_fqn = utils.normalize_name_and_ns(parent_fqn, None)
                self.target_type.fqn = parent_fqn + "_" + field_name
                assert self.target_type.parent_entity is not None
                if final_field_data:
                    if not final_field_data.field_type.type_data:
                        ipdb.set_trace()
                    self.target_type.add_source_record(final_field_data.field_type.type_data.fqn, final_field_data.field_type)
                if not self.target_type.resolve(registry):
                    raise errors.TLException("Could not resolve record mutation for field '%s' in record '%s'" % (field_name, parent_fqn))
        elif self.projection_type == PROJECTION_TYPE_STREAMING:
            # Here we have to resolve target of the streamed type.
            # Do this by resolving each of the projections into a child type and create a constructed
            # type with these child types as the arguments.

            # TODO: Investigate what "hints" can be added to this projection that directly refers to child entries
            #       that can be used to do getters/setters
            for index,proj in enumerate(self.target_type.projections):
                # if index == 0: ipdb.set_trace()
                proj.resolve(registry)
            child_types = [ proj.resolved_type for proj in self.target_type.projections ]

            # TODO: register new type constructors by names so we can delegate validations on child types to domains 
            # or as extensions
            self._resolved_type = core.Type(self.target_type.constructor, child_types)

    def _add_field(self, newfield):
        self.resolved_fields.append(newfield)

    def _include_child_fields(self, starting_record):
        if not self.field_path.all_fields_selected:
            missing_fields = set(self.field_path.selected_children) - set(starting_record.child_names)
            if len(missing_fields) > 0:
                raise errors.TLException("Invalid fields in selection: '%s'" % ", ".join(list(missing_fields)))
        selected_fields = self.field_path.get_selected_fields(starting_record)
        for field_name in selected_fields:
            newfield = Field(field_name,
                             starting_record.child_type_for(field_name),
                             self.parent_entity,
                             starting_record.child_data_for(field_name).is_optional,
                             starting_record.child_data_for(field_name).default_value,
                             starting_record.docs_for(field_name),
                             starting_record.annotations_for(field_name))
            self._add_field(newfield)


class TypeStreamDeclaration(object):
    def __init__(self, constructor_fqn, param_names, projections):
        self.constructor = constructor_fqn
        self.param_names = param_names or []
        self.projections = projections

class PathResolver(object):
    """
    PathResolver interface resolvers need to do one thing.  They take in a 
    field path and return three things:

        1. The starting record from which the field path is a valid path.
        2. The source field nested (at some arbitrary depth) from the starting record
           that corresponds to the provided field path.
        3. The final field path that is RELATIVE to the starting record.  Concpetually:
              starting_record + final_field_path = current_context + input_field_path
    """
    def __init__(self, parent_entity):
        self.parent_entity = parent_entity

    def resolve_path(self, projection, registry):
        """
        This is the tricky bit.  Given our current field path, we need to find the source type and field within 
        the type that this field path corresponds to.
        """
        if not projection.field_path:
            return None, None, None

        field_path = projection.field_path
        final_field_path = field_path

        if field_path.is_absolute:
            # then first find the root record
            starting_record = projection.root_record.source_records[0].record_type
            final_field_path = FieldPath(field_path._parts[1:], field_path.selected_children)
        else:
            # otherwise get the first type in the parent hierarchy that matches the name first field path part
            curr_entity = projection.parent_entity
            starting_record = None
            while curr_entity:
                if is_derivation(curr_entity):
                    derivation = curr_entity
                    if derivation.source_count > 1:
                        raise errors.TLException("Multiple source derivation not yet supported")
                    elif derivation.source_count == 1:
                        source_record = derivation.source_records[0].record_type.type_data
                        starting_record, final_field_path = source_record.get_binding(field_path)
                        if starting_record:
                            break
                    curr_entity = derivation.parent_entity
                elif type(curr_entity) is Projection:
                    # check for bindings for the first name
                    starting_record, final_field_path = curr_entity.get_binding(field_path)
                    if starting_record:
                        break
                    curr_entity = curr_entity.parent_entity
                else:
                    ipdb.set_trace()
                    assert False

        final_record = starting_record
        final_field_data = None
        if final_record:
            # we have something to start off from so see if the full path is viable
            # resolve the field path from the starting record
            for i,part in enumerate(final_field_path._parts):
                if final_record.constructor != "record":
                    # Cannot be resolved as the ith part from the source_record is NOT of type record
                    # so we cannot go any further
                    return starting_record, None, None
                if not final_record.is_resolved:
                    final_record.resolve(registry)
                if not final_record.contains(part):
                    return starting_record, None, None
                final_field_data = final_record.child_data_for(part)
                final_record = final_record.child_type_for(part)
        return starting_record, final_field_data, final_field_path

class Field(object):
    """
    Holds all information about a field within a record.
    """
    def __init__(self, name, field_type, record, optional = False, default = None, docs = "", annotations = None):
        assert type(name) in (str, unicode), "Found type: '%s'" % type(name)
        if not isinstance(field_type, core.Type):
            ipdb.set_trace()
        assert isinstance(field_type, core.Type), type(field_type)
        self.field_name = name or ""
        self.field_type = field_type
        self.record = record
        self.is_optional = optional
        self.default_value = default or None
        self.docs = docs
        self.errors = []
        self.annotations = annotations or []

    def to_json(self):
        out = {
            "name": self.field_name,
            "type": self.field_type
        }
        return out

    @property
    def fqn(self):
        if self.record.type_data.fqn:
            return self.record.type_data.fqn + "." + self.field_name
        else:
            return self.field_name

    def __hash__(self):
        return hash(self.fqn)

    def __cmp__(self, other):
        result = cmp(self.record, other.record)
        if result == 0:
            result = cmp(self.field_name, other.field_name)
        return result

    def copy(self):
        out = Field(self.field_name, self.field_type, self.record, self.is_optional, self.default_value, self.docs, self.annotations)
        out.errors = self.errors 
        return out

    def copyfrom(self, another):
        self.field_name = another.field_name
        self.field_type = another.field_type
        self.record = another.record
        self.is_optional = another.is_optional
        self.default_value = another.default_value
        self.docs = another.docs
        self.errors = another.errors
        self.annotations = another.annotations

    def has_errors(self):
        return len(self.errors) > 0

    def __repr__(self): return str(self)
    def __str__(self):
        return self.fqn
