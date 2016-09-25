
import ipdb

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
        if len(parts) == 0:
            ipdb.set_trace()
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

    def with_child(self, field_name):
        """
        Creates a new field path, with the given name added to the end.  If this field path
        has children then the children are replaced with this field name otherwise
        a new level is added at the end.
        """
        return FieldPath(self._parts + [field_name])

    @property
    def length(self):
        if self.is_absolute:
            return len(self._parts) - 1
        else:
            return len(self._parts)

    @property
    def last(self):
        """
        Gets the last component of a field path.
        """
        return self._parts[-1]

    def pop(self):
        return self._parts[0], FieldPath(self._parts[1:], self.selected_children)

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
            return [arg.name for arg in starting_record.args]
        else:
            return [arg.name for arg in starting_record.args if arg.name in self.selected_children]


