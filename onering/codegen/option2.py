
import ipdb
from typelib import core as tlcore
from typelib.core import Expr, Var, Fun, FunApp
from typelib.ext import ListExpr, DictExpr, TupleExpr, IfExpr, ExprList, Assignment, Literal, NewExpr
from onering.codegen.symtable import SymbolTable
from onering.codegen import ir
from onering.codegen.ir import NotExpr, ContainsExpr, GetterExpr, SetterExpr

"""
This module is responsible for generating code for a statement and all parts of an expr tree.
"""

def generate_ir_for_function(function, resolver_stack):
    symtable = SymbolTable()
    assert not function.is_external, "External functions cannot be generated"

    # Set source and dest variables in symbol table
    for typearg in function.source_typeargs:
        symtable.register_var(typearg.name, typearg.type_expr.resolve(resolver_stack), False)
    if not function.returns_void:
        symtable.register_var(function.dest_typearg.name, function.dest_typearg.resolve(resolver_stack), False)
    expr = expr_transformer(function.expr, resolver_stack, symtable = symtable)
    return expr, symtable

def expr_transformer(expr, resolver_stack, symtable):
    """ Expression transformers take the source expression tree and transform them to a form suitable for the target.  
    For instance field paths may need to be converted into a chain of if checks and so on.

    Doing these custom transformations allows better targetting to a particular backend/platform/language.
    """
    if expr is None:
        return None

    transformers = {
        Literal: default_transformer,
        Assignment: assignment_transformer,
        TupleExpr: tuple_transformer,
        ListExpr: list_transformer,
        DictExpr: dict_transformer,
        FunApp: funapp_transformer,
        Var: variable_transformer,
        IfExpr: ifexpr_transformer,
        ExprList: exprlist_transformer,
    }
    t = type(expr)
    if t not in transformers:
        ipdb.set_trace()
    return transformers[t](expr, resolver_stack, symtable)

def default_transformer(expr, resolver_stack, symtable):
    """ By default an expression is not transformed. """
    return expr, None

def exprlist_transformer(expr_list, resolver_stack, symtable):
    """ Transform child expressions of an ExprList """
    return ExprList([expr_transformer(expr, resolver_stack, symtable) for expr in expr_list.children]), None

def assignment_transformer(assignment, resolver_stack, symtable):
    """ Transform an assignment expression. """
    # Generate all "temp" vars across all statements first
    target_var = assignment.target_variable.field_path.get(0)
    target_register = symtable.get_register_for_path(target_var)
    if target_register.type_unknown:
        # Type is unknown so infer it
        exprtype = assignment.evaltype(resolver_stack)
        symtable.register_var(target_var, exprtype, True)

    # Call the the generator for the expr with the last return value as its inputs
    input_expr, last_register = expr_transformer(assignment.expr, resolver_stack, symtable)

    # Generate a setter instruction too
    setter_expr, target_var = setter_transformer(last_register, assignment.target_variable, resolver_stack, symtable)

    output = ExprList()
    output.extend(input_expr)
    output.extend(setter_expr)
    return output, last_register

def tuple_transformer(tuple_expr, resolver_stack, symtable):
    # First evaluate all child exprs
    return TupleExpr([expr_transformer(expr, resolver_stack, symtable) for expr in tuple_expr.values]), None

def list_transformer(list_expr, resolver_stack, symtable):
    # First evaluate all child exprs
    return ListExpr([expr_transformer(expr, resolver_stack, symtable) for expr in list_expr.values]), None

def dict_transformer(dict_expr, resolver_stack, symtable):
    # First evaluate all child exprs
    keys = [expr_transformer(expr, resolver_stack, symtable) for expr in dict_expr.keys]
    values = [expr_transformer(expr, resolver_stack, symtable) for expr in dict_expr.values]
    return DictExpr(keys, values), None

def funapp_transformer(expr, resolver_stack, symtable):
    # Evaluate parameter values
    arg_exprs = []
    arg_vars = []
    for arg in expr.func_args:
        arg_expr,arg_register = expr_transformer(arg, resolver_stack, symtable)
        arg_exprs.append(arg_expr)
        arg_vars.append(arg_register)
    function = expr.func_expr.resolve(resolver_stack)
    fun_type = function.fun_type

    if expr.is_type_app:
        ipdb.set_trace()
        fun_app_expr = tlcore.TypeApp(function, arg_exprs)
    else:
        fun_app_expr = tlcore.FunApp(function, arg_exprs)

    new_register = None
    if fun_type.output_arg:
        output_type = fun_type.output_arg.type_expr.resolve(resolver_stack)
        new_register = symtable.next_register(output_type)
        output = Assignment(new_register, fun_app_expr)
    else:
        output = fun_app_expr
    return output, new_register

def ifexpr_transformer(ifexpr, resolver_stack, symtable):
    case_exprs = [(expr_transformer(cond, resolver_stack, symtable),
                   expr_transformer(cond, resolver_stack, symtable)) for cond,body in ifexpr.cases]
    default_expr = None
    if ifexpr.default_expr:
        default_expr, _ = expr_transformer(ifexpr.default_expr, resolver_stack, symtable)
    return IfExpr(case_exprs, default_expr)

def variable_transformer(target_var, resolver_stack, symtable):
    # We would never directly generate a getter/setter for functions
    # (though core allows it we dont have the need to pass functions,,, yet)
    value = target_var.resolve(resolver_stack)
    assert type(value) is tlcore.TypeArg

    curr_register = None
    curr_expr = output = ExprList()
    for curr_field_name, curr_path, curr_typearg in value.unwrap_with_field_path(target_var.field_path, resolver_stack):
        last_register = curr_register
        if curr_register is None:
            curr_register = symtable.get_register_for_path(curr_field_name)
        else:
            curr_type = curr_typearg.type_expr.resolve(resolver_stack)
            curr_register = symtable.get_register_for_path(curr_path, curr_type)

            # Get the next var and store into the var
            # We need the equiv of:
            #   if (last_register.has<curr_field_name>) {
            #       curr_register = last_register.get<curr_field_name>
            #   }
            if_cond = ContainsExpr(last_register, Var(curr_field_name))
            if_body = ExprList([Assignment(curr_register, GetterExpr(last_register, curr_field_name))])
            if_expr = IfExpr([(if_cond, if_body)], None)
            curr_expr.add(if_expr)
            curr_expr = if_expr
    return output, curr_register


def setter_transformer(source_register, target_var, resolver_stack, symtable):
    if not target_var:
        ipdb.set_trace()
        return None, None

    value = target_var.resolve(resolver_stack)
    if type(value) is not tlcore.TypeArg:
        ipdb.set_trace()

    curr_register = None
    curr_expr = output = ExprList()
    for curr_field_name, curr_path, curr_typearg in value.unwrap_with_field_path(target_var.field_path, resolver_stack):
        last_register = curr_register
        if curr_register is None:
            curr_register = symtable.get_register_for_path(curr_field_name)
        else:
            curr_type = curr_typearg.type_expr.resolve(resolver_stack)
            curr_register = symtable.get_register_for_path(curr_path, curr_type)

            # What we want is the equiv of:
            # if (! last_reg.has<curr_field_name> ) {
            #    last_reg.set<curr_field_name>(new TypeOf(curr_field_name))
            # }
            if_cond = NotExpr(ContainsExpr(last_register, Var(curr_field_name)))
            if_body = SetterExpr(last_register, curr_field_name, NewExpr(curr_typearg))
            output.add(IfExpr([(if_cond, if_body)], None))
            output.add(Assignment(curr_register, GetterExpr(last_register, curr_field_name)))

    if not last_register:
        # Do a copy
        output.extend(Assignment(curr_register, source_register))
    else:
        output.extend(SetterExpr(last_register, target_var.field_path.get(-1), source_register))
    return output, None
