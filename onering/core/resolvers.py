
from __future__ import absolute_import
import ipdb
from typelib import core as tlcore
from onering.core.utils import FieldPath

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
                result = self.resolve_path(tail_field_path)
                return result
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
        result = None
        if len(self.derivation.source_aliases.keys()) == 1:
            # If there are more than sources then we MUST use a key to start the path with
            source_fqn = self.derivation.source_aliases.values()[0]
            starting_typeref = self.type_registry.get_typeref(source_fqn)

            # TODO: We should consider generalizing this.  Is it better to have "multiple" named sources here?
            # Eg in a type streaming, there are technically no sources but every bound variable is a source
            result = resolve_path_from_record(starting_typeref, field_path, self.type_registry, self)

        if (not result or not result.is_valid) and field_path.length > 0:
            # Then try it with as if the first part of the fieldpath is a source itself
            for src in self.derivation.source_aliases.keys():
                if src == field_path.get(0):
                    src = self.derivation.source_aliases[src]
                    starting_typeref = self.type_registry.get_typeref(source_fqn)
                    result = resolve_path_from_record(starting_typeref, field_path.pop()[1], self.type_registry, self)
                    break
        return result

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
        field_typeref = self.type_stream.field_path_resolution.resolved_typeref
        for index,param in enumerate(self.type_stream.param_names):
            if param == field_path.get(0):
                final_type = field_typeref.final_type
                assert field_typeref.is_resolved, "Typeref for the source field must be resolved.  It is not!"
                child_typeref = final_type.arg_at(index).typeref
                if field_path.length == 1:
                    return ResolutionResult(field_typeref, field_typeref, index, field_path)
                else:
                    _, tail_field_path = field_path.pop()
                    return resolve_path_from_record(child_typeref, tail_field_path, self.type_registry, self)
        return None

class ResolutionResult(object):
    def __init__(self, root_typeref, parent_typeref, child_key, normalized_field_path = None):
        self.root_typeref = root_typeref
        self.parent_typeref = parent_typeref
        self.child_key = child_key
        self.normalized_field_path = normalized_field_path

    @property
    def is_valid(self):
        return self.root_typeref is not None and self.parent_typeref is not None and self.child_key is not None

    @property
    def parent_type(self):
        return self.parent_typeref.target

    @property
    def resolved_typeref(self):
        if type(self.child_key) in (str, unicode):
            child = self.parent_typeref.final_type.arg_for(self.child_key).typeref
        else:
            child = self.parent_typeref.final_type.arg_at(self.child_key).typeref
        return child

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
        be set if the parent_typeref is a record type.  Otherwise None.
        """
        if self.parent_typeref.final_type.constructor is not "record":
            return self.normalized_field_path.last
        return self.child_key

def resolve_path_from_record(starting_typeref, field_path, registry, resolver):
    root_typeref = starting_typeref
    parent_typeref = starting_typeref
    final_typeref = starting_typeref
    child_key = None
    for i in xrange(field_path.length):
        part = field_path.get(i)
        final_type = final_typeref.final_type
        if final_typeref.is_unresolved or final_type.constructor != "record":
            # TODO - Throw an "unresolved type" exception?
            return ResolutionResult(root_typeref, None, None, field_path)
        if not final_type.contains(part):
            # Throw NotFound instead of none?
            break
        child_key = part
        parent_typeref = final_typeref
        final_typeref = final_type.arg_for(part).typeref
    return ResolutionResult(root_typeref, parent_typeref, child_key, field_path)
