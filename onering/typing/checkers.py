
from ipdb import set_trace
from onering.common import errors
from onering.typing import core
from onering.typing.context import Context

def type_check(thetype : core.Type, data, context : Context = None):
    """ Checks that a given bit of data conforms to the type provided  """
    context = context or Context()
    if isinstance(thetype, core.RecordType):
        for name,child in zip(thetype.child_names, thetype.child_types):
            value = data[name]
            type_check(child, value, context)
    elif isinstance(thetype, core.TupleType):
        assert isinstance(data, tuple)
        assert len(data) == len(thetype.child_types)
        for value,child_type in zip(data, thetype.child_types):
            type_check(child_type, value, context)
    elif isinstance(thetype, core.UnionType):
        assert isinstance(thetype, dict)
        children = [(name,child) for name,child in zip(thetype.child_names, thetype.child_types) if name in data]
        assert len(fields) == 1, "0 or more than 1 entry in Union"
        child_name,child_type = children[0]
        type_check(child_type, data[child_name], context)
    elif isinstance(thetype, core.TypeApp):
        # Type applications are tricky.  These will "affect" the type context
        if thetype.unused_values:
            raise errors.ValidationError("TypeApp still has unused type params.  Run the resolver first.")
        context.push()
        for k,v in thetype.param_values.items():
            context.set(k, v)
        root_type = thetype.root_type
        if isinstance(root_type, core.TypeVar):
            if root_type.binding is None:
                raise errors.ValidationError("TypeVar(%s) is unbound.  Run the resolver first.")
        type_check(root_type, data, context)
        context.pop()
    elif isinstance(thetype, core.TypeVar):
        # Find the binding for this type variable
        bound_type = thetype.bound_type
        if not bound_type:
            # Check if we are in the bindings
            bound_type = context.get(thetype.name)
        if not bound_type:
            set_trace()
            raise errors.ValidationError("TypeVar(%s) is not bound to a type." % thetype.name)
        type_check(bound_type, data, context)
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
                    bound_type = context.get(arg)
                    if bound_type is None:
                        raise errors.ValidationError("Arg(%s) is not bound to a type." % arg)
                    type_check(bound_type, value, context)
            thetype.mapper_functor(type_check_functor, data)

    # Finally apply any other validators that were nominated 
    # specifically for that particular type
    if not thetype: set_trace()
    if thetype.validator:
        thetype.validator(thetype, data, context)
