
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
        val = self.entry
        if type(self.entry) is lexer.Token:
            val = self.entry.value
        if type(val) in (str, unicode):
            return "\"%s\"" % val
        if type(val) is list:
            return "[" + ", ".join(map(str, val)) + "]"
        return str(val)

class GetFieldInstruction(object):
    """
    An instruction to get the value of a field path from a starting variable and set it into a particular register.
    """
    def __init__(self, source_register, field_key, target_register):
        self.source_register = source_register
        self.field_key = field_key
        self.target_register = target_register

    def __repr__(self):
        return "GET %s[%s] -> %s" % (self.source_register, self.field_key, self.target_register)

class CopyVarInstruction(object):
    """
    An instruction to get the value of a local var and set it into another var.
    """
    def __init__(self, source_register, target_register):
        self.source_register = source_register
        self.target_register = target_register

    def __repr__(self):
        return "GET %s -> %s" % (self.source_register , self.target_register)

class SetFieldInstruction(object):
    """
    Set the value of a field in target variable from source variable, Akin to:

        target_register.set<field_key>(source_register)
    """
    def __init__(self, source_register, field_key, target_register):
        if source_register is None or target_register is None:
            ipdb.set_trace()
        self.source_register = source_register
        self.target_register = target_register
        self.field_key = field_key

    def __repr__(self):
        return "SET %s -> %s[%s]" % (self.source_register, self.target_register, self.field_key)

class FunAppInstruction(object):
    """
    An instruction to call a particular function with the arguments as the values from a particular register
    and then set the output into the output_register.
    """
    def __init__(self, func_fqn, input_registers, output_register):
        self.func_fqn = func_fqn
        self.input_registers = input_registers
        self.output_register = output_register

    def __repr__(self):
        return "CALL %s [(%s) -> %s]" % (self.func_fqn, ", ".join(map(str, self.input_registers)), self.output_register)


class IfStatement(object):
    """
    An instruction to keep track of if statements.
    """
    def __init__(self, condition_expr, body, otherwise = None, negate = False):
        self.condition_expr = condition_expr
        self.negate = negate
        self.body = body or []
        self.otherwise = otherwise or []

class ContainsInstruction(object):
    def __init__(self, register, field_name):
        self.source_register = register
        self.field_name = field_name

class NewInstruction(object):
    def __init__(self, value_typeref, target_register):
        self.value_typeref = value_typeref
        self.target_register = target_register
