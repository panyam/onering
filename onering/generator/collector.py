
def collect_symbols_for_statements(statements, context, symtable):
    """
    Goes through all the statements in this transformer and returns a list of all bound variable names and their
    types to form the symbol table for this scope.
    """
    for statement in statements:
        collect_symbols_for_statement(statement, context, symtable)
        

def collect_symbols_for_statement(statement, context, symtable):
    for expr in statement.expressions:
        collect_symbols_for_expression(expr, context, symtable)

    if statement.is_temporary:
        vartype = statement.expressions[-1].evaluated_type
        symtable.register_var_with_type(statement.target_variable.value, vartype)
    else:
        # create a local var of type of the last function call


def collect_symbols_for_expression(expression, context, sym_table):
    """ Nothing to be done as expressions usually dont usually create new variables. """
    pass

