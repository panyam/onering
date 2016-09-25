
import ipdb
from onering import errors

class ValueOrVar(object):
    def __init__(self, entry, is_value):
        self.entry = entry
        self.is_value = is_value

    def __repr__(self):
        if self.is_value:
            return "<Value (0x%x): %s>" % (id(self), self.entry)
        else:
            return "<Var (0x%x): %s>" % (id(self), self.entry)

class GetterInstruction(object):
    """
    An instruction to get the value of a field path from a starting variable and set it into 
    a particular register.
    """
    def __init__(self, field_path, target_register):
        self.field_path = field_path
        self.target_register = target_register

    def __repr__(self):
        return "GET %s -> %s" % (self.field_path, self.target_register)

class SetterInstruction(object):
    """
    An instruction to set the value of a register into a particular field path starting of a variable.
    """
    def __init__(self, source_register, target_var):
        self.source_register = source_register
        self.target_var = target_var

    def __repr__(self):
        return "SET %s -> %s" % (self.source_register, self.target_var)

class FunctionCallInstruction(object):
    """
    An instruction to call a particular function with the arguments as the values from a particular register
    and then set the output into the output_register.
    """
    def __init__(self, func_fqn, input_registers, output_register):
        self.func_fqn = func_fqn
        self.input_registers = input_registers
        self.output_register = output_register

    def __repr__(self):
        return "CALL %s [(%s) -> %s]" % (self.func_fqn, ", ".join(self.input_registers), self.output_register)


class IfStatement(object):
    """
    An instruction to keep track of if statements.
    """
    def __init__(self, condition, body, otherwise = None):
        self.condition = condition
        self.body = body
        self.otherwise = otherwise

class ContainsInstruction(object):
    def __init__(self, var, field_name):
        self.source_var = var
        self.field_name = field_name
