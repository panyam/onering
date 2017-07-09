
import ipdb
from typelib import core as tlcore
from onering.core import modules as ormods

def is_type_entity(entity):
    # What about type functions?
    if tlcore.istype(entity):
        if entity.is_product_type or entity.is_sum_type:
            return True
    return False

def is_typefun_entity(entity):
    if not isinstance(entity, tlcore.TypeFun): return False
    return not entity.is_external

def is_fun_entity(entity):
    if not isinstance(entity, tlcore.Fun): return False
    return not entity.is_external

def is_function_mapping_entity(entity):
    return isinstance(entity, tlcore.Fun) and entity.is_external and not entity.is_type_fun

