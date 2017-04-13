
from __future__ import absolute_import 

import ipdb
from typelib import records
from typelib.utils import FQN
from typelib import core as tlcore
from typelib import enums as tlenums
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations
from onering.dsl.errors import UnexpectedTokenException

########################################################################
##          Type declaration parsing rules
########################################################################

def parse_entity(parser):
    """
    Parses top level type declarations:

        type_declaration := annotation * ( typeref_decl | custom_type_decl)
    """
    annotations = parse_annotations(parser)
    entity_class = parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    entity_parser = parser.get_entity_parser(entity_class)
    if entity_parser:
        return entity_parser(parser, annotations = annotations)
    else:
        return parse_parametric_type(parser, annotations = annotations)

def parse_typeref_decl(parser, annotations, **kwargs):
    """
    Parses typeref declaration of the form:

        "typeref" <name> "=" entity
    """
    docstring = parser.last_docstring()
    parser.ensure_token(TokenType.IDENTIFIER, "typeref")
    name = parser.ensure_token(TokenType.IDENTIFIER)
    parser.ensure_token(TokenType.EQUALS)

    # create the typeref
    newtyperef = tlcore.EntityRef(None, name, parser.current_module)
    newtyperef.target = ensure_typeref(parser)
    return newtyperef

def ensure_typeref(parser, annotations = None):
    out = parse_entity(parser)
    if out:
        assert type(out) is tlcore.EntityRef
    else:
        out = parse_named_typeref(parser, annotations)
    return out

def parse_parametric_type(parser, annotations):
    """
    Parses a parametric type:

        type_constructor type_name ? "<" args ">"
    """
    if not parser.peeked_token_is(TokenType.IDENTIFIER): return None
    next_token = parser.next_token()

    # TODO - Check that next_token is actually not referring to a "primitive" type
    if parser.peeked_token_is(parser.GENERIC_OPEN_TOKEN):
        return parse_parametric_type_body(parser, constructor = next_token.value, annotations = annotations)
    elif parser.peeked_token_is(TokenType.IDENTIFIER):
        name_token = parser.next_token()
        if parser.peeked_token_is(parser.GENERIC_OPEN_TOKEN):
            # push token back so it can be used by the rule
            parser.unget_token(name_token)
            return parse_parametric_type_body(parser, constructor = next_token.value, annotations = annotations)
        else:
            # push token back anyway as rule doesnt match
            parser.unget_token(name_token)
    # Put token back in stream
    parser.unget_token(next_token)
    return None

def parse_parametric_type_body(parser, constructor, annotations = None):
    newtyperef, docs = parse_newtyperef_preamble(parser, constructor)

    parser.ensure_token(parser.GENERIC_OPEN_TOKEN)
    child_typerefs = [ ensure_typeref(parser) ]

    while not parser.peeked_token_is(parser.GENERIC_CLOSE_TOKEN):
        parser.ensure_token(TokenType.COMMA)
        child_typerefs.append(ensure_typeref(parser))
    parser.ensure_token(parser.GENERIC_CLOSE_TOKEN)

    parent = None
    if newtyperef.name:
        parent = parser.current_module
    newtyperef.target = tlcore.Type(newtyperef.name, parent, constructor,
                                    type_params = None, type_args = child_typerefs, annotations = annotations, docs = docs)
    return newtyperef

def parse_named_typeref(parser, annotations = None):
    parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    fqn = parser.ensure_fqn()
    # if this type exists in the type registry use this type
    # otherwise register as an unresolved type and proceed
    return parser.get_typeref(fqn)

def parse_newtyperef_preamble(parser, constructor, name_required = False):
    name = None
    if name_required:
        name = parser.ensure_token(TokenType.IDENTIFIER)

    if name:
        print "Registering new %s: '%s'" % (constructor, name)
        newtyperef = parser.current_module.ensure_key(name)
    else:
        newtyperef = tlcore.EntityRef(None, None, None)

    assert newtyperef is not None, "A type was NOT parsed"
    docs = parser.last_docstring()
    return newtyperef, docs

########################################################################
##          Enum and Union parsing
########################################################################

def parse_enum(parser, annotations = None):
    """
    Parses an enum declaration of the form:

        enum ( "[" type "]" ) ? enum_body
    """
    parser.ensure_token(TokenType.IDENTIFIER, "enum")
    newtyperef, fqn, docs = parse_newtyperef_preamble(parser, "enum", True)
    type_args = None
    if parser.next_token_is(parser.GENERIC_OPEN_TOKEN):
        type_args = [ensure_typeref(parser)]
        parser.ensure_token(parser.GENERIC_CLOSE_TOKEN)

    symbols = parse_enum_body(parser)
    newtyperef.target = tlenums.EnumType(symbols, type_args, annotations = annotations, docs = docs)
    return newtyperef

def parse_enum_body(parser):
    """
    Parse the body of an enum declaration:

        enum_body := "{" enum_symbol * + "}"

        enum_symbol := identifier ( "=" literal )
    """
    symbols = []
    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        annotations = parse_annotations(parser)
        name = parser.ensure_token(TokenType.IDENTIFIER)
        value = None
        if parser.next_token_is(TokenType.EQUALS):
            value = parser.ensure_literal_value()
        symbols.append(tlenums.EnumSymbol(name, value, annotations, parser.last_docstring))
        # consume comma silently
        parser.next_token_if(TokenType.COMMA, consume = True)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    return symbols

def parse_union_body(parser):
    """
    Parse the body of an union declaration:
        "{" any_type_decl + "}"
    """
    union_types = []
    parser.ensure_token(TokenType.OPEN_SQUARE)
    while not parser.peeked_token_is(TokenType.CLOSE_SQUARE):
        union_types.append(ensure_typeref(parser))
        parser.consume_tokens(TokenType.COMMA)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    return union_types

########################################################################
##          Record and Field parsing
########################################################################

def parse_record(parser, annotations = None):
    parser.ensure_token(TokenType.IDENTIFIER, "record")
    newtyperef, docs = parse_newtyperef_preamble(parser, "record", True)
    fields = parse_record_body(parser)
    newtyperef.target = records.RecordType(newtyperef.name, None, fields, annotations = annotations, docs = docs)
    return newtyperef

def parse_record_body(parser):
    """
    Parses the body of a record declaration:

        record_type_body := "{" ( annotation * field_declaration ) * "}"

    """
    fields = []
    parser.ensure_token(TokenType.OPEN_BRACE)

    # read annotations as they can be used by ... or field projections
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        # read a field projection
        fields.append(parse_field_declaration(parser))

    parser.ensure_token(TokenType.CLOSE_BRACE)
    return fields

def parse_field_declaration(parser):
    """
        field_declaration := annotations ? IDENTIFIER ":" type_decl "?" ? ( "=" literal_value ) ?
    """
    annotations = parse_annotations(parser)
    docstring = parser.last_docstring()
    field_name = parser.ensure_token(TokenType.IDENTIFIER)
    parser.ensure_token(TokenType.COLON)
    field_typeref = ensure_typeref(parser)
    is_optional = False
    default_value = None

    if parser.next_token_is(TokenType.QMARK):
        is_optional = True

    if parser.next_token_is(TokenType.EQUALS):
        default_value = parser.ensure_literal_value()

    field = records.FieldTypeArg(field_name, field_typeref, is_optional, default_value, annotations, docstring)
    return field
