
import ipdb
from typelib import core as tlcore
from onering.codegen.symtable import SymbolTable
from onering.codegen import ir
from typelib.core import Expr, Variable, Fun, FunApp
from typelib.ext import ListExpr, DictExpr, TupleExpr, IfExpr, ExprList, Assignment, Literal

"""
This module is responsible for generating code for a statement and all parts of an expr tree.
"""

def generate_ir_for_expr(expr, resolver_stack, instructions, symtable):
    if instructions is None: instructions = []
    if symtable is None: symtable = SymbolTable()

    if expr is None:
        return instructions, symtable, None

    irgenerators = {
        Literal: generate_ir_for_literal,
        TupleExpr: generate_ir_for_tuple,
        ListExpr: generate_ir_for_list,
        DictExpr: generate_ir_for_dict,
        FunApp: generate_ir_for_fun_app,
        Variable: generate_ir_for_variable,
        IfExpr: generate_ir_for_if_expr,
        Assignment: generate_ir_for_assignment,
        ExprList: generate_ir_for_expr_list,
    }
    t = type(expr)
    if t not in irgenerators:
        ipdb.set_trace()
    return irgenerators[t](expr, resolver_stack, instructions, symtable)

def generate_ir_for_function(function, resolver_stack):
    symtable = SymbolTable()
    assert not function.is_external, "External functions cannot be generated"

    # Set source and dest variables in symbol table
    for typearg in function.source_typeargs:
        symtable.register_var(typearg.name, typearg.type_expr, False)
    if not function.returns_void:
        symtable.register_var(function.dest_typearg.name, function.dest_typearg, False)
    instructions, symtable, _ = generate_ir_for_expr(function.expr, resolver_stack, [], symtable = symtable)
    return instructions, symtable

def generate_ir_for_expr_list(expr_list, resolver_stack, instructions, symtable):
    """
    Generates the IR for a bunch of statements and returns the instruction list as well as the final symbol table required.
    """
    assert instructions is not None and symtable is not None
    # Now do the normal generation
    last_register = None
    for index,expr in enumerate(expr_list.children):
        instructions, symtable, last_register = generate_ir_for_expr(expr, resolver_stack, instructions, symtable)
    return instructions, symtable, last_register

def generate_ir_for_assignment(assignment, resolver_stack, instructions, symtable):
    # Generate all "temp" vars across all statements first
    target_var = assignment.target_variable.field_path.get(0)
    if assignment.parent_function.is_temp_variable(target_var):
        # Since the assignment is to a temporary var, now is a chance to set the temp var's
        # type if it is not already set
        exprtype = assignment.evaltype(resolver_stack)
        if assignment.parent_function.temp_var_type(target_var) is None:
            assignment.parent_function.register_temp_var(target_var, exprtype)
        symtable.register_var(target_var, exprtype, True)

    # Call the the generator for the expr with the last return value as its inputs
    instructions, symtable, last_register = generate_ir_for_expr(assignment.expr, resolver_stack, instructions, symtable)

    # Generate a setter instruction too
    generate_ir_for_setter(last_register, assignment.target_variable, resolver_stack, instructions, symtable)

    # Statements dont have return values
    return instructions, symtable, None

def generate_ir_for_literal(expr, resolver_stack, instructions, symtable):
    # So there are no explicit "inputs", just locations or values that something is bound to
    # then why the rigmoral of passing input_values?   This means our values should either
    # be const values, or addresses and the bindings should give us this.  Also input_values 
    # does not make sense because you could refer to values that are coming from a "global"ish
    # scope ie variables local to a function
    return instructions, symtable, ir.ValueOrVar(expr.value, True)

def generate_ir_for_tuple(expr, resolver_stack, instructions, symtable):
    # First evaluate all child exprs
    child_values = []
    for child in expr.values:
        instructions, symtable, value = generate_ir_for_expr(child, resolver_stack, instructions, symtable)
        child_values.append(value)
    return instructions, symtable, child_values

def generate_ir_for_list(expr, resolver_stack, instructions, symtable):
    # First evaluate all child exprs
    child_values = []
    for child in expr.values:
        instructions, symtable, value = generate_ir_for_expr(child, resolver_stack, instructions, symtable)
        child_values.append(value)
    return instructions, symtable, ir.ValueOrVar(child_values, True)

def generate_ir_for_dict(expr, resolver_stack, instructions, symtable):
    # TBD
    out = {}
    for k,v in expr.values.iteritems():
        instructions, symtable, key_values = generate_ir_for_expr(k, resolver_stack, instructions, symtable)
        instructions, symtable, value_values = generate_ir_for_expr(v, resolver_stack, instructions, symtable)
        out[key_values] = value_values
    return instructions, symtable, out

def generate_ir_for_fun_app(expr, resolver_stack, instructions, symtable):
    # Evaluate parameter values
    if expr.is_type_app:
        ipdb.set_trace()
    arg_values = []
    for arg in expr.func_args:
        instructions, symtable, value = generate_ir_for_expr(arg, resolver_stack, instructions, symtable)
        arg_values.append(value)
    function = expr.func_expr.resolve(resolver_stack)
    func_type = function.func_type
    new_register = None
    if func_type.output_arg:
        output_type = func_type.output_arg.type_expr.resolve(resolver_stack)
        new_register = symtable.next_register(output_type)
    instructions.append(ir.FunAppInstruction(function.fqn, arg_values, new_register))
    return instructions, symtable, new_register

def generate_ir_for_if_expr(ifexpr, resolver_stack, instructions, symtable):
    top_ifinstr = None
    curr_instrs = instructions
    for condition,expr in ifexpr.cases:
        # we are dealing with first condition
        cond_instrs, symtable, value = generate_ir_for_expr(condition, resolver_stack, curr_instrs, symtable)
        body_instrs, symtable, _ = generate_ir_for_expr(expr, resolver_stack, None, symtable)
        ifinstr = ir.IfStatement(ir.ValueOrVar(value, True), body_instrs)
        if not top_ifinstr: top_ifinstr = ifinstr
        curr_instrs.append(ifinstr)
        curr_instrs = ifinstr.otherwise

    if ifexpr.default_expr:
        generate_ir_for_expr(ifexpr.default_expr, resolver_stack, curr_instrs, symtable)
    return instructions, symtable, top_ifinstr

def generate_ir_for_variable(target_var, resolver_stack, instructions, symtable):
    # We would never directly generate a getter/setter for functions
    # (though core allows it we dont have the need to pass functions,,, yet)
    value = target_var.resolve(resolver_stack)
    assert type(value) is tlcore.TypeArg

    curr_register = None
    curr_instrs = instructions
    for curr_field_name, curr_path, curr_typearg in value.unwrap_with_field_path(target_var.field_path, resolver_stack):
        last_register = curr_register
        if curr_register is None:
            curr_register = symtable.get_register_for_path(curr_field_name)
        else:
            curr_type = curr_typearg.type_expr.resolve(resolver_stack)
            curr_register = symtable.get_register_for_path(curr_path, curr_type)
            # Get the next var and store into the var
            contains_instr = ir.ContainsInstruction(last_register, curr_field_name)
            get_instr = ir.GetFieldInstruction(last_register, curr_field_name, curr_register)
            if_stmt = ir.IfStatement(contains_instr, [ get_instr ], None)
            curr_instrs.append(if_stmt)
            curr_instrs = if_stmt.body

    return instructions, symtable, curr_register


def generate_ir_for_setter(source_register, target_var, resolver_stack, instructions, symtable):
    if not target_var:
        ipdb.set_trace()
        return instructions, symtable, None

    # if "dest/status" == str(target_var.field_path): ipdb.set_trace()
    value = target_var.resolve(resolver_stack)
    if type(value) is not tlcore.TypeArg:
        ipdb.set_trace()
    curr_register = None
    curr_instrs = instructions
    for curr_field_name, curr_path, curr_typearg in value.unwrap_with_field_path(target_var.field_path, resolver_stack):
        last_register = curr_register
        if curr_register is None:
            curr_register = symtable.get_register_for_path(curr_field_name)
        else:
            curr_type = curr_typearg.type_expr.resolve(resolver_stack)
            curr_register = symtable.get_register_for_path(curr_path, curr_type)
            # Get the next var and store into the var
            contains_instr = ir.ContainsInstruction(last_register, curr_field_name)
            set_default_instr = ir.NewInstruction(curr_typearg, curr_register)
            if_stmt = ir.IfStatement(contains_instr, [ set_default_instr ], None, negate = True)
            instructions.append(if_stmt)

            get_instr = ir.GetFieldInstruction(last_register, curr_field_name, curr_register)
            instructions.append(get_instr)

    if not last_register:
        # Do a copy
        instructions.append(ir.CopyVarInstruction(source_register, curr_register))
    else:
        instructions.append(ir.SetFieldInstruction(source_register, target_var.field_path.get(-1), last_register))
    return instructions, symtable, None
