
from __future__ import absolute_import
import ipdb
from typelib import core as tlcore
from onering import utils
from onering.dsl.parser.rules.types import parse_any_type_decl
from onering.core import functions, platforms
from onering.dsl.errors import SourceException, UnexpectedTokenException
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations
from onering.dsl.parser.rules.functions import parse_function_signature

########################################################################
##          Platform bindings parsing rules
########################################################################

def parse_platform(parser, annotations):
    """
    Parses a platform binding to a single platform:

        platform_binding := "platform" platform_name<IDENT> "{"
            ( function_binding | type_binding ) *
        "}"
    """
    parser.ensure_token(TokenType.IDENTIFIER, "platform")
    platform_name = parser.ensure_token(TokenType.IDENTIFIER)
    platform = parser.onering_context.get_or_register_platform(platform_name, annotations,
                                                               parser.last_docstring())

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

def parse_platform_function_binding(parser, platform, annotations):
    """
    Parses a function binding in a platform.

        function_binding := "func" func_fqn<FQN> function_signature "=>" native_func<STRING>
    """
    docs = parser.last_docstring()

    func_fqn = parser.ensure_fqn()
    # Type signature
    function_signature = parse_function_signature(parser)

    parser.ensure_token(TokenType.STREAM)
    native_fqn = parser.ensure_token(TokenType.STRING)

    # Create a function of a given type and register it
    func_type = tlcore.FunctionType(function_signature.input_types,
                                    function_signature.output_type, annotations, docs)
    # TODO - If a function is registered twice - say for different platforms
    # We should ignore one if types are the same and throw errors if different platforms
    # have different type signatures
    func_typeref = parser.register_type(func_fqn, func_type)

    # create the function object
    function = parser.onering_context.get_function(func_fqn, ignore_missing = True)
    if not function:
        function = functions.Function(func_fqn, func_typeref,
                                      function_signature.inputs_need_inference,
                                      function_signature.output_needs_inference,
                                      annotations, docs)
        parser.onering_context.register_function(function)
    else:
        ipdb.set_trace()
        pass

    platform.add_function(function, native_fqn)
    return function


def parse_platform_type_binding(parser, platform, annotations):
    """
    Parses a type binding in a platform.  This is slightly different from a normal type declaration.
    A normal type declaration has no parametrized type arguments (this is what gets unified in GADT!!)

        type_binding := "type" type_declaration "=>" native_type_template<STRING>

        type_declaration := FQN
                |   FQN "[" type_arg ( "," type_arg ) * "]"

        type_arg := "$" name<IDENT> | type_declaration
    """
    docs = parser.last_docstring()

    # Get the fqn
    type_fqn = parser.ensure_fqn()

    type_binding = platforms.TypeBinding(type_fqn)

    if parser.next_token_is(TokenType.OPEN_SQUARE):
        while not parser.peeked_token_is(TokenType.CLOSE_SQUARE) or \
              parser.peeked_token_is(TokenType.COMMA):
            parser.next_token_if(TokenType.COMMA)
            arg = parse_type_binding_arg(parser)
            type_binding.add_argument(arg)
        parser.ensure_token(TokenType.CLOSE_SQUARE)
        parser.ensure_token(TokenType.STREAM)

    native_template = parser.ensure_token(TokenType.STRING)
    platform.add_type(type_binding, native_template)
