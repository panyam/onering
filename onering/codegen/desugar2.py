
from ipdb import set_trace
from typelib import core as tlcore
from typelib.core import Expr, Var, Fun, FunApp
from typelib.ext import ListExpr, DictExpr, TupleExpr, IfExpr, ExprList, Assignment, Literal, NewExpr
from onering.codegen.symtable import SymbolTable
from onering.codegen import ir
from onering.codegen.ir import NotExpr, GetterExpr, SetterExpr

"""
This module is responsible for generating code for a statement and all parts of an expr tree. 
Part of this process is to take the source expression tree, desugaring (and sometimes sugaring) 
it where necessary and creating another (valid) expression tree that can be fed to the renderer.
"""

def get_transformer_for_expr(expr):
    transformers = {
        Literal: default_transformer,
        Assignment: transform_assignment,
        TupleExpr: transform_tuple,
        ListExpr: transform_list,
        DictExpr: transform_dict,
        FunApp: transform_app,
        Var: transform_variable_for_read,
        IfExpr: transform_ifexpr,
        ExprList: transform_exprlist,
    }
    t = type(expr)
    if t not in transformers:
        set_trace()
    return transformers[t]

def transform_function(function):
    symtable = SymbolTable()
    assert not function.is_external, "External functions cannot be generated"
    output = ExprList()
    output.add(symtable)

    # Set source and dest variables in symbol table
    for typearg in function.source_typeargs:
        symtable.register_var(typearg.name, typearg.type_expr.resolve(), False)
    if not function.returns_void:
        symtable.register_var(function.dest_typearg.name, function.dest_typearg.resolve(), False)
    newexpr, _ = transform_expr(function.expr, symtable = symtable)
    output.extend(newexpr)
    newfunc = Fun(function.name, function.fun_type, output, function.parent, function.annotations, function.docs)
    return newfunc, symtable

def transform_expr(expr, symtable):
    """ Expression transformers take the source expression tree and transform them to a form suitable for the target.  
    For instance field paths may need to be converted into a chain of if checks and so on.

    Doing these custom transformations allows better targetting to a particular backend/platform/language.
    """
    if expr is None: return None
    transformer = get_transformer_for_expr(expr)
    return transformer(expr, symtable)

def default_transformer(expr, symtable):
    """ By default an expression is not transformed. """
    return expr, None

def transform_exprlist(expr_list, symtable):
    """ Transform child expressions of an ExprList """
    children = [transform_expr(expr, symtable)[0] for expr in expr_list.children]
    return ExprList(children), None

def transform_assignment(assignment, symtable):
    """ Transform an assignment expression. """
    # Generate all "temp" vars across all statements first
    target_var = assignment.target_variable.field_path.get(0)
    target_register = symtable.get_register_for_path(target_var)
    if target_register.type_unknown:
        # Type is unknown so infer it
        exprtype = assignment.evaltype()
        symtable.register_var(target_var, exprtype, True)

    # Call the the generator for the expr with the last return value as its inputs
    input_expr, last_register = transform_expr(assignment.expr, symtable)

    # Generate a setter instruction too
    setter_expr, target_var = transform_variable_for_write(last_register, assignment.target_variable, symtable)

    output = ExprList()
    output.extend(input_expr)
    output.extend(setter_expr)
    return output, last_register

def transform_tuple(tuple_expr, symtable):
    # First evaluate all child exprs
    children = [transform_expr(expr, symtable)[1] for expr in list_expr.values]
    return TupleExpr(children), None

def transform_list(list_expr, symtable):
    # First evaluate all child exprs
    children = [transform_expr(expr, symtable)[1] for expr in list_expr.values]
    return ListExpr(children), None

def transform_dict(dict_expr, symtable):
    # First evaluate all child exprs
    keys = [transform_expr(expr, symtable)[1] for expr in dict_expr.keys]
    values = [transform_expr(expr, symtable)[1] for expr in dict_expr.values]
    return DictExpr(keys, values), None

def transform_app(expr, symtable):
    # Evaluate parameter values
    arg_exprs = []
    arg_vars = []
    for arg in expr.func_args:
        arg_expr,arg_register = transform_expr(arg, symtable)
        arg_exprs.append(arg_expr)
        arg_vars.append(arg_register)
    function = expr.func_expr.resolve()
    fun_type = function.fun_type

    if expr.is_type_app:
        set_trace()
        fun_app_expr = tlcore.TypeApp(function, arg_vars)
    else:
        fun_app_expr = tlcore.FunApp(function, arg_vars)

    new_register = None
    if fun_type.output_arg:
        output_type = fun_type.output_arg.type_expr.resolve()
        new_register = symtable.next_register(output_type)
        output = Assignment(new_register, fun_app_expr)
    else:
        output = fun_app_expr
    return output, new_register

def transform_ifexpr(ifexpr, symtable):
    case_exprs = [(transform_expr(cond, symtable),
                   transform_expr(cond, symtable)) for cond,body in ifexpr.cases]
    default_expr = None
    if ifexpr.default_expr:
        default_expr, _ = transform_expr(ifexpr.default_expr, symtable)
    return IfExpr(case_exprs, default_expr)

def transform_variable_for_read(target_var, symtable):
    value = target_var.resolve()
    assert type(value) is tlcore.TypeArg

    # Instead of generating a bunch of intermediate variables, this just calls
    # a UDF that traverses the field path and to get its value or a default value
    # suitable for that type
    getter_func = Var("onering.platform.get_field_path_or_default") # .resolve()
    return FunApp(getter_func, target_var.field_path), None

def transform_variable_for_write(source_register, target_var, symtable):
    if not target_var:
        set_trace()
        return None, None

    value = target_var.resolve()
    if type(value) is not tlcore.TypeArg: set_trace()

    if str(target_var.field_path) == "dest/status":
        set_trace()


    if target_var.field_path.length == 1:
        curr_register = symtable.get_register_for_path(target_var.field_path.get(0))
        return Assignment(curr_register, source_register)

    curr_register = None
    curr_expr = output = ExprList()
    # Ensure nothing in the field path is missing
    setter_func = Var("onering.platform.ensure_field_path_or_default") # .resolve()
    output.add(FunApp(setter_func, target_var.field_path))

    for curr_field_name, curr_path, curr_typearg in value.unwrap_with_field_path(target_var.field_path):
        last_register = curr_register
        if curr_register is None:
            curr_register = symtable.get_register_for_path(curr_field_name)
        else:
            curr_type = curr_typearg.type_expr.resolve()
            curr_register = symtable.get_register_for_path(curr_path, curr_type)
            output.add(Assignment(curr_register, GetterExpr(last_register, curr_field_name)))

    output.add(SetterExpr(last_register, target_var.field_path.get(-1), source_register))
    return output, None
