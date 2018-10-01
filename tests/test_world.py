
from ipdb import set_trace
from onering.common import errors
from onering.typing.core import *
from onering.typing import checkers
from onering.targets import packages
from onering.runtime import world
from . import default_types as defaults

def create_default_world():
    w = world.World()

    # What do we want with the world?
    # First we want to define our core types
    w.typing_context.add("core.Byte", defaults.Byte)
    w.typing_context.add("core.Char", defaults.Char)
    w.typing_context.add("core.Float", defaults.Float)
    w.typing_context.add("core.Double", defaults.Double)
    w.typing_context.add("core.Int", defaults.Int)
    w.typing_context.add("core.Long", defaults.Long)
    w.typing_context.add("core.String", defaults.String)
    w.typing_context.add("core.Array", defaults.Array)
    w.typing_context.add("core.Ref", defaults.Ref)
    w.typing_context.add("core.List", defaults.List)
    w.typing_context.add("core.Map", defaults.Map)
    w.typing_context.add("core.DateTime", defaults.DateTime)
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
    w.typing_context.add("utils.Pair", Pair)

    package1 = packages.Package("core")
    package2 = packages.Package("utils")
