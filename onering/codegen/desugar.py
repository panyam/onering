
from ipdb import set_trace
from typecube import core as tccore
from typecube.core import Expr, Var, Fun, FunApp
from typecube.ext import ListExpr, DictExpr, TupleExpr, IfExpr, ExprList, Assignment, Literal, NewExpr
from onering.codegen.symtable import SymbolTable
from onering.codegen import ir
from onering.codegen.ir import NotExpr, ContainsExpr, GetterExpr, SetterExpr

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
        fun_app_expr = tccore.TypeApp(function, arg_vars)
    else:
        fun_app_expr = tccore.FunApp(function, arg_vars)

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
    # We would never directly generate a getter/setter for functions
    # (though core allows it we dont have the need to pass functions,,, yet)
    if str(target_var.field_path) == "dest/status":
        set_trace()
    value = target_var.resolve()
    assert type(value) is tccore.TypeArg

    curr_register = None
    curr_expr = output = ExprList()
    for curr_field_name, curr_path, curr_typearg in value.unwrap_with_field_path(target_var.field_path):
        last_register = curr_register
        if curr_register is None:
            curr_register = symtable.get_register_for_path(curr_field_name)
        else:
            curr_type = curr_typearg.type_expr.resolve()
            curr_register = symtable.get_register_for_path(curr_path, curr_type)

            # Get the next var and store into the var
            # We need the equiv of:
            #   if (last_register.has<curr_field_name>) {
            #       curr_register = last_register.get<curr_field_name>
            #   }
            if_cond = ContainsExpr(last_register, curr_field_name)
            if_body = ExprList([Assignment(curr_register, GetterExpr(last_register, curr_field_name))])
            if_expr = IfExpr([(if_cond, if_body)], None)
            curr_expr.add(if_expr)
            curr_expr = if_expr
    return output, curr_register

def transform_variable_for_write(source_register, target_var, symtable):
    if not target_var:
        set_trace()
        return None, None

    if str(target_var.field_path) == "dest/status":
        set_trace()

    value = target_var.resolve()
    if type(value) is not tccore.TypeArg: set_trace()

    curr_register = None
    curr_expr = output = ExprList()
    for curr_field_name, curr_path, curr_typearg in value.unwrap_with_field_path(target_var.field_path):
        last_register = curr_register
        if curr_register is None:
            curr_register = symtable.get_register_for_path(curr_field_name)
        else:
            curr_type = curr_typearg.type_expr.resolve()
            curr_register = symtable.get_register_for_path(curr_path, curr_type)

            # What we want is the equiv of:
            # if (! last_reg.has<curr_field_name> ) {
            #    last_reg.set<curr_field_name>(new TypeOf(curr_field_name))
            # }
            if_cond = NotExpr(ContainsExpr(last_register, curr_field_name))
            if_body = SetterExpr(last_register, curr_field_name, NewExpr(curr_typearg))
            output.add(IfExpr([(if_cond, if_body)], None))
            output.add(Assignment(curr_register, GetterExpr(last_register, curr_field_name)))

    if not last_register:
        output.extend(Assignment(curr_register, source_register))
    else:
        output.extend(SetterExpr(last_register, target_var.field_path.get(-1), source_register))
    return output, None
