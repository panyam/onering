
from __future__ import absolute_import 

import ipdb
from typelib import records
from typelib import core as tlcore
from typelib import enums as tlenums
from onering import utils
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations
from onering.dsl.errors import UnexpectedTokenException

########################################################################
##          Type declaration parsing rules
########################################################################

def parse_entity(parser, typereffed_fqn = None):
    """
    Parses top level type declarations:

        type_declaration := annotation * ( typeref_decl | custom_type_decl)
    """
    annotations = parse_annotations(parser)
    entity_class = parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    entity_parser = parser.get_entity_parser(entity_class)
    if entity_parser:
        return entity_parser(parser, annotations = annotations, typereffed_fqn = typereffed_fqn)
    else:
        return parse_parametric_type(parser, annotations = annotations, typereffed_fqn = typereffed_fqn)

def parse_typeref_decl(parser, annotations, **kwargs):
    """
    Parses typeref declaration of the form:

        "typeref" <name> "=" entity
    """
    docstring = parser.last_docstring()
    parser.ensure_token(TokenType.IDENTIFIER, "typeref")
    name = parser.ensure_token(TokenType.IDENTIFIER)
    fqn = utils.FQN(name, parser.namespace).fqn

    parser.ensure_token(TokenType.EQUALS)
    target_typeref = parse_entity(parser, typereffed_fqn = fqn)
    if not isinstance(target_typeref, tlcore.TypeRef):
        ipdb.set_trace()

    parser.register_type(fqn, target_typeref)
    return fqn

def ensure_typeref(parser, annotations = [], typereffed_fqn = None):
    out = parse_entity(parser, typereffed_fqn)
    if out:
        assert type(out) is tlcore.TypeRef
    else:
        out = parse_named_typeref(parser, annotations)
    return out

def parse_parametric_type(parser, annotations, typereffed_fqn = None):
    """
    Parses a parametric type:

        type_constructor type_name ? "[" args "]"
    """
    if not parser.peeked_token_is(TokenType.IDENTIFIER): return None
    next_token = parser.next_token()

    # TODO - Check that next_token is actually not referring to a "primitive" type
    if parser.peeked_token_is(TokenType.OPEN_SQUARE):
        return parse_parametric_type_body(parser, constructor = next_token.value, annotations = annotations, typereffed_fqn = typereffed_fqn)
    elif parser.peeked_token_is(TokenType.IDENTIFIER):
        name_token = parser.next_token()
        if parser.peeked_token_is(TokenType.OPEN_SQUARE):
            # push token back so it can be used by the rule
            parser.unget_token(name_token)
            return parse_parametric_type_body(parser, constructor = next_token.value, annotations = annotations, typereffed_fqn = typereffed_fqn)
        else:
            # push token back anyway as rule doesnt match
            parser.unget_token(name_token)
    # Put token back in stream
    parser.unget_token(next_token)
    return None

def parse_parametric_type_body(parser, constructor, annotations = [], typereffed_fqn = None):
    newtyperef, fqn, docs = parse_newtyperef_preamble(parser, constructor, typereffed_fqn)

    parser.ensure_token(TokenType.OPEN_SQUARE)
    child_typerefs = [ ensure_typeref(parser) ]

    while not parser.peeked_token_is(TokenType.CLOSE_SQUARE):
        parser.ensure_token(TokenType.COMMA)
        child_typerefs.append(ensure_typeref(parser))
    parser.ensure_token(TokenType.CLOSE_SQUARE)

    newtyperef.target = tlcore.Type(None, constructor, type_params = None, type_args = child_typerefs, annotations = annotations, docs = docs)
    return newtyperef

def parse_named_typeref(parser, annotations = [], typereffed_fqn = None):
    parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    fqn = parser.ensure_fqn()
    # if this type exists in the type registry use this type
    # otherwise register as an unresolved type and proceed
    return parser.get_typeref(fqn)

def parse_newtyperef_preamble(parser, constructor, typereffed_fqn, force_fqn_if_missing = False):
    fqn = typereffed_fqn
    if parser.peeked_token_is(TokenType.IDENTIFIER) or (fqn is None and force_fqn_if_missing):
        # we have a name
        n = parser.ensure_token(TokenType.IDENTIFIER)
        ns = parser.namespace
        fqn = utils.FQN(n, ns).fqn

    if fqn:
        print "Registering new %s: '%s'" % (constructor, fqn)
        newtyperef = parser.register_type(fqn, None)
    else:
        newtyperef = tlcore.TypeRef(None, None)

    assert newtyperef is not None, "A type was NOT parsed"
    docs = parser.last_docstring()
    return newtyperef, fqn, docs

########################################################################
##          Enum and Union parsing
########################################################################

def parse_enum(parser, annotations = [], typereffed_fqn = None):
    parser.ensure_token(TokenType.IDENTIFIER, "enum")
    newtyperef, fqn, docs = parse_newtyperef_preamble(parser, "enum", typereffed_fqn, True)
    symbols = parse_enum_body(parser)
    newtyperef.target = tlenums.EnumType(symbols, annotations = annotations, docs = docs)

def parse_enum_body(parser):
    """
    Parse the body of an enum declaration:

        "{" enum_symbols + "}"
    """
    symbols = []
    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        annotations = parse_annotations(parser)
        name = parser.ensure_token(TokenType.IDENTIFIER)
        symbols.append(tlenums.EnumSymbol(name, annotations, parser.last_docstring))
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

def parse_record(parser, annotations = [], typereffed_fqn = None):
    parser.ensure_token(TokenType.IDENTIFIER, "record")
    newtyperef, fqn, docs = parse_newtyperef_preamble(parser, "record", typereffed_fqn, True)
    fields = parse_record_body(parser)
    rec_name = utils.FQN(fqn, parser.namespace).name
    newtyperef.target = records.RecordType(fields, annotations = annotations, docs = docs, name = rec_name)
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
