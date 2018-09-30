
from ipdb import set_trace
from onering.common import errors
from onering.typing.core import *
from onering.runtime import world
from onering.typing import checkers
from . import default_types as defaults

def test_world():
    w = world.World()

    # What do we want with the world?
    # First we want to define our core types
    w.global_module.add_entry("Byte", NativeType("Byte"))
    w.global_module.add_entry("Char", NativeType("Char"))
    w.global_module.add_entry("Float", NativeType("Float"))
    w.global_module.add_entry("Double", NativeType("Double"))
    w.global_module.add_entry("Int", NativeType("Int"))
    w.global_module.add_entry("Long", NativeType("Long"))
    w.global_module.add_entry("String", NativeType("String"))
    w.global_module.add_entry("Array", NativeType("Array", ["T"]))
    w.global_module.add_entry("List", NativeType("List", ["T"]))
    w.global_module.add_entry("Map", NativeType("Map", ["T", "V"]))
    w.global_module.add_entry("DateTime", TypeVar("DateTime"))
