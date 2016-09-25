
import ipdb
from onering import errors

class ValueOrAddress(object):
    def __init__(self, entry):
        self.entry = entry

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
