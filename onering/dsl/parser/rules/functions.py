
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
    func_fqn = ".".join([parser.current_module.fqn, func_name])
    input_typeargs, output_typearg = parse_function_signature(parser)

    parent = parser.current_module if func_name else None
    functype = tlcore.make_fun_type(None, input_typeargs, output_typearg, parent)
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
    # if we declared an inline Type then dont refer to it directly but via a Var
    if type(param_typeexpr) is tlcore.Fun and param_typeexpr.name:
        param_typeexpr = tlcore.Var(param_typeexpr.name)
    is_optional     = parser.next_token_is(TokenType.QMARK)
    default_value   = None
    if parser.next_token_is(TokenType.EQUALS):
        default_value = parser.ensure_literal_value()

    return tlcore.TypeArg(param_name, param_typeexpr, is_optional, default_value, annotations, docstring)

def parse_function_body(parser, function):
    if parser.peeked_token_is(TokenType.OPEN_BRACE):
        from onering.dsl.parser.rules.exprs import parse_expr_list
        function.expr = parse_expr_list(parser, function)


