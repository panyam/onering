
from __future__ import absolute_import
import ipdb
from onering import utils
from onering.dsl.errors import SourceException, UnexpectedTokenException
from onering.errors import OneringException
from onering.dsl.lexer import Token, TokenType
from onering.core import transformers
from onering.core import exprs as orexprs
from onering.dsl.parser.rules.annotations import parse_annotations
from onering.dsl.parser.rules.misc import parse_field_path

########################################################################
##          Transformer Parsing Rules
########################################################################

def parse_transformer_group(parser, annotations, **kwargs):
    """
    Parses transformer declarations

        transformers name<IDENT>    "{" transformer_decl * "}"
    """
    parser.ensure_token(TokenType.IDENTIFIER, "transformers")
    fqn = utils.FQN(parser.ensure_token(TokenType.IDENTIFIER), parser.namespace).fqn
    print "Parsing new transformer group: '%s'" % fqn

    transformer_group = transformers.TransformerGroup(fqn, annotations = annotations, docs = parser.last_docstring())
    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        # read a transformer
        annotations = parse_annotations(parser)
        # consume the "transformer"
        parser.next_token_if(TokenType.IDENTIFIER, "transformer", consume = True)

        transformer = parse_transformer(parser, annotations, transformer_group)
        transformer_group.add_transformer(transformer)

    parser.register_transformer_group(transformer_group)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    return transformer_group

def parse_transformer(parser, annotations, transformer_group = None):
    """
    Parses a single transformer declaration

        transformer_decl := transformer_name ( src_type_fqn | src_type_fqn_list )
                            ( "(" src_varname ")" ) ?
                            "=> dest_type_fqn<IDENT>
                            ( "(" dest_varname ")" ) ?
                            "{" transformer_rule * "}"

        src_type_fqn_list := src_type_fqn | src_type_fqn ( "," src_type_fqn ) *

        src_type_fqn := FQN ( "as" var_name<IDENT> ) ?
    """
    transformer_name = parser.ensure_token(TokenType.IDENTIFIER)

    # Parse the source variables
    source_variables = []

    def parse_src_fqn(parser):
        src_fqn = parser.ensure_fqn()
        src_fqn = parser.normalize_fqn(src_fqn)
        src_varname = None
        if parser.next_token_is(TokenType.IDENTIFIER, "as"):
            src_varname = parser.ensure_token(TokenType.IDENTIFIER)
        return src_fqn, src_varname

    source_variables.append(parse_src_fqn(parser))
    while parser.next_token_is(TokenType.COMMA):
        source_variables.append(parse_src_fqn(parser))

    parser.ensure_token(TokenType.STREAM)
    dest_fqn = parser.ensure_fqn()
    dest_varname = None
    if parser.next_token_is(TokenType.IDENTIFIER, "as"):
        dest_varname = parser.ensure_token(TokenType.IDENTIFIER)

    dest_fqn = parser.normalize_fqn(dest_fqn)

    print "Parsing new transformer '%s': %s -> %s" % (transformer_name, ", ".join(map(lambda x: x[0], source_variables)), dest_fqn)

    transformer = transformers.Transformer(fqn = transformer_name,
                                           source_variables = source_variables,
                                           dest_fqn = dest_fqn,
                                           dest_varname = dest_varname,
                                           group = transformer_group,
                                           annotations = annotations,
                                           docs = parser.last_docstring())

    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        # read a transformer
        statement = parse_transformer_rule(parser, transformer)
        transformer.add_statement(statement)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    parser.consume_tokens(TokenType.SEMI_COLON)
    return transformer

def parse_transformer_rule(parser, transformer):
    """
    Parses a single transformer rule.

        transformer_rule := let_statment | stream_expr

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
    return orexprs.Statement(transformer, exprs[:-1], exprs[-1], is_temporary)

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
        out = orexprs.LiteralExpression(parser.next_token())
    elif parser.peeked_token_is(TokenType.STRING):
        out = orexprs.LiteralExpression(parser.next_token())
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
            source = source.get(0)
            source_fqn = parser.normalize_fqn(source)
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
            out = orexprs.FunctionCallExpression(source_fqn, func_args)
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

