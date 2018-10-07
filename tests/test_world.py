
from ipdb import set_trace
from onering.common import errors
from onering.typing.core import *
from onering.typing import checkers, resolver
from onering.targets import packages
from onering.runtime import world
from . import default_types as defaults

def create_default_world():
    w = world.World()

    # What do we want with the world?
    # First we want to define our core types
    w.typing_context.set("core.Byte", defaults.Byte)
    w.typing_context.set("core.Char", defaults.Char)
    w.typing_context.set("core.Float", defaults.Float)
    w.typing_context.set("core.Double", defaults.Double)
    w.typing_context.set("core.Int", defaults.Int)
    w.typing_context.set("core.Long", defaults.Long)
    w.typing_context.set("core.String", defaults.String)
    w.typing_context.set("core.Array", defaults.Array)
    w.typing_context.set("core.Ref", defaults.Ref)
    w.typing_context.set("core.List", defaults.List)
    w.typing_context.set("core.Map", defaults.Map)
    w.typing_context.set("core.DateTime", TypeVar("core.Long"))
    return w

def test_world():
    create_default_world()

def test_record_gen():
    """ Test how a record is generated in a given language. """
    Pair = RecordType().add_multi(
                defaults.Int, "first",
                defaults.String, "second")

    # We want something like this
    # Here package is a virtual bundle or project (existing or new) where things 
    # are collected and dumped to.  The env/target decides what kind of generator
    # or templates to be used when emitting the artifacts.
    # The name indicates the project/package details we are modifying.
    w = create_default_world()
    w.typing_context.set("utils.Pair", Pair)

    package1 = packages.Package("core")
    package2 = packages.Package("utils")

def test_resolution_failure():
    """ Resolution is a phase where after taking in a bunch of types with 
    a whole lot of TypeVars in place, these TypeVars are bound to particular
    types already registered in the typing context.
    """
    w = create_default_world()

    Pair = RecordType(["F", "S"]).add_multi("F", "first", "S", "second")
    w.typing_context.set("utils.Pair", Pair)
    P1 = TypeApp("utils.Pair").apply(defaults.Int, defaults.String)
    checkers.type_check(Pair[defaults.Int, defaults.String], {'first': 1, 'second': '2'}, w.typing_context)
    try:
        checkers.type_check(P1, {'first': 1, 'second': '2'}, w.typing_context)
        assert False
    except errors.ValidationError as ve:
        pass

def test_resolution_success():
    """ Resolution is a phase where after taking in a bunch of types with 
    a whole lot of TypeVars in place, these TypeVars are bound to particular
    types already registered in the typing context.
    """
    w = create_default_world()

    Pair = RecordType(["F", "S"]).add_multi("F", "first", "S", "second")
    w.typing_context.set("utils.Pair", Pair)
    P1 = TypeApp("utils.Pair").apply(defaults.Int, defaults.String)

    resolver.resolve_bindings(w.typing_context)
    resolver.resolve_bindings_for_type(P1, w.typing_context)
    checkers.type_check(P1, {'first': 1, 'second': '2'}, w.typing_context)
