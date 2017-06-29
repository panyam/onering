
from __future__ import absolute_import
import ipdb
from typelib import core as tlcore
from typelib import ext as tlext
from typelib.utils import FieldPath
from onering import utils
from onering.dsl import errors
from onering.dsl.parser.rules.types import ensure_typeexpr
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations
from onering.dsl.parser.rules.misc import parse_field_path

########################################################################
##          Fun type and definition parsing rules
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
    input_typeargs, output_typearg = parse_function_signature(parser)

    parent = parser.current_module if func_name else None
    functype = tlcore.make_func_type(func_name, input_typeargs, output_typearg, parent)
    function = tlcore.Fun(func_name, functype, None, parser.current_module, annotations = annotations, docs = docs)
    if not is_external:
        parse_function_body(parser, function)

    if type_params:
        function = tlcore.TypeFun(func_name, type_params, function, parent, annotations = annotations, docs = docs)

    parser.add_entity(func_name, function)
    parser.onering_context.fgraph.register(function)
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
    output_typearg = None
    if parser.next_token_is(TokenType.ARROW):
        output_typeexpr = None
        output_varname = "dest"
        output_typeexpr = ensure_typeexpr(parser)
        if parser.next_token_is(TokenType.IDENTIFIER, "as"):
            output_varname = parser.ensure_token(TokenType.IDENTIFIER)
        output_typearg = tlcore.TypeArg(output_varname, output_typeexpr)
    return input_params, output_typearg 

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
    if type(param_typeexpr) is tlcore.Fun and param_typeexpr.name:
        param_typeexpr = tlcore.Variable(param_typeexpr.name)
    is_optional     = parser.next_token_is(TokenType.QMARK)
    default_value   = None
    if parser.next_token_is(TokenType.EQUALS):
        default_value = parser.ensure_literal_value()

    return tlcore.TypeArg(param_name, param_typeexpr, is_optional, default_value, annotations, docstring)

def parse_function_body(parser, function):
    if parser.peeked_token_is(TokenType.OPEN_BRACE):
        function.expr = parse_expr_list(parser, function)

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
    exprs = parse_expr_chain(parser)

    # An expr must have more than 1 expr
    if len(exprs) <= 1:
        ipdb.set_trace()
        raise errors.OneringException("A rule statement must have at least one expr")

    parser.consume_tokens(TokenType.SEMI_COLON)

    # ensure last var IS a variable expr
    if not isinstance(exprs[-1], tlcore.Variable):
        raise errors.OneringException("Final target of an expr MUST be a variable")
    target_var = exprs[-1]
    exprlist = tlext.ExprList(exprs[:-1])
    if target_var.field_path.get(0) == '_':
        return exprlist
    else:
        if is_temporary:
            function.register_temp_var(target_var.field_path.get(0))
        return tlext.Assignment(function, target_var, exprlist)

def parse_expr_chain(parser):
    """
    Parse an expr chain of the form 

        expr => expr => expr => expr
    """
    out = [ parse_expr(parser) ]

    # if the next is a "=>" then start streaming!
    while parser.peeked_token_is(TokenType.STREAM):
        parser.ensure_token(TokenType.STREAM)
        out.append(parse_expr(parser))
    return out

def parse_expr(parser):
    """
    Parse a function call expr or a literal.

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
            parser.onering_context.IntType
        elif type(value) is long:
            parser.onering_context.LongType
        elif type(value) is float:
            parser.onering_context.DoubleType
        else:
            assert False
        out = tlext.Literal(value, vtype)
    elif parser.peeked_token_is(TokenType.STRING):
        out = tlext.Literal(parser.next_token().value, tlext.StringType)
    elif parser.peeked_token_is(TokenType.OPEN_SQUARE):
        # Read a list
        out = parse_list_expr(parser)
    elif parser.peeked_token_is(TokenType.OPEN_BRACE):
        out = parse_struct_expr(parser)
    elif parser.peeked_token_is(TokenType.OPEN_PAREN):
        out = parse_tuple_expr(parser)
    elif parser.peeked_token_is(TokenType.IDENTIFIER, "if"):
        out = parse_if_expr(parser)
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
            out = tlcore.FunApp(tlcore.Variable(source), func_args)
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

