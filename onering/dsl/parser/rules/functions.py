
from __future__ import absolute_import
import ipdb
from typelib import core as tlcore
from typelib import functions as tlfunctions
from onering import utils
from onering.dsl.parser.rules.types import ensure_typeref
from onering.dsl.errors import SourceException, UnexpectedTokenException
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations
from onering.dsl.parser.rules.misc import parse_field_path
from onering.core import exprs as orexprs
from onering.core import functions as orfuncs

########################################################################
##          Function type and definition parsing rules
########################################################################

def parse_function(parser, annotations, **kwargs):
    """Parses a function declaration.

    function        :=  function_type function_body ? 
    function_type   :=  "fun" name<IDENT>   input_params ? ( ":" output_type )
    function_body   := "{" stream_statement * "}"
    """
    docs = parser.last_docstring()
    parser.ensure_token(TokenType.IDENTIFIER, "fun")

    func_name = parser.ensure_token(TokenType.IDENTIFIER)

    input_types, output_typeref = parse_function_signature(parser)
    parent = parser.current_module if func_name else None
    functype = tlfunctions.FunctionType(func_name, parent, input_types, output_typeref, annotations = annotations, docs = docs)
    if parser.peeked_token_is(TokenType.OPEN_BRACE):
        # Brace yourself for a function definition!!!
        function = orfuncs.Function(func_name, parser.current_module, functype, annotations = annotations, docs = docs)
        parser.add_entity(function)
        statements = parse_function_body(parser, function)
        return function
    else:
        # Return a function type
        functyperef = tlcore.EntityRef(functype, func_name, parser.current_module, annotations = annotations, docs = docs)
        parser.add_entity(functyperef)
        return functyperef

def parse_function_signature(parser, require_param_name = True):
    """Parses the type signature declaration in a function declaration:

        function_signature      ::  input_params ? ( ":" output_typeref ) ?

        input_type_signature    ::  "(" param_decls ? ")"

        param_decls             ::  param_decl ( "," param_decl ) *

        param_decl              ::  ( param_name<IDENT> ":" ) ?   // if param names are optional
                                        param_type

    Returns:
        Returns the input typeref list and the output typeref (both being optional)
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
    output_typeref = None
    if parser.next_token_is(TokenType.COLON):
        output_typeref = ensure_typeref(parser)

    return input_params, output_typeref

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

    param_typeref   = ensure_typeref(parser)
    is_optional     = parser.next_token_is(TokenType.QMARK)
    default_value   = None
    if parser.next_token_is(TokenType.EQUALS):
        default_value = parser.ensure_literal_value()

    return tlfunctions.ParamTypeArg(param_name, param_typeref, is_optional, default_value, annotations, docstring)

def parse_function_body(parser, function):
    statements = []
    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        statement = parse_statement(parser, function)
        statements.append(statement)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    parser.consume_tokens(TokenType.SEMI_COLON)
    return statements

def parse_statement(parser, function):
    """
    Parses a single statement.

        statement := let_statment | stream_expr

        let_statement := "let" stream_expr

        stream_expr := expr ( => expr ) * => expr
    """
    annotations = parse_annotations(parser)

    is_temporary = False
    if parser.next_token_is(TokenType.IDENTIFIER, "let"):
        exprs = parse_expression_chain(parser)
        is_temporary = True
    else:
        exprs = parse_expression_chain(parser)

    # An expression must have more than 1 expression
    if len(exprs) <= 1:
        raise OneringException("A rule statement must have at least one expression")

    # ensure last var IS a variable expression
    if not isinstance(exprs[-1], orexprs.VariableExpression):
        raise OneringException("Final target of an expression MUST be a variable")

    parser.consume_tokens(TokenType.SEMI_COLON)
    return orexprs.Statement(exprs[:-1], exprs[-1], is_temporary)

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
        out = orexprs.LiteralExpression(parser.next_token().value)
    elif parser.peeked_token_is(TokenType.STRING):
        out = orexprs.LiteralExpression(parser.next_token().value)
    elif parser.peeked_token_is(TokenType.OPEN_SQUARE):
        # Read a list
        out = parse_list_expression(parser)
    elif parser.peeked_token_is(TokenType.OPEN_BRACE):
        out = parse_struct_expression(parser)
    elif parser.peeked_token_is(TokenType.OPEN_PAREN):
        out = parse_tuple_expression(parser)
    elif parser.peeked_token_is(TokenType.IDENTIFIER):
        # See if we have a function call or a var or a field path
        source = parse_field_path(parser, allow_abs_path = False, allow_child_selection = False)
        out = orexprs.VariableExpression(source, readonly = True, source_type = orexprs.VarSource.AUTO)

        func_args = []
        if parser.peeked_token_is(TokenType.OPEN_PAREN):
            # function expression, so ensure field path has only one entry
            if source.length > 1:
                raise OneringException("Fieldpaths cannot be used as functions")

            # Treat the source as a function name that will be resolved later on
            source_name = source.get(0)
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

            # Make sure function exists
            out = orexprs.FunctionCallExpression(source_name, func_args)
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
    return transformers.TupleExpression(exprs)

