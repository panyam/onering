
from __future__ import absolute_import
import ipdb
from typelib import core as tlcore
from typelib.utils import FieldPath
from onering import core as orcore
from onering import utils
from onering.dsl.parser.rules.types import ensure_typeexpr
from onering.errors import OneringException
from onering.dsl.errors import SourceException, UnexpectedTokenException
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations
from onering.dsl.parser.rules.misc import parse_field_path
from onering.core import exprs as orexprs

########################################################################
##          Function type and definition parsing rules
########################################################################

def parse_function(parser, is_external, annotations, **kwargs):
    """Parses a function declaration.

    function        :=  function_type function_body ? 
    function_type   :=  "fun" name<IDENT>   "(" input_params ")" ? ( ":" output_type )
    function_body   := "{" stream_statement * "}"
    """
    docs = parser.last_docstring()
    parser.ensure_token(TokenType.IDENTIFIER, "fun")

    from onering.dsl.parser.rules.types import parse_typefunc_preamble
    func_name, type_params, docs = parse_typefunc_preamble(parser, name_required = True)
    input_typeexprs, output_typeexpr, output_varname = parse_function_signature(parser)

    parent = parser.current_module if func_name else None
    functype = tlcore.make_func_type(func_name, type_params, input_typeexprs, output_typeexpr, parent)
    function = tlcore.Function(func_name, functype, parser.current_module, annotations = annotations, docs = docs)
    function.is_external = is_external
    function.dest_varname = output_varname or "dest"
    function.is_external = is_external or not parser.peeked_token_is(TokenType.OPEN_BRACE)
    parser.add_entity(func_name, function)
    parser.onering_context.fgraph.register(function)

    if not function.is_external:
        parse_function_body(parser, function)
    return function

def parse_function_signature(parser, require_param_name = True):
    """Parses the type signature declaration in a function declaration:

        function_signature      ::  input_params ? ( ":" (output_typeexpr ( "as" varname<IDENT> ) ? ) ?

        input_type_signature    ::  "(" param_decls ? ")"

        param_decls             ::  param_decl ( "," param_decl ) *

        param_decl              ::  ( param_name<IDENT> ":" ) ?   // if param names are optional
                                        param_type

    Returns:
        Returns the input typeexpr list and the output typeexpr (both being optional)
    """

    # First read the input params
    input_params = []
    if parser.next_token_is(TokenType.OPEN_PAREN):
        while not parser.peeked_token_is(TokenType.CLOSE_PAREN):
            input_params.append(parse_param_declaration(parser, require_param_name))

            # Consume the COMMA
            if parser.next_token_is(TokenType.COMMA):
                pass
        parser.ensure_token(TokenType.CLOSE_PAREN)

    # Now read the output type (if any)
    output_typeexpr = tlcore.TypeVariable("void")
    output_varname = None
    if parser.next_token_is(TokenType.ARROW):
        output_typeexpr = ensure_typeexpr(parser)
        if parser.next_token_is(TokenType.IDENTIFIER, "as"):
            output_varname = parser.ensure_token(TokenType.IDENTIFIER)

    return input_params, output_typeexpr, output_varname

def parse_param_declaration(parser, require_name = True):
    """
        param_declaration := annotations ?
                             ( name<IDENTIFIER> ":" ) ?
                             type_decl
                             "?" ?                      // Optionality
                             ( "=" literal_value ) ?
    """
    annotations = parse_annotations(parser)
    docstring = parser.last_docstring()

    param_name = None
    if require_name:
        param_name = parser.ensure_token(TokenType.IDENTIFIER)
        parser.ensure_token(TokenType.COLON)
    elif parser.peeked_token_is(TokenType.IDENTIFIER) and \
                parser.peeked_token_is(TokenType.COLON, offset = 1):
        param_name = parser.ensure_token(TokenType.IDENTIFIER)
        parser.ensure_token(TokenType.COLON)

    param_typeexpr  = ensure_typeexpr(parser)
    # if we declared an inline Type then dont refer to it directly but via a Variable
    if type(param_typeexpr) is tlcore.TypeFunction and param_typeexpr.name:
        param_typeexpr = tlcore.TypeVariable(param_typeexpr.name)
    is_optional     = parser.next_token_is(TokenType.QMARK)
    default_value   = None
    if parser.next_token_is(TokenType.EQUALS):
        default_value = parser.ensure_literal_value()

    return tlcore.TypeArg(param_name, param_typeexpr, is_optional, default_value, annotations, docstring)

def parse_function_body(parser, function):
    if not parser.peeked_token_is(TokenType.OPEN_BRACE):
        function.is_external = True
    else:
        for statement in parse_statement_block(parser):
            function.add_statement(statement)

def parse_statement_block(parser):
    """ Parses a statement block.

    statment_block := "{" statement * "}"

    """
    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        yield parse_statement(parser)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    parser.consume_tokens(TokenType.SEMI_COLON)

def parse_statement(parser):
    """
    Parses a single statement.

        statement := let_statment | stream_expr | if_expr

        let_statement := "let" stream_expr

        if_expr := "if" condition "{" statements "}"

        stream_expr := expr ( => expr ) * => expr
    """
    annotations = parse_annotations(parser)

    is_temporary = False
    is_funccall = False
    if parser.next_token_is(TokenType.IDENTIFIER, "let"):
        exprs = parse_expression_chain(parser)
        is_temporary = True
    else:
        exprs = parse_expression_chain(parser)

    # An expression must have more than 1 expression
    if len(exprs) <= 1:
        ipdb.set_trace()
        raise OneringException("A rule statement must have at least one expression")

    parser.consume_tokens(TokenType.SEMI_COLON)

    # ensure last var IS a variable expression
    if not isinstance(exprs[-1], tlcore.Variable):
        raise OneringException("Final target of an expression MUST be a variable")
    return tlcore.Statement(exprs[:-1], exprs[-1], is_temporary)

def parse_expression_chain(parser):
    """
    Parse an expression chain of the form 

        expr => expr => expr => expr
    """
    out = [ parse_expression(parser) ]

    # if the next is a "=>" then start streaming!
    while parser.peeked_token_is(TokenType.STREAM):
        parser.ensure_token(TokenType.STREAM)
        out.append(parse_expression(parser))
    return out

def parse_expression(parser):
    """
    Parse a function call expression or a literal.

        expr := literal
                if_expression
                list_expression
                dict_expression
                tuple_expression
                dot_delimited_field_path
                stream_expr
                expr "[" key "]"
                func_fqn "(" ")"
                func_fqn "(" expr ( "," expr ) * ")"
    """
    out = None
    if parser.peeked_token_is(TokenType.NUMBER):
        value = parser.next_token().value
        if type(value) is int:
            parser.onering_context.IntType
        elif type(value) is long:
            parser.onering_context.LongType
        elif type(value) is float:
            parser.onering_context.DoubleType
        else:
            assert False
        out = orexprs.LiteralExpression(value, vtype)
    elif parser.peeked_token_is(TokenType.STRING):
        out = orexprs.LiteralExpression(parser.next_token().value, orcore.StringType)
    elif parser.peeked_token_is(TokenType.OPEN_SQUARE):
        # Read a list
        out = parse_list_expression(parser)
    elif parser.peeked_token_is(TokenType.OPEN_BRACE):
        out = parse_struct_expression(parser)
    elif parser.peeked_token_is(TokenType.OPEN_PAREN):
        out = parse_tuple_expression(parser)
    elif parser.peeked_token_is(TokenType.IDENTIFIER, "if"):
        out = parse_if_expression(parser)
    elif parser.peeked_token_is(TokenType.IDENTIFIER):
        # See if we have a function call or a var or a field path
        source = parse_field_path(parser, allow_abs_path = False, allow_child_selection = False)
        out = tlcore.Variable(source)

        # check if we have a function call
        func_param_exprs = []
        func_args = []
        if parser.next_token_is(parser.GENERIC_OPEN_TOKEN):
            func_param_exprs = [ ensure_typeexpr(parser) ]
            while not parser.peeked_token_is(parser.GENERIC_CLOSE_TOKEN):
                parser.ensure_token(TokenType.COMMA)
                func_param_exprs.append(ensure_typeexpr(parser))
            parser.ensure_token(parser.GENERIC_CLOSE_TOKEN)

        if func_param_exprs or parser.peeked_token_is(TokenType.OPEN_PAREN):
            # function expression, so ensure field path has only one entry
            # Treat the source as a function name that will be resolved later on
            parser.ensure_token(TokenType.OPEN_PAREN)
            while not parser.peeked_token_is(TokenType.CLOSE_PAREN):
                # read another expression
                expr = parse_expression(parser)
                func_args.append(expr)
                if parser.next_token_is(TokenType.COMMA):
                    # TODO: ensure next val is an IDENTIFIER or a literal value
                    # Right now lack of this check wont break anything but 
                    # will allow "," at the end which is a bit, well rough!
                    pass
            parser.ensure_token(TokenType.CLOSE_PAREN)

        if func_param_exprs or func_args:
            if source.length > 1:
                raise OneringException("Fieldpaths cannot be used as functions")
            out = tlcore.FunctionCall(tlcore.Variable(source), func_param_exprs, func_args)
    else:
        raise UnexpectedTokenException(parser.peek_token(),
                                       TokenType.STRING, TokenType.NUMBER,
                                       TokenType.OPEN_BRACE, TokenType.OPEN_SQUARE,
                                       TokenType.LT)
    return out

def parse_tuple_expression(parser):
    parser.ensure_token(TokenType.OPEN_PAREN)
    exprs = []
    if not parser.next_token_is(TokenType.CLOSE_PAREN):
        expr = parse_expression(parser)
        exprs = [expr]
        while parser.next_token_is(TokenType.COMMA):
            expr = parse_expression(parser)
            exprs.append(expr)
        parser.ensure_token(TokenType.CLOSE_PAREN)
    return orexprs.TupleExpression(exprs)

def parse_list_expression(parser):
    parser.ensure_token(TokenType.OPEN_SQUARE)
    exprs = []
    if not parser.next_token_is(TokenType.CLOSE_PAREN):
        expr = parse_expression(parser)
        exprs = [expr]
        while parser.next_token_is(TokenType.COMMA):
            expr = parse_expression(parser)
            exprs.append(expr)
        parser.ensure_token(TokenType.CLOSE_SQUARE)
    return orexprs.ListExpression(exprs)

def parse_if_expression(parser):
    """ Parse an if expression:

        "if" condition statement_block
        ( "elif" condition statement_block ) *
        ( "else" statement_block ) ?
    Parse an expression chain of the form 

        expr => expr => expr => expr
    """
    parser.ensure_token(TokenType.IDENTIFIER, "if")
    conditions = []
    condition = parse_expression(parser)
    body = list(parse_statement_block(parser))
    conditions.append((condition, body))
    default_expression = None

    while True:
        if parser.next_token_is(TokenType.IDENTIFIER, "elif"):
            condition = parse_expression(parser)
            body = list(parse_statement_block(parser))
            conditions.append((condition, body))
        elif parser.next_token_is(TokenType.IDENTIFIER, "else"):
            default_expression = list(parse_statement_block(parser))
        else:
            break

    return orexprs.IfExpression(conditions, default_expression)

