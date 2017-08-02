
from __future__ import absolute_import
from ipdb import set_trace
from typecube import core as tccore
from typecube import ext as tcext
from onering import utils
from onering.dsl import errors
from onering.dsl.parser.rules.types import ensure_typeexpr
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations

def parse_expr_list(parser):
    """ Parses a statement block.

    expr_list := "{" expr * "}"

    """
    out = tcext.ExprList()
    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        out.add(parse_statement(parser))
    parser.ensure_token(TokenType.CLOSE_BRACE)
    parser.consume_tokens(TokenType.SEMI_COLON)
    return out

def parse_statement(parser):
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
    target = parse_expr(parser)

    parser.consume_tokens(TokenType.SEMI_COLON)

    # ensure last var IS a variable expr
    if not target.isa(tccore.Var) and not target.isa(tcext.Index):
        raise errors.OneringException("Final target of an expr MUST be a variable or an index expression")

    if target.isa(tccore.Var) and target.name == '_':
        return expr
    else:
        return tcext.Assignment(target, expr, is_temporary)

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
            vtype = tcext.IntType
        elif type(value) is long:
            vtype = tcext.LongType
        elif type(value) is float:
            vtype = tcext.DoubleType
        else:
            assert False
        out = tcext.Literal(value, vtype)
    elif parser.peeked_token_is(TokenType.STRING):
        out = tcext.Literal(parser.next_token().value, tcext.StringType)
    elif parser.peeked_token_is(TokenType.OPEN_SQUARE):
        # Read a list
        out = parse_list_expr(parser)
    elif parser.peeked_token_is(TokenType.OPEN_BRACE):
        out = parse_expr_list(parser)
    elif parser.peeked_token_is(TokenType.OPEN_PAREN):
        out = parse_tuple_expr(parser)
    elif parser.peeked_token_is(TokenType.IDENTIFIER, "if"):
        out = parse_if_expr(parser)
    elif parser.peeked_token_is(TokenType.IDENTIFIER):
        # See if we have a variable or an index chain expression
        out = parse_index_expr(parser)

        # check if we have a function call and also check if function call
        # is a call to a function of a generic function type!
        func_param_exprs = []
        if parser.next_token_is(parser.GENERIC_OPEN_TOKEN):
            func_param_exprs = [ ensure_typeexpr(parser) ]
            while not parser.peeked_token_is(parser.GENERIC_CLOSE_TOKEN):
                parser.ensure_token(TokenType.COMMA)
                func_param_exprs.append(ensure_typeexpr(parser))
            parser.ensure_token(parser.GENERIC_CLOSE_TOKEN)

            # Yep we have a type func being instantiated so
            # dont forget to return a func_app whose function is a type_app!
            out = tccore.QuantApp(out, func_param_exprs)

        func_args = []
        if parser.next_token_if(TokenType.OPEN_PAREN, consume = True):
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
            out = tccore.FunApp(out, func_args)
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
    return tcext.TupleExpr(exprs)

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
    return tcext.ListExpr(exprs)

def parse_index_expr(parser):
    """ Parse a field chain indexing expression:

        a/b/0/2/c/d
    """
    out = tccore.Var(parser.ensure_token(TokenType.IDENTIFIER))
    while parser.next_token_if(TokenType.SLASH, consume = True):
        next = parser.ensure_token(TokenType.IDENTIFIER)
        out = tcext.Index(out, next)
    return out

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

    return tcext.IfExpr(conditions, default_expr)
