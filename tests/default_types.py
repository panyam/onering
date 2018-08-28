
from typecube.core import *
from typecube import errors

def default_string_validator(thetype, val, bindings = None):
    if type(val) is not str:
        raise errors.ValidationError("%s needs to be a string, found %s" % (str(val), str(type(val))))
    return val

def default_int_validator(thetype, val, bindings = None):
    if type(val) is not int:
        raise errors.ValidationError("%s needs to be a int, found %s" % (str(val), str(type(val))))
    return val

def default_float_validator(thetype, val, bindings = None):
    if type(val) is not float:
        raise errors.ValidationError("%s needs to be a float, found %s" % (str(val), str(type(val))))
    return val

def default_array_mapper_functor(function, val):
    if type(val) is not list:
        raise errors.ValidationError("%s needs to be a list, found %s" % (str(val), str(type(val))))
    for v in val: function(v)
    return val

def default_dict_mapper_functor(function, val):
    if type(val) is not dict:
        raise errors.ValidationError("%s needs to be a dict, found %s" % (str(val), str(type(val))))
    for k,v in iter(val.items()): function(k,v)
    return val

Byte = NativeType("byte")
Char = NativeType("char")
Float = NativeType("float").set_validator(default_float_validator)
Double = NativeType("double").set_validator(default_float_validator)
Int = NativeType("int").set_validator(default_int_validator)
Long = NativeType("Long").set_validator(default_int_validator)
String = NativeType("String").set_validator(default_string_validator)

Array = NativeType("Array", ["T"])
Array.mapper_functor = default_array_mapper_functor

List = NativeType("List", ["T"])
List.mapper_functor = default_array_mapper_functor

Map = NativeType("Map", ["K", "V"])
Map.mapper_functor = default_dict_mapper_functor

DateTime = TypeVar("DateTime")
