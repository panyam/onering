
import ipdb
from onering.generator.symtable import SymbolTable
from onering.generator import ir
from onering.core.exprs import Expression, LiteralExpression, ListExpression, DictExpression, TupleExpression, FunctionCallExpression, VariableExpression, VarSource

"""
This module is responsible for generating code for a statement and all parts of an expression tree.
"""

SRC_MARKER_VAR = "<src>"
DEST_MARKER_VAR = "<dest>"

def generate_ir_for_transformer(transformer, context):
    instructions = []
    symtable = SymbolTable()

    # Set source and dest variables in symbol table
    symtable.register_var(SRC_MARKER_VAR, transformer.src_typeref)
    symtable.register_var(DEST_MARKER_VAR, transformer.dest_typeref)
    instructions, symtable, _ = generate_ir_for_statements(transformer.all_statements, context)
    return instructions, symtable

def generate_ir_for_statements(statements, context, instructions = None, symtable = None):
    """
    Generates the IR for a bunch of statements and returns the instruction list as well as the final symbol table required.
    """
    if not instructions:
        instructions = []
    if not symtable:
        symtable = SymbolTable()

    for statement in (statements):
        if statement.is_temporary:
            # Register var if this is temporary
            symtable.register_var(statement.target_variable.value, statement.target_variable.evaluated_typeref)
        generate_ir_for_statement(statement, context, instructions, symtable)
    return instructions, symtable, None

def generate_ir_for_statement(statement, context, instructions, symtable):
    """
    Given the statement of the form:

        expr1 => expr2 => expr3 => var

    Each expression is really a function that takes result of previous expression and returns a result 
    (could be empty result - and results written directly to symbol table), so could could be:

        output1 = gen_code(expr1, input = None)
        output2 = gen_code(expr2, input = output1)
        output3 = gen_code(expr3, input = output2)
        assign(output3, var)

    In sync/functional world this is equivalent to:
        var = expr3(expr2(expr1(None)))

    In async/callback world:
        expr1(None).then(function(result1) {
            expr2(result1).then(function(result2) {
                expr3(result2).then(function(result3) {
                    var = result3;
                })
            })
        })

        In promise land:
            expr1(None)
            .then(expr2)
            .then(expr3)
            .then(assign(var));
    """
    last_return = None
    for expr in statement.expressions:
        # Call the the generator for the expression with the last return value as its inputs
        instructions, symtable, last_return = generate_ir_for_expression(expr, context, last_return, instructions, symtable)

    # Generate a setter instruction too
    instructions.append(ir.SetterInstruction(last_return, statement.target_variable))

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
    # then why the rigmore of passing input_values?   This means our values should either
    # be const values, or addresses and the bindings should give us this.  Also input_values does not make sense
    # because you could refer to values that are coming from a "global"ish scope ie variables local to a function
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
    newvar = symtable.next_var(expr.evaluated_typeref)
    instructions.append(ir.FunctionCallInstruction(expr.func_fqn, arg_values, newvar))
    return instructions, symtable, newvar

def generate_ir_for_variable(expr, context, input_values, instructions, symtable):
    # For variables do a getter and store them somewhere but only the first time,
    # otherwise reuse them

    if expr.source_type == VarSource.LOCAL_VAR:
        return instructions, symtable, symtable.get_var(expr.value)
    else:
        resolution_result = expr.resolution_result 
        starting_typeref = resolution_result.root_typeref
        field_path = resolution_result.normalized_field_path
        varname = SRC_MARKER_VAR
        if expr.source_type == VarSource.DEST_FIELD:
            varname = DEST_MARKER_VAR

        # What we want is given a starting variable name and a field path, 
        # last_path = varname
        # last_var = varname
        # last_typeref
        def gen_for_path(last_path, last_var, last_typeref, field_path):
            if not field_path or field_path.length == 0:
                return []

            head, tail_path = field_path.pop()
            next_path = last_path + "/" + head
            next_typeref = last_typeref.final_type.arg_for(head).typeref
            next_var = symtable.get_var_for_path(next_path, next_typeref)
            return [ir.IfStatement(ir.ContainsInstruction(last_var, head),
                                    gen_for_path(next_path, next_var, next_typeref, tail_path)
                                    )]

        instructions.extend(gen_for_path(varname, varname, starting_typeref, field_path))
        ipdb.set_trace()
    return instructions, symtable, newvar
