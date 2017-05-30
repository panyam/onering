
import ipdb
from typelib import core as tlcore
from onering.generator.symtable import SymbolTable
from onering.generator import ir
from typelib.core import Expression, Variable, Function, FunctionCall
from typelib.ext import ListExpression, DictExpression, TupleExpression, IfExpression, LiteralExpression, ExpressionList, Assignment

"""
This module is responsible for generating code for a statement and all parts of an expression tree.
"""

def generate_ir_for_expression(expr, context, instructions, symtable):
    if instructions is None: instructions = []
    if symtable is None: symtable = SymbolTable()

    if expr is None:
        return instructions, symtable, None

    irgenerators = {
        LiteralExpression: generate_ir_for_literal,
        TupleExpression: generate_ir_for_tuple,
        ListExpression: generate_ir_for_list,
        DictExpression: generate_ir_for_dict,
        FunctionCall: generate_ir_for_function_call,
        Variable: generate_ir_for_variable,
        IfExpression: generate_ir_for_if_expression,
        Assignment: generate_ir_for_assignment,
        ExpressionList: generate_ir_for_expression_list,
    }
    return irgenerators[type(expr)](expr, context, instructions, symtable)

def generate_ir_for_function(function, context):
    symtable = SymbolTable()
    assert not function.is_external, "External functions cannot be generated"

    # Set source and dest variables in symbol table
    for typearg in function.source_typeargs:
        symtable.register_var(typearg.name, typearg.type_expr, False)
    if not function.returns_void:
        symtable.register_var(function.dest_varname, function.dest_typearg, False)
    instructions, symtable, _ = generate_ir_for_expression(function.expression, context, [], symtable = symtable)
    return instructions, symtable

def generate_ir_for_expression_list(expression_list, context, instructions, symtable):
    """
    Generates the IR for a bunch of statements and returns the instruction list as well as the final symbol table required.
    """
    assert instructions is not None and symtable is not None
    # Now do the normal generation
    last_register = None
    for index,expr in enumerate(expression_list.children):
        instructions, symtable, last_register = generate_ir_for_expression(expr, context, instructions, symtable)
    return instructions, symtable, last_register

def generate_ir_for_assignment(assignment, context, instructions, symtable):
    # Generate all "temp" vars across all statements first
    if assignment.is_temporary:
        # Register var if this is temporary
        symtable.register_var(assignment.target_variable.field_path.get(0), assignment.target_variable.evaluated_typeexpr, True)

    # Call the the generator for the expression with the last return value as its inputs
    instructions, symtable, last_register = generate_ir_for_expression(assignment.expression, context, instructions, symtable)

    # Generate a setter instruction too
    generate_ir_for_setter(last_register, assignment.target_variable, instructions, symtable)

    # Statements dont have return values
    return instructions, symtable, None

def generate_ir_for_literal(expr, context, instructions, symtable):
    # So there are no explicit "inputs", just locations or values that something is bound to
    # then why the rigmoral of passing input_values?   This means our values should either
    # be const values, or addresses and the bindings should give us this.  Also input_values 
    # does not make sense because you could refer to values that are coming from a "global"ish
    # scope ie variables local to a function
    return instructions, symtable, ir.ValueOrVar(expr.value, True)

def generate_ir_for_tuple(expr, context, instructions, symtable):
    # First evaluate all child expressions
    child_values = []
    for child in expr.values:
        instructions, symtable, value = generate_ir_for_expression(child, context, instructions, symtable)
        child_values.append(value)
    return instructions, symtable, child_values

def generate_ir_for_list(expr, context, instructions, symtable):
    # First evaluate all child expressions
    child_values = []
    for child in expr.values:
        instructions, symtable, value = generate_ir_for_expression(child, context, instructions, symtable)
        child_values.append(value)
    return instructions, symtable, ir.ValueOrVar(child_values, True)

def generate_ir_for_dict(expr, context, instructions, symtable):
    # TBD
    out = {}
    for k,v in expr.values.iteritems():
        instructions, symtable, key_values = generate_ir_for_expression(k, context, instructions, symtable)
        instructions, symtable, value_values = generate_ir_for_expression(v, context, instructions, symtable)
        out[key_values] = value_values
    return instructions, symtable, out

def generate_ir_for_function_call(expr, context, instructions, symtable):
    # Evaluate parameter values
    arg_values = []
    for arg in expr.func_args:
        instructions, symtable, value = generate_ir_for_expression(arg, context, instructions, symtable)
        arg_values.append(value)
    new_register = symtable.next_register(expr.evaluated_typeexpr)
    instructions.append(ir.FunctionCallInstruction(expr.func_expr.root_value.fqn, arg_values, new_register))
    return instructions, symtable, new_register

def generate_ir_for_if_expression(ifexpr, context, instructions, symtable):
    top_ifinstr = None
    curr_instrs = instructions
    for condition,expr in ifexpr.cases:
        # we are dealing with first condition
        cond_instrs, symtable, value = generate_ir_for_expression(condition, context, curr_instrs, symtable)
        body_instrs, symtable, _ = generate_ir_for_expression(expr, context, None, symtable)
        ifinstr = ir.IfStatement(ir.ValueOrVar(value, True), body_instrs)
        if not top_ifinstr: top_ifinstr = ifinstr
        curr_instrs.append(ifinstr)
        curr_instrs = ifinstr.otherwise

    if ifexpr.default_expression:
        generate_ir_for_expression(ifexpr.default_expression, context, curr_instrs, symtable)
    return instructions, symtable, top_ifinstr

def generate_ir_for_variable(target_var, context, instructions, symtable):
    starting_var, field_path = target_var.field_path.pop()

    # We would never directly generate a getter/setter for functions
    # (though langauge allows it we dont have the need to pass functions,,, yet)
    assert not target_var.is_function

    # if str(target_var.field_path) == "src/statusCode": ipdb.set_trace()
    curr_typearg = target_var.root_value
    # if not curr_typearg: ipdb.set_trace()
    curr_path = starting_var
    curr_register = symtable.get_register_for_path(starting_var)
    curr_instrs = instructions
    while field_path.length > 0:
        next_field_name, tail_path = field_path.pop()
        next_path = curr_path + "/" + next_field_name
        if curr_typearg is None:
            ipdb.set_trace()
        next_typearg = curr_typearg.type_expr.resolved_value.args.withname(next_field_name)
        next_register = symtable.get_register_for_path(next_path, next_typearg.type_expr)

        # Get the next var and store into the var
        contains_instr = ir.ContainsInstruction(curr_register, next_field_name)
        get_instr = ir.GetFieldInstruction(curr_register, next_field_name, next_register)
        if_stmt = ir.IfStatement(contains_instr, [ get_instr ], None)
        curr_instrs.append(if_stmt)
        curr_instrs = if_stmt.body
        curr_path, curr_register, field_path = next_path, next_register, tail_path

    return instructions, symtable, curr_register


def generate_ir_for_setter(source_register, target_var, instructions, symtable):
    if not target_var:
        return instructions, symtable, None

    starting_var, field_path = target_var.field_path.pop()
    starting_register = symtable.get_register_for_path(starting_var)
    if target_var.is_temporary and field_path.length == 0:
        # Do a direct copy as no nesting into a local var
        instructions.append(ir.CopyVarInstruction(source_register, starting_register))
        return instructions, symtable, None

    curr_typearg = target_var.root_value
    curr_register = starting_register
    curr_path = starting_var
    while field_path.length > 1:
        # At each level of the remaining field paths, keep finding and setting fields if they are null
        next_field_name, tail_path = field_path.pop()
        next_path = curr_path + "/" + next_field_name
        next_typearg = curr_typearg.type_expr.resolved_value.args.withname(next_field_name)
        next_register = symtable.get_register_for_path(next_path, next_typearg.type_expr)

        # Get the next register and store into the register
        contains_instr = ir.ContainsInstruction(curr_register, next_field_name)
        set_default_instr = ir.NewInstruction(curr_typearg, next_register)
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
