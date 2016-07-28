
import importlib
import errors

def transform_fields(field_mapper, source_fields):
    """
    Applies a mapper to all fields in the source_fields list and returns a new set of fields.
    If name maps to another field more than once or another field in the source field list 
    (other than itself) an invalid mapping exception is thrown.
    """
    encountered = dict(map(lambda x: (x.name, True), source_fields))
    out = []
    for field in source_fields:
        newField = field.copy()
        newField.name = field_mapper(newField)
        if newField.name != field.name and newField.name in encountered:
            raise errors.TransformerException("Name of the mapped field(%s) already exists for field: %s" % (newField.name, field.name))
        encountered[newField.name] = newField
        out.append(newField)
    return out

def load_mapper(mapper_name):
    """
    Loads a fully mapper given the qualified mapper name
    """
    mapper_parts = mapper_name.split(".")
    mapper_packages, func_name = mapper_parts[:-1], mapper_parts[-1]
    thepackage = mapper_parts[0]
    # themodule = importlib.import_module(".".join(mapper_parts[1:-1]), thepackage)
    themodule = importlib.import_module(".".join(mapper_packages))
    return getattr(themodule, func_name)
