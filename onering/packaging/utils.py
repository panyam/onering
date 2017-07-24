
import ipdb
from typecube import core as tlcore
from onering.core import modules as ormods

def is_type_entity(entity):
    # What about type functions?
    if tlcore.istype(entity):
        if entity.is_product_type or entity.is_sum_type or entity.is_alias_type:
            return True
    return False

def is_typeop_entity(entity):
    if not isinstance(entity, tlcore.TypeOp): return False
    return not entity.is_external

def is_fun_entity(entity):
    if not issubclass(entity.__class__, tlcore.Fun): return False
    return not entity.is_external

def is_function_mapping_entity(entity):
    return isinstance(entity, tlcore.Fun) and entity.is_external and not entity.is_type_fun

