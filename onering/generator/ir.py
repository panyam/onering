
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

class SetterInstruction(object):
    """
    An instruction to set the value of a register into a particular field path starting of a variable.
    """
    def __init__(self, source_register, field_path):
        self.source_register = source_register
        self.field_path = field_path

class FunctionCallInstruction(object):
    """
    An instruction to call a particular function with the arguments as the values from a particular register
    and then set the output into the output_register.
    """
    def __init__(self, func_name, input_registers, output_register):
        pass
