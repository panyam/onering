
import ipdb
from onering.generator.symtable import SymbolTable
from onering.generator import ir
from onering.core.exprs import Expression, LiteralExpression, ListExpression, DictExpression, TupleExpression, FunctionCallExpression, VariableExpression

"""
This module is responsible for generating code for a statement and all parts of an expression tree.
"""

def generate_ir_for_function(function, context):
    symtable = SymbolTable()

    # Set source and dest variables in symbol table
    for src_varname,src_typeref in function.source_variables:
        symtable.register_var(src_varname, src_typeref, False)
    symtable.register_var(function.dest_varname, function.typeref.output_typeref, False)
    instructions, symtable, _ = generate_ir_for_statements(function.all_statements, context, symtable = symtable)
    return instructions, symtable

def generate_ir_for_statements(statements, context, instructions = None, symtable = None):
    """
    Generates the IR for a bunch of statements and returns the instruction list as well as the final symbol table required.
    """
    if not instructions: instructions = []
    if not symtable: symtable = SymbolTable()

    # Generate all "temp" vars across all statements first
    for index,statement in enumerate(statements):
        if statement.is_temporary:
            # Register var if this is temporary
            symtable.register_var(statement.target_variable.value.get(0), statement.target_variable.evaluated_typeref, True)

    # Now do the normal generation
    for index,statement in enumerate(statements):
        generate_ir_for_statement(statement, context, instructions, symtable)

    return instructions, symtable, None

def generate_ir_for_statement(statement, context, instructions, symtable):
    last_return = None
    for expr in statement.expressions:
        # Call the the generator for the expression with the last return value as its inputs
        instructions, symtable, last_register = generate_ir_for_expression(expr, context, last_return, instructions, symtable)

    # Generate a setter instruction too
    generate_ir_for_setter(last_register, statement.target_variable, instructions, symtable)

    # Statements dont have return values
    return instructions, symtable, None

def generate_ir_for_expression(expr, context, input_values, instructions, symtable):
    irgenerators = {
        LiteralExpression: generate_ir_for_literal,
        TupleExpression: generate_ir_for_tuple,
        ListExpression: generate_ir_for_list,
        DictExpression: generate_ir_for_dict,
        FunctionCallExpression: generate_ir_for_function_call,
        VariableExpression: generate_ir_for_variable,
    }
    return irgenerators[type(expr)](expr, context, input_values, instructions, symtable)

def generate_ir_for_literal(expr, context, input_values, instructions, symtable):
    # So there are no explicit "inputs", just locations or values that something is bound to
    # then why the rigmoral of passing input_values?   This means our values should either
    # be const values, or addresses and the bindings should give us this.  Also input_values 
    # does not make sense because you could refer to values that are coming from a "global"ish
    # scope ie variables local to a function
    return instructions, symtable, ir.ValueOrVar(expr.value, True)

def generate_ir_for_tuple(expr, context, input_values, instructions, symtable):
    # First evaluate all child expressions
    child_values = []
    for child in expr.values:
        instructions, symtable, value = generate_ir_for_expression(child, context, None, instructions, symtable)
        child_values.append(value)
    return instructions, symtable, child_values

def generate_ir_for_list(expr, context, input_values, instructions, symtable):
    # First evaluate all child expressions
    child_values = []
    for child in expr.values:
        instructions, symtable, value = generate_ir_for_expression(child, context, None, instructions, symtable)
        child_values.append(value)
    return instructions, symtable, child_values

def generate_ir_for_dict(expr, context, input_values, instructions, symtable):
    # TBD
    out = {}
    for k,v in expr.values.iteritems():
        instructions, symtable, key_values = generate_ir_for_expression(k, context, None, instructions, symtable)
        instructions, symtable, value_values = generate_ir_for_expression(v, context, None, instructions, symtable)
        out[key_values] = value_values
    return instructions, symtable, out

def generate_ir_for_function_call(expr, context, input_values, instructions, symtable):
    # Evaluate parameter values
    arg_values = []
    for arg in expr.func_args:
        instructions, symtable, value = generate_ir_for_expression(arg, context, None, instructions, symtable)
        arg_values.append(value)
    new_register = symtable.next_register(expr.evaluated_typeref)
    instructions.append(ir.FunctionCallInstruction(expr.func_ref.final_entity.fqn, arg_values, new_register))
    return instructions, symtable, new_register

def generate_ir_for_variable(expr, context, input_values, instructions, symtable):
    starting_var, field_path = expr.normalized_field_path.pop()
    if expr.is_temporary:
        starting_typeref = expr.evaluated_typeref
    else:
        resolution_result = expr.field_resolution_result 
        if not resolution_result:
            ipdb.set_trace()
        starting_typeref = resolution_result.root_typeref

    curr_typeref = starting_typeref
    curr_path = starting_var
    curr_register = symtable.get_register_for_path(starting_var)
    curr_instrs = instructions
    while field_path.length > 0:
        next_field_name, tail_path = field_path.pop()
        next_path = curr_path + "/" + next_field_name
        next_typeref = curr_typeref.final_entity.arg_for(next_field_name).typeref
        next_register = symtable.get_register_for_path(next_path, next_typeref)

        # Get the next var and store into the var
        contains_instr = ir.ContainsInstruction(curr_register, next_field_name)
        get_instr = ir.GetFieldInstruction(curr_register, next_field_name, next_register)
        if_stmt = ir.IfStatement(contains_instr, [ get_instr ], None)
        curr_instrs.append(if_stmt)
        curr_instrs = if_stmt.body
        curr_path, curr_register, field_path = next_path, next_register, tail_path

    return instructions, symtable, curr_register



def generate_ir_for_setter(source_register, target_var, instructions, symtable):
    starting_var, field_path = target_var.normalized_field_path.pop()
    starting_register = symtable.get_register_for_path(starting_var)
    if target_var.is_temporary:
        starting_typeref = target_var.evaluated_typeref
        if field_path.length == 0:
            # Do a direct copy as no nesting into a local var
            instructions.append(ir.CopyVarInstruction(source_register, starting_register))
            return instructions, symtable, None
    else:
        assert field_path.length > 0, "Source or Destination variables cannot be overwritten"
        resolution_result = target_var.field_resolution_result 
        if resolution_result == None: ipdb.set_trace()
        starting_typeref = resolution_result.root_typeref

    curr_typeref = starting_typeref
    curr_path = starting_var
    curr_register = starting_register

    while field_path.length > 1:
        # At each level of the remaining field paths, keep finding and setting
        # fields if they are null
        next_field_name, tail_path = field_path.pop()
        next_path = curr_path + "/" + next_field_name
        next_typeref = curr_typeref.final_type.arg_for(next_field_name).typeref
        next_register = symtable.get_register_for_path(next_path, next_typeref)

        # Get the next register and store into the register
        contains_instr = ir.ContainsInstruction(curr_register, next_field_name)
        set_default_instr = ir.NewInstruction(curr_typeref, next_register)
        if_stmt = ir.IfStatement(contains_instr, [ set_default_instr ], None, negate = True)
        instructions.append(if_stmt)

        get_instr = ir.GetFieldInstruction(curr_register, next_field_name, next_register)
        instructions.append(get_instr)

        curr_path, curr_register, field_path = next_path, next_register, tail_path

    assert field_path.length <= 1
    # Means we have a single entry in the path left
    # so the value can be directly set
    instructions.append(ir.SetFieldInstruction(source_register, field_path.get(0), curr_register))

    return instructions, symtable, None
