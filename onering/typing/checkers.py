
# Type checkers for data given types
from typecube import core
from typecube import errors

class Bindings(object):
    class Entry(object):
        def __init__(self, value, level, prev = None):
            self.value = value
            self.level = level
            self.prev = prev

        def __repr__(self):
            if self.prev:
                return "%s[%d] (%s)" % (repr(self.value), self.level, repr(self.prev))
            else:
                return "%s[%d]" % (repr(self.value), self.level)

    def __init__(self):
        self.level = 0
        self.entries = {}

    def __setitem__(self, key, value):
        entry = self.entries.get(key, None)
        if entry is not None and entry.level > self.level:
            raise errors.ValidationError("Value for '%s' already exists in this level (%d)" % (key, self.level))
        self.entries[key] = Bindings.Entry(value, self.level, entry)

    def __getitem__(self, key):
        while key in self.entries and self.entries[key].level > self.level:
            self.entries[key] = self.entries[key].prev
        if key not in self.entries: return None
        return self.entries[key].value

    def push(self):
        self.level += 1

    def pop(self):
        self.level += 1

def type_check(thetype, data, bindings = None):
    """ Checks that a given bit of data conforms to the type provided  """
    if not bindings: bindings = Bindings()
    if isinstance(thetype, core.RecordType):
        for name,child in zip(thetype.child_names, thetype.child_types):
            value = data[name]
            type_check(child, value, bindings)
    elif isinstance(thetype, core.TupleType):
        assert isinstance(data, tuple)
        assert len(data) == len(thetype.child_types)
        for value,child_type in zip(data, thetype.child_types):
            type_check(child_type, value, bindings)
    elif isinstance(thetype, core.UnionType):
        assert isinstance(thetype, dict)
        children = [(name,child) for name,child in zip(thetype.child_names, thetype.child_types) if name in data]
        assert len(fields) == 1, "0 or more than 1 entry in Union"
        child_name,child_type = children[0]
        type_check(child_type, data[child_name], bindings)
    elif isinstance(thetype, core.TypeApp):
        # Type applications are tricky.  These will "affect" bindings
        bindings.push()
        for k,v in thetype.param_values.items():
            bindings[k] = v
        type_check(thetype.root_type, data, bindings)
        bindings.pop()
    elif isinstance(thetype, core.TypeVar):
        # Find the binding for this type variable
        bound_type = bindings[thetype.name]
        if bound_type is None:
            raise errors.ValidationError("TypeVar(%s) is not bound to a type." % thetype.name)
        type_check(bound_type, data, bindings)
    elif isinstance(thetype, core.NativeType):
        # Native types are interesting - these can be plain types such as Int, Float etc
        # or they can be generic types like Array<T>, Map<K,V>
        # While plain types are fine, generic types (ie native types with args) pose a problem.
        # How do we perform type checking on "contents" of the data given native types.
        # We need native types to be able to apply mapper functions on data as they see fit.
        # So to deal with custom validations on native types we need
        # native types to expose mapper functors for us!!!
        if thetype.args and thetype.mapper_functor:
            def type_check_functor(*values):
                for arg, value in zip(thetype.args, values):
                    bound_type = bindings[arg]
                    if bound_type is None:
                        raise errors.ValidationError("Arg(%s) is not bound to a type." % arg)
                    type_check(bound_type, value)
            thetype.mapper_functor(type_check_functor, data)

    # Finally apply any other validators that were nominated 
    # specifically for that particular type
    if thetype.validator:
        thetype.validator(thetype, data, bindings)
