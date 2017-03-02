
from __future__ import absolute_import
import ipdb
from typelib import core as tlcore
from typelib import functions as tlfunctions
from onering import utils
from onering.dsl.parser.rules.types import ensure_typeref
from onering.core import functions, platforms
from onering.dsl.errors import SourceException, UnexpectedTokenException
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations

########################################################################
##          Function parsing rules
########################################################################

def parse_function(parser, annotations):
    """Parses a function declaration.

    function    :=  "fun" name<IDENT>   input_params ? ( ":" output_type )
    """
    parser.ensure_token(TokenType.IDENTIFIER, "fun")

    fqn = utils.FQN(parser.ensure_token(TokenType.IDENTIFIER), parser.namespace).fqn
    print "Parsing new function binding: '%s'" % fqn

    function_signature = parse_function_signature(parser)

    # Create a function of a given type and register it
    func_type = tlcore.FunctionType(function_signature.input_types,
                                    function_signature.output_type, annotations, docs)
    func_typeref = parser.register_type(fqn, func_type)

    # create the function object
    function = functions.Function(fqn, func_typeref, annotations, docs)
    return function

def parse_function_signature(parser, require_param_name = False):
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
    output_type = None
    if parser.next_token_is(TokenType.COLON):
        output_type = parser.ensure_entity(tlcore.Typeref)

    return input_params, output_type

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

    return tlfunctions.FunctionParamArg(param_name, param_typeref, is_optional, default_value, annotations, docstring)

