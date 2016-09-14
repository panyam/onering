
from typelib import records
from typelib import core as tlcore
from typelib import enums as tlenums
from onering import utils
from onering.dsl.lexer import Token, TokenType
from annotations import parse_annotations

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
        from derivations import parse_derivation
        return parse_derivation(parser, annotations)
    elif type_class == "transformer":
        parser.next_token()     # consume it
        from transformers import parse_transformer
        parse_transformer(parser, annotations)
    elif type_class == "transformers":
        from transformers import parse_transformer_group
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
    target_type = parse_any_type_decl(parser, typereffed_fqn = fqn)

    parser.register_type(fqn, target_type)
    return fqn

def parse_any_type_decl(parser, annotations = [], typereffed_fqn = None):
    next_token = parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    if next_token == "array":
        return parse_array_type_decl(parser, annotations)
    elif next_token == "map":
        return parse_map_type_decl(parser, annotations)
    elif next_token in [ "record", "enum", "union" ]:
        return parse_complex_type_decl(parser, annotations, typereffed_fqn)
    else:
        return parse_primitive_type(parser, annotations)

def parse_primitive_type(parser, annotations = []):
    parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    fqn = parser.ensure_fqn()
    # if this type exists in the type registry use this type
    # otherwise register as an unresolved type and proceed
    return parser.get_type(fqn)

def parse_array_type_decl(parser, annotations = []):
    parser.ensure_token(TokenType.IDENTIFIER, "array")
    parser.ensure_token(TokenType.OPEN_SQUARE)
    target_type = parse_any_type_decl(parser)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    return tlcore.ListType(target_type, annotations = annotations, docs = parser.last_docstring())

def parse_map_type_decl(parser, annotations = []):
    parser.ensure_token(TokenType.IDENTIFIER, "map")
    parser.ensure_token(TokenType.OPEN_SQUARE)
    key_type = parse_any_type_decl(parser)
    parser.ensure_token(TokenType.COMMA)
    value_type = parse_any_type_decl(parser)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    return tlcore.MapType(key_type, value_type, annotations = annotations, docs = parser.last_docstring())

def parse_complex_type_decl(parser, annotations = [], typereffed_fqn = None):
    type_class = parser.ensure_token(TokenType.IDENTIFIER)
    if type_class not in ["union", "enum", "record"]:
        raise UnexpectedTokenException(parser.peek_token(), "union", "enum", "record")

    newtype = None
    fqn = typereffed_fqn
    if parser.peeked_token_is(TokenType.IDENTIFIER):
        # we have a name
        n = parser.ensure_token(TokenType.IDENTIFIER)
        ns = parser.document.namespace
        n,ns,fqn = utils.normalize_name_and_ns(n, ns)

    if type_class == "enum":
        newtype = tlenums.EnumType(annotations = annotations, docs = parser.last_docstring())
        if fqn:
            newtype = parser.register_type(fqn, newtype)
            newtype.type_data.fqn = fqn
        parse_enum_body(parser, newtype)
    elif type_class == "union":
        newtype = tlcore.UnionType([], annotations = annotations, docs = parser.last_docstring())
        if fqn:
            newtype = parser.register_type(fqn, newtype)
        parse_union_body(parser, newtype)
    elif type_class == "record":
        newtype = records.RecordType(records.Record(fqn, None, None), annotations = annotations, docs = parser.last_docstring())
        record_data = newtype.type_data
        if fqn:
            newtype = parser.register_type(fqn, newtype)
            print "Parsing new record: '%s'" % fqn

        parse_record_body(parser, newtype)

        # Try for a resolution if we dont want lazy evaluation
        if not parser.lazy_resolution_enabled:
            newtype.resolve(parser.onering_context.type_registry, parser.resolver)
    else:
        assert False

    assert newtype is not None, "A type was NOT parsed"
    return newtype

########################################################################
##          Enum and Union parsing
########################################################################

def parse_enum_body(parser, enum_type):
    """
    Parse the body of an enum declaration:

        "{" enum_symbols + "}"
    """
    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        annotations = parse_annotations(parser)
        symbol = parser.ensure_token(TokenType.IDENTIFIER)
        enum_type.type_data.add_symbol(symbol, annotations, parser.last_docstring)
        # consume comma silently
        parser.next_token_if(TokenType.COMMA, consume = True)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    return enum_type

def parse_union_body(parser, union_type):
    """
    Parse the body of an union declaration:
        "{" any_type_decl + "}"
    """
    parser.ensure_token(TokenType.OPEN_SQUARE)
    while not parser.peeked_token_is(TokenType.CLOSE_SQUARE):
        child_type = parse_any_type_decl(parser)
        union_type.add_child(child_type)
        parser.next_token_if(TokenType.COMMA, consume = True)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    return union_type

########################################################################
##          Record and Field parsing
########################################################################

def parse_record_body(parser, parent_record):
    """
    Parses the body of a record declaration:

        record_type_body := "{" ( annotation * field_declaration ) * "}"

    """
    parser.ensure_token(TokenType.OPEN_BRACE)

    # read annotations as they can be used by ... or field projections
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        # read a field projection
        parse_field_declaration(parser, parent_record)

    parser.ensure_token(TokenType.CLOSE_BRACE)
    return parent_record

def parse_field_declaration(parser, parent_record):
    """
        field_declaration := annotations ? IDENTIFIER ":" type_decl "?" ? ( "=" literal_value ) ?
    """
    annotations = parse_annotations(parser)
    docstring = parser.last_docstring()
    field_name = parser.ensure_token(TokenType.IDENTIFIER)
    parser.ensure_token(TokenType.COLON)
    field_type = parse_any_type_decl(parser)
    is_optional = False
    default_value = None

    if parser.next_token_is(TokenType.QUESTION):
        is_optional = True

    if parser.next_token_is(TokenType.EQUALS):
        default_value = parser.ensure_literal_value()

    child_data = records.FieldData(field_name, parent_record, is_optional, default_value)
    parent_record.add_child(field_type, field_name, docstring, annotations, child_data)
