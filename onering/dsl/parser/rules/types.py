
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

def parse_type_decl(parser):
    """
    Parses top level type declarations:

        type_declaration := annotation * ( typeref_decl | complex_type_decl)
    """
    annotations = parse_annotations(parser)
    type_class = parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    if type_class == "typeref":
        return parse_typeref_decl(parser, annotations)
    elif type_class == "derive":
        from onering.dsl.parser.rules.derivations import parse_derivation
        return parse_derivation(parser, annotations)
    elif type_class == "bind":
        from onering.dsl.parser.rules.functions import parse_bind
        return parse_bind(parser, annotations)
    elif type_class == "___transformer___": # Disable for now
        parser.next_token()     # consume it
        from onering.dsl.parser.rules.transformers import parse_transformer
        parse_transformer(parser, annotations)
    elif type_class == "transformers":
        from onering.dsl.parser.rules.transformers import parse_transformer_group
        parse_transformer_group(parser, annotations)
    else:
        return parse_complex_type_decl(parser, annotations)

def parse_typeref_decl(parser, annotations):
    """
    Parses typeref declaration of the form:

        "typeref" <name> "=" type_data
    """
    docstring = parser.last_docstring()
    parser.ensure_token(TokenType.IDENTIFIER, "typeref")
    name = parser.ensure_token(TokenType.IDENTIFIER)
    name, namespace, fqn = utils.normalize_name_and_ns(name, parser.document.namespace)

    parser.ensure_token(TokenType.EQUALS)
    target_typeref = parse_any_type_decl(parser, typereffed_fqn = fqn)
    if not isinstance(target_typeref, tlcore.TypeRef):
        ipdb.set_trace()

    parser.register_type(fqn, target_typeref)
    return fqn

def parse_any_type_decl(parser, annotations = [], typereffed_fqn = None):
    # TODO - Use generic generic types instead of hard coded map and array 
    # ie based on the presence of a "[" token after an identifier
    next_token = parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    if next_token == "array":
        return parse_array_type_decl(parser, annotations)
    elif next_token == "map":
        return parse_map_type_decl(parser, annotations)
    elif next_token in [ "record", "enum", "union" ]:
        return parse_complex_type_decl(parser, annotations, typereffed_fqn)
    else:
        return parse_named_typeref(parser, annotations)

def parse_named_typeref(parser, annotations = []):
    parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    fqn = parser.ensure_fqn()
    # if this type exists in the type registry use this type
    # otherwise register as an unresolved type and proceed
    return parser.get_typeref(fqn)

def parse_array_type_decl(parser, annotations = []):
    parser.ensure_token(TokenType.IDENTIFIER, "array")
    parser.ensure_token(TokenType.OPEN_SQUARE)
    target_type = parse_any_type_decl(parser)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    return tlcore.TypeRef(tlcore.ArrayType(target_type, annotations = annotations, docs = parser.last_docstring()), None)

def parse_map_type_decl(parser, annotations = []):
    parser.ensure_token(TokenType.IDENTIFIER, "map")
    parser.ensure_token(TokenType.OPEN_SQUARE)
    key_type = parse_any_type_decl(parser)
    parser.ensure_token(TokenType.COMMA)
    value_type = parse_any_type_decl(parser)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    return tlcore.TypeRef(tlcore.MapType(key_type, value_type, annotations = annotations, docs = parser.last_docstring()), None)

def parse_complex_type_decl(parser, annotations = [], typereffed_fqn = None):
    type_class = parser.ensure_token(TokenType.IDENTIFIER)
    if type_class not in ["union", "enum", "record"]:
        raise UnexpectedTokenException(parser.peek_token(), "union", "enum", "record")

    newtype = None
    fqn = typereffed_fqn
    if parser.peeked_token_is(TokenType.IDENTIFIER) or fqn is None:
        # we have a name
        n = parser.ensure_token(TokenType.IDENTIFIER)
        ns = parser.document.namespace
        n,ns,fqn = utils.normalize_name_and_ns(n, ns)

    if fqn:
        print "Registering new %s: '%s'" % (type_class, fqn)
        newtyperef = parser.register_type(fqn, None)
    else:
        newtyperef = tlcore.TypeRef(None, None)

    docs = parser.last_docstring()
    if type_class == "enum":
        symbols = parse_enum_body(parser)
        newtyperef.target = tlenums.EnumType(symbols, annotations = annotations, docs = docs)
    elif type_class == "union":
        union_types = parse_union_body(parser)
        newtyperef.target = tlcore.UnionType(union_types, annotations = annotations, docs = docs)
    elif type_class == "record":
        fields = parse_record_body(parser)
        newtyperef.target = records.RecordType(fields, annotations = annotations, docs = docs)
    else:
        assert False

    assert newtyperef is not None, "A type was NOT parsed"
    return newtyperef

########################################################################
##          Enum and Union parsing
########################################################################

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
        union_types.append(parse_any_type_decl(parser))
        parser.consume_tokens(TokenType.COMMA)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    return union_types

########################################################################
##          Record and Field parsing
########################################################################

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
    field_typeref = parse_any_type_decl(parser)
    is_optional = False
    default_value = None

    if parser.next_token_is(TokenType.QUESTION):
        is_optional = True

    if parser.next_token_is(TokenType.EQUALS):
        default_value = parser.ensure_literal_value()

    field = records.FieldTypeArg(field_name, field_typeref, is_optional, default_value, annotations, docstring)
    return field
