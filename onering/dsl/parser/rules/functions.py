
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
##          Function parsing rules
########################################################################

def parse_bind(parser, annotations):
    """
    Parses a binding to a single function.
        "bind" func_name<IDENT> type_signature "{"
        "}"

        type_signature:
            input_type_signature ?
            ( input_type_signature "=>" output_type_signature ) ?

        input_type_signature:
            "?"
            |   input_types
            |   "(" input_types ")"

        output_type_signature:
            "?"
            |   output_type
    """
    docs = parser.last_docstring()

    parser.ensure_token(TokenType.IDENTIFIER, "bind")
    n = parser.ensure_token(TokenType.IDENTIFIER)
    ns = parser.document.namespace
    n,ns,fqn = utils.normalize_name_and_ns(n, ns)

    print "Parsing new function binding: '%s'" % fqn

    input_types = []
    output_type = None
    inputs_need_inference = True
    output_needs_inference = True

    # Read input types in the signature if any
    if parser.next_token_is(TokenType.QMARK):
        inputs_need_inference = True
    else:
        if parser.peeked_token_is(TokenType.OPEN_PAREN):
            parser.ensure_token(TokenType.OPEN_PAREN)
            while not parser.peeked_token_is(TokenType.CLOSE_PAREN):
                input_types.append(parse_any_type_decl(parser))
                if parser.peeked_token_is(TokenType.COMMA):
                    parser.consume_token()
                    break
            parser.ensure_token(TokenType.CLOSE_PAREN)
            inputs_need_inference = False
        elif not parser.peeked_token_is(TokenType.OPEN_BRACE):
            input_types.append(parse_any_type_decl(parser))
            inputs_need_inference = False

    # Read output types in the signature if any
    if parser.next_token_is(TokenType.STREAM):
        if parser.next_token_is(TokenType.QMARK):
            output_needs_inference = True
        else:
            output_needs_inference = False
            output_type = parse_any_type_decl(parser)

    # Create a function of a given type and register it
    func_type = tlcore.FunctionType(input_types, output_type, annotations, docs)
    func_typeref = parser.register_type(fqn, func_type)

    # create the function object
    function = functions.Function(fqn, func_typeref,
                                  inputs_need_inference,
                                  output_needs_inference,
                                  annotations, docs)

    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        annotations = parse_annotations(parser)
        platform = parser.ensure_token(TokenType.STRING)
        parser.ensure_token(TokenType.EQUALS)
        native_fqn = parser.ensure_token(TokenType.STRING)
        platform_binding = functions.PlatformBinding(platform, native_fqn, annotations, parser.last_docstring())
        function.add_platform(platform_binding)
        parser.consume_tokens(TokenType.COMMA)
    parser.ensure_token(TokenType.CLOSE_BRACE)

    parser.onering_context.register_function(function)
    
    return function