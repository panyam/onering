
from __future__ import absolute_import
import ipdb
from typelib import core as tlcore
from onering import utils
from onering.dsl.parser.rules.types import parse_any_type_decl
from onering.core import functions, platforms
from onering.dsl.errors import SourceException, UnexpectedTokenException
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations

########################################################################
##          Function parsing rules
########################################################################

def parse_bind(parser, annotations):
    """
    Parses a binding to a single function.
        "bind" func_name<IDENT> function_signature "{"
        "}"
    """
    docs = parser.last_docstring()

    parser.ensure_token(TokenType.IDENTIFIER, "bind")
    fqn = utils.FQN(parser.ensure_token(TokenType.IDENTIFIER), parser.document.namespace).fqn

    print "Parsing new function binding: '%s'" % fqn

    function_signature = parse_function_signature(parser)

    # Create a function of a given type and register it
    func_type = tlcore.FunctionType(function_signature.input_types,
                                    function_signature.output_type, annotations, docs)
    func_typeref = parser.register_type(fqn, func_type)

    # create the function object
    function = functions.Function(fqn, func_typeref,
                                  function_signature.inputs_need_inference,
                                  function_signature.output_needs_inference,
                                  annotations, docs)

    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        annotations = parse_annotations(parser)
        platform = parser.ensure_token(TokenType.STRING)
        parser.ensure_token(TokenType.EQUALS)
        native_fqn = parser.ensure_token(TokenType.STRING)
        platform = parser.onering_context.get_platform(platform, register = True)
        platform.add_function(function, native_fqn, annotations = annotations, docs = parser.last_docstring)
        parser.consume_tokens(TokenType.COMMA)
    parser.ensure_token(TokenType.CLOSE_BRACE)

    parser.onering_context.register_function(function)
    
    return function


def parse_function_signature(parser):
    """
    Parses the type signature declaration in a function declaration:

        function_signature:
            input_type_signature ?
            ( input_type_signature "->" output_type_signature ) ?

        input_type_signature:
            "?"
            |   input_types
            |   "(" input_types ")"

        output_type_signature:
            "?"
            |   output_type

    Returns:
        function_signature  -   A function signature object that contains all the input, output 
                                type specification and whether any types require inferencing 
                                based on the their call patterns in transformers.
    """
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
                if parser.peeked_token_is(TokenType.CLOSE_PAREN):
                    break
                parser.ensure_token(TokenType.COMMA)
            parser.ensure_token(TokenType.CLOSE_PAREN)
            inputs_need_inference = False
        elif parser.peeked_token_is(TokenType.IDENTIFIER):
            input_types.append(parse_any_type_decl(parser))
            inputs_need_inference = False

    # Read output types in the signature if any
    if parser.next_token_is(TokenType.ARROW):
        if parser.next_token_is(TokenType.QMARK):
            output_needs_inference = True
        else:
            output_needs_inference = False
            output_type = parse_any_type_decl(parser)

    return functions.Signature(input_types, output_type, inputs_need_inference, output_needs_inference)
