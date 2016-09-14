
import ipdb
from utils import FieldPath

def resolve_path_from_record(starting_record, field_path, registry, resolver):
    root_record = starting_record
    parent_record = starting_record
    final_record = starting_record
    child_type_key = None
    for i in xrange(field_path.length):
        part = field_path.get(i)
        if final_record.constructor != "record":
            # TODO - Throw a "bad type" exception?
            break
        if not final_record.is_resolved:
            # TODO - Does the order of resolutions make a difference?
            final_record.resolve(registry)
        if not final_record.contains(part):
            # Throw NotFound instead of none?
            break
        child_type_key = part
        parent_record = final_record
        final_record = final_record.child_type_for(part)
    return ResolutionResult(root_record, parent_record, child_type_key, field_path)

class ResolutionResult(object):
    def __init__(self, root_type, parent_type, child_type_key, full_field_path = None):
        self.root_type = root_type
        self.parent_type = parent_type
        self.child_type_key = child_type_key
        self.full_field_path = full_field_path

    @property
    def is_valid(self):
        return self.root_type is not None and self.parent_type is not None and self.child_type_key is not None

    @property
    def resolved_type(self):
        if type(self.child_type_key) in (str, unicode):
            return self.parent_type.child_type_for(self.child_type_key)
        else:
            return self.parent_type.child_type_at(self.child_type_key)

    @property
    def resolved_type_data(self):
        if type(self.child_type_key) in (str, unicode):
            return self.parent_type.child_data_for(self.child_type_key)
        else:
            return self.parent_type.child_data_at(self.child_type_key)

    @property
    def docs(self):
        return ""

    @property
    def annotations(self):
        return []

    @property
    def field_name(self):
        """
        Name of the field as a result of the path resolution.  Note that this only 
        be set if the parent_type is a record type.  Otherwise None.
        """
        if self.parent_type.constructor is not "record":
            return self.full_field_path.last
        return self.child_type_key


class PathResolver(object):
    """
    An interface that helps in the resolution of a field path.  This is hierarchical in nature.
    """
    def __init__(self, parent_resolver = None):
        self.parent_resolver = parent_resolver

    def resolve_path(self, field_path):
        if field_path.is_absolute:
            # resolve it with reference to this level if we have no other parent
            if self.parent_resolver:
                # TODO - Should there be a "root" property to go directly to the root instead
                # of repeatedly calling parent until we hit the root?
                return self.parent_resolver.resolve_path(field_path)
            elif field_path.length > 0:
                _, tail_field_path = field_path.pop()
                return self.resolve_path(tail_field_path)
            else:
                return self._resolve_relative_path(field_path)
        else:
            resolution_result = self._resolve_relative_path(field_path)
            if resolution_result is None or not resolution_result.is_valid:
                # Implementation could not resolve so delegate to parent resolve if one exists
                if self.parent_resolver:
                    return self.parent_resolver.resolve_path(field_path)
            return resolution_result


    def _resolve_relative_path(self, field_path):
        """
        This when implemented by derived resolvers will handle projection/context specific resolution of field paths.
        """
        pass


class DerivationPathResolver(PathResolver):
    def __init__(self, parent_resolver, derivation, type_registry):
        super(DerivationPathResolver, self).__init__(parent_resolver)
        self.derivation = derivation
        self.type_registry = type_registry

    def _resolve_relative_path(self, field_path):
        """
        Checks if the field path matches any of the fields in the derivation's source records
        """
        # get the first source ...
        source_fqn = self.derivation.source_aliases.values()[0]
        starting_type = self.type_registry.get_type(source_fqn)

        return resolve_path_from_record(starting_type, field_path, self.type_registry, self)

class TypeStreamPathResolver(PathResolver):
    def __init__(self, parent_resolver, type_stream, type_registry):
        super(TypeStreamPathResolver, self).__init__(parent_resolver)
        self.type_stream = type_stream
        self.type_registry = type_registry

    def _resolve_relative_path(self, field_path):
        """
        Checks if the field path matches any of the fields in the derivation's source records
        """
        # get the first source ...
        # basicaly check if field_path[0] matches any of the parameters then drill down on that
        field_type = self.type_stream.field_path_resolution.resolved_type
        for index,param in enumerate(self.type_stream.param_names):
            if param == field_path.get(0):
                child_type = field_type.child_type_at(index)
                if field_path.length == 1:
                    return ResolutionResult(field_type, field_type, index, field_path)
                else:
                    _, tail_field_path = field_path.pop()
                    return resolve_path_from_record(child_type, tail_field_path, self.type_registry, self)
        return None
