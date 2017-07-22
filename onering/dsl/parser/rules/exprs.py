
from __future__ import absolute_import
from ipdb import set_trace
from typecube import core as tlcore
from typecube import ext as tlext
from typecube.utils import FieldPath
from onering import utils
from onering.dsl import errors
from onering.dsl.parser.rules.types import ensure_typeexpr
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations
from onering.dsl.parser.rules.misc import parse_field_path

def parse_expr_list(parser, function):
    """ Parses a statement block.

    expr_list := "{" expr * "}"

    """
    out = tlext.ExprList()
    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        out.add(parse_statement(parser, function))
    parser.ensure_token(TokenType.CLOSE_BRACE)
    parser.consume_tokens(TokenType.SEMI_COLON)
    return out

def parse_statement(parser, function):
    """
    Parses a single statement.

        statement := let_statment | stream_expr | if_expr

        let_statement := "let" stream_expr

        if_expr := "if" condition "{" statements "}"

        stream_expr := expr ( => expr ) * => expr
    """
    annotations = parse_annotations(parser)

    is_temporary = parser.next_token_is(TokenType.IDENTIFIER, "let")
    expr = parse_expr(parser)
    parser.ensure_token(TokenType.STREAM)
    target_var = parse_expr(parser)

    parser.consume_tokens(TokenType.SEMI_COLON)

    # ensure last var IS a variable expr
    if not isinstance(target_var, tlcore.Var):
        raise errors.OneringException("Final target of an expr MUST be a variable")

    if target_var.field_path.get(0) == '_':
        return expr
    else:
        if is_temporary:
            function.register_temp_var(target_var.field_path.get(0))
        return tlext.Assignment(target_var, expr)

def parse_expr(parser):
    """ Parse a function call expr or a literal.

        expr := literal
                if_expr
                list_expr
                dict_expr
                tuple_expr
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
            vtype = tlext.IntType
        elif type(value) is long:
            vtype = tlext.LongType
        elif type(value) is float:
            vtype = tlext.DoubleType
        else:
            assert False
        out = tlext.Literal(value, vtype)
    elif parser.peeked_token_is(TokenType.STRING):
        out = tlext.Literal(parser.next_token().value, tlext.StringType)
    elif parser.peeked_token_is(TokenType.OPEN_SQUARE):
        # Read a list
        out = parse_list_expr(parser)
    elif parser.peeked_token_is(TokenType.OPEN_BRACE):
        out = parse_dict_expr(parser)
    elif parser.peeked_token_is(TokenType.OPEN_PAREN):
        out = parse_tuple_expr(parser)
    elif parser.peeked_token_is(TokenType.IDENTIFIER, "if"):
        out = parse_if_expr(parser)
    elif parser.peeked_token_is(TokenType.IDENTIFIER):
        # See if we have a function call or a var or a field path
        source = parse_field_path(parser, allow_abs_path = False, allow_child_selection = False)
        out = tlcore.Var(source)

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
            # function expr, so ensure field path has only one entry
            # Treat the source as a function name that will be resolved later on
            parser.ensure_token(TokenType.OPEN_PAREN)
            while not parser.peeked_token_is(TokenType.CLOSE_PAREN):
                # read another expr
                expr = parse_expr(parser)
                func_args.append(expr)
                if parser.next_token_is(TokenType.COMMA):
                    # TODO: ensure next val is an IDENTIFIER or a literal value
                    # Right now lack of this check wont break anything but 
                    # will allow "," at the end which is a bit, well rough!
                    pass
            parser.ensure_token(TokenType.CLOSE_PAREN)

        if func_param_exprs or func_args:
            if source.length > 1:
                raise errors.OneringException("Fieldpaths cannot be used as functions")
            out = tlcore.FunApp(tlcore.Var(source), func_args)
    else:
        raise errors.UnexpectedTokenException(parser.peek_token(),
                                       TokenType.STRING, TokenType.NUMBER,
                                       TokenType.OPEN_BRACE, TokenType.OPEN_SQUARE,
                                       TokenType.LT)
    return out

def parse_tuple_expr(parser):
    parser.ensure_token(TokenType.OPEN_PAREN)
    exprs = []
    if not parser.next_token_is(TokenType.CLOSE_PAREN):
        expr = parse_expr(parser)
        exprs = [expr]
        while parser.next_token_is(TokenType.COMMA):
            expr = parse_expr(parser)
            exprs.append(expr)
        parser.ensure_token(TokenType.CLOSE_PAREN)
    return tlext.TupleExpr(exprs)

def parse_list_expr(parser):
    parser.ensure_token(TokenType.OPEN_SQUARE)
    exprs = []
    if not parser.next_token_is(TokenType.CLOSE_PAREN):
        expr = parse_expr(parser)
        exprs = [expr]
        while parser.next_token_is(TokenType.COMMA):
            expr = parse_expr(parser)
            exprs.append(expr)
        parser.ensure_token(TokenType.CLOSE_SQUARE)
    return tlext.ListExpr(exprs)

def parse_if_expr(parser):
    """ Parse an if expr:

        "if" condition statement_block
        ( "elif" condition statement_block ) *
        ( "else" statement_block ) ?
    Parse an expr chain of the form 

        expr => expr => expr => expr
    """
    parser.ensure_token(TokenType.IDENTIFIER, "if")
    conditions = []
    condition = parse_expr(parser)
    body = parse_expr_list(parser)
    conditions.append((condition, body))
    default_expr = None

    while True:
        if parser.next_token_is(TokenType.IDENTIFIER, "elif"):
            condition = parse_expr(parser)
            body = parse_expr_list(parser)
            conditions.append((condition, body))
        elif parser.next_token_is(TokenType.IDENTIFIER, "else"):
            default_expr = parse_expr_list(parser)
        else:
            break

    return tlext.IfExpr(conditions, default_expr)
