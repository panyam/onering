
from onering import errors

class CheckerExpression(object):
    """
    An expression used to check whether a variable contains a value for a particular field.
    This result does not need to be stored.
    """
    def __init__(self, varname, fieldname):
        self.varname = varname
        self.fieldname = fieldname

    def __str__(self):
        return "Check<%s has %s>" % (self.varname, self.fieldname)

class SetterExpression(object):
    """
    Sets a value to a variable that may or may not have a field name.
    If the fieldname is missing then a local variable is to be created
    by the given name if it doesnt already exist.
    """
    def __init__(self, varname, fieldname, expression):
        self.varname = varname
        self.fieldname = fieldname
        self.expression = expression

    def __str__(self):
        return "Set<%s = %s>" % (self.varname + "." + self.fieldname if self.varname else self.fieldname, self.expression)

class GetterExpression(object):
    def __init__(self, varname, fieldname):
        self.varname = varname
        self.fieldname = fieldname

    def __str__(self):
        return "Get<%s . %s>" % (self.varname, self.fieldname)

class IfStatement(object):
    def __init__(self, condition, success_cases, failure_cases = None):
        self.condition = condition
        self.success_cases = success_cases or []
        self.failure_cases = failure_cases or []

    def __str__(self):
        return "If (%s) { %s } else { %s }" % (self.condition, self.success_cases, self.failure_cases)

def generate_getter_instructions(onering, vartype, source_name, field_path, varprefix = "var", startindex = 0):
    if not vartype.is_record_type:
        raise errors.OneringException("variable is not a record type")

    currcomp, rest = field_path[0], field_path[1:]
    condition = CheckerExpression(source_name, currcomp.name)

    nextvarname = "%s_%d" % (varprefix, startindex)
    nextvartype = vartype.type_data.get_field(currcomp.name).field_type
    created_vars = [(nextvartype, nextvarname)]

    setter = SetterExpression(nextvarname, None, GetterExpression(source_name, currcomp.name))
    startindex += 1
    next_getters, next_created_vars = [],[]
    if rest:
        next_getters, next_created_vars = generate_getter_instructions(onering, nextvartype, nextvarname, rest, varprefix, startindex)
    created_vars.extend(next_created_vars)

    return [IfStatement(condition, [setter] + next_getters)], created_vars


def generate_instructions(onering, source_var, source_type, source_field_paths, target_var, target_type, target_field_path):
    """
    Generates a list of platform and language agnostic instructions denoting
    get/set/apply/check operations that can be rendered by platform/language specific 
    templates to generate instance transformers.

    Essentially transformation rules are a series of:

        invoke_getter on object X for field Y and store into var N if X.Y exists
        apply mapper to var A and store into var B
        create a value of a particular type and store as var N
        invoke_setter on object A for Field B with value from var X

        take some examples:

        A and X -> target.setA(source.getX())
            var1 = null;
            if source.hasX() { var1 = source.getX(); }
            var2 = mapper(var1)
            target.setA(var2)

        A.x, B.y    -> source.getA().setx(target.getB().getY())
            type(B) var1;
            type(B.y) var2;
            type(A) var3;
            if target.hasB() {
                var1 = target.getB()
                if var1.hasY() {
                    var2 = var1.getY();
                }
            }
            if !source.hasA() {
                var3 = new type(A)();
                source.setA(var3);
            }
            var3 = source.getA();
            var3.setX(var2)
    """
    pass

def create_field_transformer(onering):
    def transform_field_func(source_var, source_field, target_var, target_field):
        lines = [ ]
        preamble = "if ( %s ) {" % invoke_checker(source_var, source_field)
        if target_field.field_type.is_list_type:
            target_list_type = target_field.field_type.type_data.value_type.list_type
            lines.extend([
                "if ( ! %s ) {" % invoke_checker(target_var, target_field),
                "    %s.set%s(new %s());" % (target_var, camel_case(target_field.name), target_list_type),
                "}",
                "%s target_list = %s;" % (target_list_type, invoke_getter(target_var, target_field)),
            ])

        if source_field.field_type.is_list_type and target_field.field_type.is_list_type:
            # We have two lists we need to copy from and to.
            # When two things arent lists we are good 
            transformer_code = apply_transformer(onering, source_field.field_type.type_data.value_type, target_field.field_type.type_data.value_type, "entry")
            lines.extend([
                "for (%s entry : %s)" % (source_field.field_type.type_data.value_type.list_type, invoke_getter(source_var, source_field)),
                "{",
                "    target_list.add(%s);" % transformer_code,
                "}"
            ])
        elif target_field.field_type.is_list_type:
            # copy source into target[0]
            transformer_code = apply_transformer(onering, source_field.field_type, target_field.field_type.type_data.value_type, source_var)
            lines.extend([
                "%s.add(%s)" % (target_var, transformer_code)
            ])
        elif source_field.field_type.is_list_type:
            getter = "%s.get(0)" % invoke_getter(source_var, source_field)
            transformer_code = apply_transformer(onering, source_field.field_type.type_data.value_type, target_field.field_type, getter)
            lines.extend([
                "%s.set%s(%s);" % (target_var, camel_case(target_field.name), transformer_code)
            ])
        else:
            # Best case - we have to "un" lists so just transform and copy
            transformer_code = apply_transformer(onering, source_field.field_type, target_field.field_type, source_var)
            lines.extend([
                "%s.set%s(%s);" % (target_var, camel_case(target_field.name), transformer_code)
            ])
        return "\n".join(["", preamble] + ["    " + l for l in lines] + ["}"])
    return transform_field_func
