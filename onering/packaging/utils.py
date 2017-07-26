
import ipdb
from typecube import core as tccore
from onering.core import modules as ormods

def is_type_entity(entity):
    # What about type functions?
    if entity.isa(tccore.ProductType) or entity.isa(tccore.SumType) or entity.isa(tccore.AliasType):
        return True
    return False

def is_typeop_entity(entity):
    if not isinstance(entity, tccore.TypeOp): return False
    return not entity.is_external

def is_fun_entity(entity):
    return (entity.isa(tccore.Quant) or entity.isa(tccore.Fun)) and not entity.is_external

def is_function_mapping_entity(entity):
    return isinstance(entity, tccore.Fun) and entity.is_external and not entity.is_type_fun

