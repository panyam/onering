
from __future__ import absolute_import
import ipdb
from onering import utils
from onering.core import platforms
from onering.dsl.errors import SourceException, UnexpectedTokenException
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations

########################################################################
##          Platform bindings parsing rules
########################################################################

def parse_platform(parser, annotations, **kwargs):
    """
    Parses a platform binding to a single platform:

        platform_binding := "platform" platform_name<IDENT> "{"
            ( type_binding ) *
        "}"
    """
    parser.ensure_token(TokenType.IDENTIFIER, "platform")
    platform_name = parser.ensure_token(TokenType.IDENTIFIER)
    platform = parser.onering_context.get_platform(platform_name, register = True,
                                                   annotations = annotations, docs = parser.last_docstring())

    print "Parsing new platform bindings: '%s'" % platform_name

    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        annotations = parse_annotations(parser)

        binding_type = parser.ensure_token(TokenType.IDENTIFIER)

        if binding_type == "type":
            parse_platform_type_binding(parser, platform, annotations)
        else:
            raise UnexpectedTokenException(parser.peek_token(), "type")
        parser.consume_tokens(TokenType.COMMA)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    return platform


def parse_platform_type_binding(parser, platform, annotations):
    """
    Parses a type binding in a platform.  This is slightly different from a normal type declaration.
    A normal type declaration has no parametrized type arguments (this is what gets unified in GADT!!)

        type_binding := "type" type_declaration "=>" native_type_template<STRING>

        type_declaration := FQN
                |   FQN "[" type_arg ( "," type_arg ) * "]"

        type_arg := "$" name<IDENT> | type_declaration
    """


    def parse_type_binding_arg(parser, root = None):
        """
        Parses a type binding argument in a type binding.  See "type_arg" rule above.
        """
        if root and parser.peeked_token_is(TokenType.DOLLAR_LITERAL):
            # then we have a parametric argument
            return platforms.TypeBinding(parser.next_token().value, is_param = True)
        elif parser.peeked_token_is(TokenType.IDENTIFIER):
            # Have type declaration here.   See "type_declaration" rule above
            type_fqn = parser.ensure_fqn()
            type_binding = platforms.TypeBinding(type_fqn)
            if not root:
                root = type_binding

            if parser.next_token_is(parser.GENERIC_OPEN_TOKEN):
                while not parser.peeked_token_is(parser.GENERIC_CLOSE_TOKEN):
                    arg = parse_type_binding_arg(parser, root)
                    type_binding.add_argument(arg)
                    if parser.peeked_token_is(TokenType.COMMA):
                        parser.next_token()
                parser.ensure_token(parser.GENERIC_CLOSE_TOKEN)
            return type_binding
        else:
            raise UnexpectedTokenException(parser.peek_token(),
                                           TokenType.IDENTIFIER,
                                           TokenType.DOLLAR_LITERAL)

    docs = parser.last_docstring()
    type_binding = parse_type_binding_arg(parser)
    parser.ensure_token(TokenType.STREAM)
    native_template = parser.ensure_token(TokenType.STRING)
    platform.add_type_binding(type_binding, native_template)
