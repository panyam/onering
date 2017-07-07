
import ipdb
from typelib import core as tlcore
from onering.core import modules as ormods

def is_type_entity(entity):
    # What about type functions?
    if type(entity) is tlcore.Type:
        if entity.category in (tlcore.TypeCategory.PRODUCT_TYPE, tlcore.TypeCategory.SUM_TYPE, tlcore.TypeCategory.ALIAS_TYPE):
            return True
        ipdb.set_trace()
        return False

    if type(entity) is tlcore.FunApp and entity.is_type_app:
        resval = entity.resolved_value
        ipdb.set_trace()
        return is_type_entity(resval)
    return False

def is_type_fun_entity(entity):
    if not isinstance(entity, tlcore.Fun): return False
    return entity.is_type_fun

def is_fun_entity(entity):
    if not isinstance(entity, tlcore.Fun): return False
    if entity.is_external: return False
    return not entity.is_type_fun

def is_function_mapping_entity(entity):
    return isinstance(entity, tlcore.Fun) and entity.is_external and not entity.is_type_fun

