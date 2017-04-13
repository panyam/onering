
from __future__ import absolute_import 

import ipdb
from typelib.utils import FQN
from onering.dsl.lexer import Token, TokenType
from onering.core import projections

from onering.dsl.parser.rules.annotations import parse_annotations
from onering.dsl.parser.rules.misc import parse_field_path

########################################################################
##          Derivation and Projection Parsing
########################################################################

def parse_derivation(parser, annotations = [], **kwargs):
    """
    Parses a derivation

    derivation := "derive" FQN derivation_header derivation_body
    """
    parser.ensure_token(TokenType.IDENTIFIER, "derive")

    name = parser.ensure_token(TokenType.IDENTIFIER)
    print "Parsing new derivation: '%s'" % name

    derivation = projections.RecordDerivation(name, parser.current_module, annotations = annotations, docs = parser.last_docstring())
    parse_derivation_header(parser, derivation)
    parse_derivation_body(parser, derivation)
    parser.current_module.add_entity(derivation)
    return derivation


def parse_derivation_header(parser, derivation):
    """
    Parses a derivation header:

        derivation_header := ":" source_fqn ("as" IDENTIFIER) ? ( "," source_fqn ("as" IDENTIFIER) ) *
    """
    if not parser.next_token_is(TokenType.COLON):
        return 

    while True:
        source_alias, source_fqn = None, parser.ensure_fqn()
        source_fqn = parser.normalize_fqn(source_fqn)
        if parser.next_token_is(TokenType.IDENTIFIER, "as"):
            source_alias = parser.ensure_token(TokenType.IDENTIFIER)
        derivation.add_source(source_fqn, source_alias)
        if not parser.next_token_is(TokenType.COMMA):
            return 

def parse_derivation_body(parser, derivation):
    """
    Parses the body of a derivation

        derivation_body := "{" projection * "}"
    """
    parser.ensure_token(TokenType.OPEN_BRACE)

    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        # read a field projection
        projection = parse_projection(parser, derivation)
        derivation.add_projection(projection)
        parser.consume_tokens(TokenType.COMMA)

    parser.ensure_token(TokenType.CLOSE_BRACE)
    return derivation

def parse_projection(parser, parent_derivation,
                     allow_renaming = True, allow_optionality = True, allow_default_value = True):
    """
    Parse a field projection:

        projection_source projection_target
    """
    annotations = parse_annotations(parser)

    assert parent_derivation is None or isinstance(parent_derivation, projections.RecordDerivation), "Bad parent deriv type"

    # First parse the projection source:
    # Parse a field projection source:
    #       projection :=   field_path "/" *
    #                   |   field_path "/" "(" IDENTIFIER ( "," IDENTIFIER ) * ")"
    #                   |   field_path ( "as" IDENTIFIER ) ? 
    field_path = parse_field_path(parser)
    if field_path.has_children:
        return projections.MultiFieldProjection(parent_derivation, field_path)

    # We are onto single field projections now
    projected_name = None
    if field_path and allow_renaming:
        # Now check for renaming ie "as" <newname>
        if parser.next_token_is(TokenType.IDENTIFIER, "as"):
            projected_name = parser.ensure_token(TokenType.IDENTIFIER)

    projection = parse_projection_target(parser, parent_derivation, field_path)
    projection.projected_name = projected_name

    projection.is_optional = None
    if allow_optionality and parser.next_token_is(TokenType.QMARK):
        projection.is_optional = True

    projection.default_value = None
    if allow_default_value and parser.next_token_is(TokenType.EQUALS):
        projection.default_value = parser.ensure_literal_value()

    parser.consume_tokens(TokenType.SEMI_COLON)
    return projection

def parse_projection_target(parser, parent_derivation, field_path):
    """
    Parse a field projection target:
        projection :=   ( ":" ( any_type_decl | record_type_body ) )
                    |   "=>" ( IDENT ? ) derivation_body
                    |   "[" params "]" "=>" type_constructor "[" projections "]"
                        ) ?
                        "?" ?
                        ( "=" literal_value ) ?
    """
    # Check if we have a mutation or a type declaration            
    if parser.next_token_is(TokenType.COLON):
        if parser.peeked_token_is(TokenType.IDENTIFIER):
            from onering.dsl.parser.rules.types import ensure_typeref
            projected_type = ensure_typeref(parser)
            return projections.SimpleFieldProjection(parent_derivation, field_path, projected_typeref = projected_type)
        else:
            raise UnexpectedTokenException(parser.peek_token(), TokenType.IDENTIFIER)
    elif parser.next_token_is(TokenType.STREAM):
        # We have an inline derivation
        new_record_fqn = None
        if parser.peeked_token_is(TokenType.IDENTIFIER):
            n = parser.next_token().value
            ns = parser.namespace
            new_record_fqn = FQN(n, ns).fqn

        derivation = projections.RecordDerivation(new_record_fqn)
        parse_derivation_body(parser, derivation)
        return projections.InlineDerivation(parent_derivation, field_path, derivation = derivation)
    elif parser.peeked_token_is(parser.GENERIC_OPEN_TOKEN):
        return parse_type_stream_decl(parser, parent_derivation, field_path)

    return projections.SimpleFieldProjection(parent_derivation, field_path)

def parse_type_stream_decl(parser, parent_projection, field_path):
    """
    Parses a type stream declaration:


        type_stream_decl := "<" arglist ">" "=>" TYPE<IDENTIFIER> "[" derivations "]" 
    """
    # Parse the argument list of what is being streamed
    param_names = []
    if parser.next_token_is(parser.GENERIC_OPEN_TOKEN):
        param_names = parser.read_ident_list(TokenType.COMMA)
        parser.ensure_token(parser.GENERIC_CLOSE_TOKEN)

    parser.ensure_token(TokenType.STREAM)

    children = []

    # There MUST be a type constructor
    type_constructor = parser.ensure_fqn()

    parser.ensure_token(parser.GENERIC_OPEN_TOKEN)

    annotations = parse_annotations(parser)
    while not parser.peeked_token_is(parser.GENERIC_CLOSE_TOKEN):
        if parser.peeked_token_is(TokenType.OPEN_BRACE):
            # Then we have a complete derivation body
            derivation = projections.RecordDerivation(None, annotations = annotations, docs = parser.last_docstring())
            parse_derivation_body(parser, derivation)
            children.append(derivation)
        else:
            # TODO - Need annotations?
            projection = parse_projection(parser, None, allow_renaming = False, allow_optionality = False, allow_default_value = False)
            children.append(projection)
        # Consume a comma silently 
        parser.next_token_if(TokenType.COMMA, consume = True)
        annotations = parse_annotations(parser)
    parser.ensure_token(parser.GENERIC_CLOSE_TOKEN)
    return projections.TypeStream(parent_projection, field_path, param_names, type_constructor, children)
