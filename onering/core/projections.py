
from onering import errors
from typelib import errors as tlerrors
from onering.utils import normalize_name_and_ns

class Projection(object):
    """
    Projection is anything that results in the creation of a type.
    This could be named like a field or a named derived type (like a record, union, enum)
    or an unnamed type like the argument to a type constructor (eg key type of a map)
    """
    @property
    def target_is_optional(self):
        """
        Whether projectee is optional.  Some projectees should not be optional.
        """
        return False

    @property
    def target_default_value(self):
        """
        Whether there is a default value for the projectee.  Not all projectees need to have default values.
        """
        return None

    @property
    def target_name(self):
        """
        The name of the target after being projected.  Not all projectees need to have names.
        """
        return None

    @property
    def target_type(self)
        """
        The resolved type that is created as a result of this projection.
        """
        # This must be implemented by child projection types
        return None

class FieldProjection(Projection):
    """
    A projection that simply takes a source field and returns it as is with a possibly new type.
    """
    @property
    def source_field_path(self):
        """
        The source field this projection is "taking on" from.
        """

class TypeStreaming(FieldProjection):
    """
    A type of field projection that results in container types being created.
    """
    pass

class InlineDerivation(FieldProjection):
    """
    A type of field projection that results in a new record being derived.
    """
    pass
