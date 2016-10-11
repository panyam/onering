
from __future__ import absolute_import
import ipdb
from typelib import core as tlcore
from onering import utils
from onering.dsl.parser.rules.types import parse_any_type_decl
from onering.core import functions
from onering.dsl.errors import SourceException, UnexpectedTokenException
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations

########################################################################
##          Platform bindings parsing rules
########################################################################

def parse_bind(parser, annotations):
    """
    Parses a platform binding to a single platform:

        platform_binding := "platform" platform_name<IDENT> "{"
            ( function_binding | type_binding ) *
        "}"
    """
    parser.ensure_token(TokenType.IDENTIFIER, "platform")
    platform_name = parser.ensure_token(TokenType.IDENTIFIER)
    platform = parser.onering_context.get_or_register_platform(platform_name, annotations,
                                                               parser.last_docstring()

    print "Parsing new platform bindings: '%s'" % platform_name

    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        annotations = parse_annotations(parser)

        binding_type = parser.ensure_token(TokenType.IDENTIFIER)

        if binding_type == "func":
            parse_platform_function_binding(parser, platform, annotations)
        elif binding_type == "type":
            parse_platform_type_binding(parser, platform, annotations)
        else:
            raise UnexpectedTokenException(parser.peek_token(), "type", "func")
        parser.consume_tokens(TokenType.COMMA)
    parser.ensure_token(TokenType.CLOSE_BRACE)


def parse_platform_type_bindings(parser, platform, annotations):
    """
    Parses a type binding in a platform.

        type_binding := "type" type_declaration "=>" native_type_template<STRING>
    """
    docs = parser.last_docstring()

def parse_platform_function_bindings(parser, platform, annotations):
    """
    Parses a function binding in a platform.

        function_binding := "func" func_name<IDENT> function_signature "=>" native_func<STRING>
    """
    docs = parser.last_docstring()

    func_name = parser.ensure_token(TokenType.STRING)
    # Type signature
    function_signature = parse_function_signature(parser)

    parser.ensure_token(TokenType.STREAM)

    native_fqn = parser.ensure_token(TokenType.STRING)

    # Create a function of a given type and register it
    func_type = tlcore.FunctionType(function_signature.input_types,
                                    function_signature.output_type, annotations, docs)
    func_typeref = parser.register_type(fqn, func_type)

    # create the function object
    function = parser.onering_context.get_function(fqn)
    if not function:
        function = functions.Function(fqn, func_typeref,
                                      function_signature.inputs_need_inference,
                                      function_signature.output_needs_inference,
                                      annotations, docs)
        parser.onering_context.register_function(function)

    platform.add_function(function, native_fqn)
    return function
