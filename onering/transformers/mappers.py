
import re

def CamelCaseToUnderScoreFieldMapper(field):
    def prefix_us(x):
        index,x = x
        if x[0].islower():
            return x
        elif x[0].isupper():
            if index == 0:
                return x.lower()
            elif len(x) > 1:
                return "_" + x
            else:
                return "_" + x.lower()
    parts = re.sub("([A-Z]+)","_\g<1>_", field.name).split("_")
    return "".join(map(prefix_us, enumerate(filter(lambda x: x, parts))))

def UrnSuffixFieldMapper(field):
    if field.field_type.fqn.endswith("Urn") and not field.name.endswith("urn"):
        # we have an urn type so suffix it with _urn
        return field.name + "_urn"
    else:
        return field.name
