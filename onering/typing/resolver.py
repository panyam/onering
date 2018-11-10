
from ipdb import set_trace
import typing
from onering.common import errors
from onering.typing import core
from onering.typing.context import Context

def resolve_bindings(context : Context):
    typesleft = list(context.all_types)
    while typesleft:
        fqn, T = typesleft.pop()
        resolve_bindings_for_type(T, context, [])

def resolve_bindings_for_type(T : core.Type, context : Context, container_stack : typing.List[core.Type] = None):
    """ Resolves the bindings starting from a given Type instance T and 
        binds them to the correct type or binder.

    By the end of this phase, we expect all type variables to have one of the 
    two pieces of info:

        1. It has a bound type that is a proper (non TypeVar) Type object
           (eg core.Int, utils.Pair etc).
        2. Or it points to a parent (non TypeVar) type whose arg value 
           when set, is the value also used by this TypeVar - ie during
           type applications.
    """
    container_stack = container_stack or []
    if isinstance(T, core.NativeType):
        # Native types dont need any resolution as we dont know anything about them
        return

    if issubclass(T.__class__, core.DataType):
        newstack = [T] + container_stack
        [resolve_bindings_for_type(child, context, newstack) for child in T.child_types]
    elif isinstance(T, core.TypeApp):
        resolve_bindings_for_type(T.root_type, context, container_stack)
        [resolve_bindings_for_type(v, context, container_stack) for v in T.param_values.values()]
        # Now that root has been resolved, apply any unused values we have
        while T.unused_values:
            prevlen = len(T.unused_values)
            T.apply(T.unused_values.pop(0))
            # TODO - Expecting a bug here but not sure how to fix it yet So investigating
            assert len(T.unused_values) == prevlen - 1
    elif isinstance(T, core.TypeVar):
        # Now the fun begins - find the parent in the container stack that has this "name"
        # as a variable otherwise bind to a value in the context
        for parent in container_stack:
            if T.name in parent.args:
                T.bound_parent = parent
                return
        T.bound_type = context.get(T.name)

