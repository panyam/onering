
import ipdb
from onering import errors
from onering.dsl import lexer

class ValueOrVar(object):
    def __init__(self, entry, is_value):
        self.entry = entry
        self.is_value = is_value

    def __repr__(self):
        if self.is_value:
            return "<Value (0x%x): %s>" % (id(self), self.entry)
        else:
            return "<Var (0x%x): %s>" % (id(self), self.entry)

    def __str__(self):
        if type(self.entry) is lexer.Token:
            val = self.entry.value
            if type(val) in (str, unicode):
                return "\"%s\"" % val
            return str(val)
        else:
            return str(self.entry)

class GetFieldInstruction(object):
    """
    An instruction to get the value of a field path from a starting variable and set it into a particular register.
    """
    def __init__(self, source_var, field_key, target_var):
        self.source_var = source_var
        self.field_key = field_key
        self.target_var = target_var

    def __repr__(self):
        return "GET %s[%s] -> %s" % (self.source_var, self.field_key, self.target_var)

class CopyVarInstruction(object):
    """
    An instruction to get the value of a local var and set it into another var.
    """
    def __init__(self, source_var, target_var):
        self.source_var = source_var
        self.target_var = target_var

    def __repr__(self):
        return "GET %s -> %s" % (self.source_var , self.target_var)

class SetFieldInstruction(object):
    """
    Set the value of a field in target variable from source variable
    """
    def __init__(self, source_var, field_key, target_var):
        self.source_var = source_var
        self.target_var = target_var
        self.field_key = field_key

    def __repr__(self):
        return "SET %s -> %s[%s]" % (self.source_var, self.target_var, self.field_key)

class FunctionCallInstruction(object):
    """
    An instruction to call a particular function with the arguments as the values from a particular register
    and then set the output into the output_register.
    """
    def __init__(self, func_fqn, input_vars, output_var):
        self.func_fqn = func_fqn
        self.input_vars = input_vars
        self.output_var = output_var

    def __repr__(self):
        return "CALL %s [(%s) -> %s]" % (self.func_fqn, ", ".join(self.input_vars), self.output_var)


class IfStatement(object):
    """
    An instruction to keep track of if statements.
    """
    def __init__(self, condition_var, body, otherwise = None, negate = False):
        self.condition_var = condition_var
        self.negate = negate
        self.body = body or []
        self.otherwise = otherwise or []

class ContainsInstruction(object):
    def __init__(self, var, field_name):
        self.source_var = var
        self.field_name = field_name

class NewInstruction(object):
    def __init__(self, value_typeref, target_var):
        self.value_typeref = value_typeref
        self.target_var = target_var
