
from onering.common import errors
from onering.typing.core import *

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

Byte = NativeType()
Char = NativeType()
Float = NativeType().set_validator(default_float_validator)
Double = NativeType().set_validator(default_float_validator)
Int = NativeType().set_validator(default_int_validator)
Long = NativeType().set_validator(default_int_validator)
String = NativeType().set_validator(default_string_validator)

Ref = NativeType(["T"])

Array = NativeType(["T"])
Array.mapper_functor = default_array_mapper_functor

List = NativeType(["T"])
List.mapper_functor = default_array_mapper_functor

Map = NativeType(["K", "V"])
Map.mapper_functor = default_dict_mapper_functor
