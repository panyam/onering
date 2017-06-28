
from __future__ import absolute_import 

import ipdb
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

        type_declaration := annotation * ( typeref_decl | custom_type_decl )
    """
    annotations = parse_annotations(parser)
    is_extern = False
    if parser.next_token_if(TokenType.IDENTIFIER, "extern", consume = True):
        is_extern = True
    entity_class = parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    entity_parser = parser.get_entity_parser(entity_class)
    if entity_parser:
        return entity_parser(parser, is_external = is_extern, annotations = annotations)
    else:
        return parse_type_initializer_or_name(parser, annotations = annotations)

def parse_typeref_decl(parser, annotations, **kwargs):
    """
    Parses typeref declaration of the form:

        "typeref" <name> ( "<" type_params ">" ) ? "=" entity
    """
    parser.ensure_token(TokenType.IDENTIFIER, "typeref")
    name, type_params, docs = parse_typefunc_preamble(parser, name_required = True, allow_generics = True)
    parser.ensure_token(TokenType.EQUALS)

    # create the typeref
    typeref = tlcore.make_typeref(name, ensure_typeexpr(parser), parent = parser.current_module, annotations = annotations, docs = docs)
    if type_params:
        typeref = tlcore.TypeFun(name, type_params, typeref, None, parent = parser.current_module, annotations = annotations, docs = docs)
    print "Registering new typeref: '%s'" % name
    parser.add_entity(name, typeref)
    return typeref

def ensure_typeexpr(parser, annotations = None):
    out = parse_entity(parser)
    if not issubclass(out.__class__, tlcore.Expr):
        ipdb.set_trace()
        assert False
    return out

def parse_type_initializer_or_name(parser, annotations):
    """
    Parses a parametric type:

        type_name ( "<" args ">" ) ?
    """
    if not parser.peeked_token_is(TokenType.IDENTIFIER):
        ipdb.set_trace()
        return None
    fqn = parser.ensure_fqn()

    if parser.next_token_is(parser.GENERIC_OPEN_TOKEN):
        child_typeexprs = [ ensure_typeexpr(parser) ]
        while not parser.peeked_token_is(parser.GENERIC_CLOSE_TOKEN):
            parser.ensure_token(TokenType.COMMA)
            child_typeexprs.append(ensure_typeexpr(parser))
        parser.ensure_token(parser.GENERIC_CLOSE_TOKEN)
        return tlcore.TypeApp(tlcore.Variable(fqn), child_typeexprs)

    # Otherwise we just have a Variable
    return tlcore.Variable(fqn)

def parse_typefunc_preamble(parser, name_required = False, allow_generics = True):
    name = None
    if name_required or parser.peeked_token_is(TokenType.IDENTIFIER):
        name = parser.ensure_token(TokenType.IDENTIFIER)

    # Type params
    type_params = []
    if allow_generics:
        if parser.next_token_is(parser.GENERIC_OPEN_TOKEN):
            type_params.append(parser.ensure_token(TokenType.IDENTIFIER))
            while not parser.peeked_token_is(parser.GENERIC_CLOSE_TOKEN):
                parser.ensure_token(TokenType.COMMA)
                type_params.append(parser.ensure_token(TokenType.IDENTIFIER))
            parser.ensure_token(parser.GENERIC_CLOSE_TOKEN)

    docs = parser.last_docstring()
    return name, type_params, docs


########################################################################
##          Extern type parsing
########################################################################

def parse_extern_type(parser, annotations = None):
    """ Enables parsing of external types - ie types that are just contexts which we may 
    not know anything re its implementation but we just need a wrapper type. eg with List<a>
    we have no idea what List means and that it is defined externally but we want to deal
    with them as types.

    extern_type := "extern" name<IDENT> "<" type_params ">"
    """
    parser.ensure_token(TokenType.IDENTIFIER, "extern")
    name, type_params, docs = parse_typefunc_preamble(parser, name_required = True)

    type_func = tlcore.make_wrapper_type(name, type_params, parser.current_module,
                                         annotations = annotations, docs = docs)
    parser.add_entity(name, type_func)
    return type_func


########################################################################
##          Enum and Union parsing
########################################################################

def parse_enum(parser, is_external, annotations = None):
    """
    Parses an enum declaration of the form:

        enum ( "[" type "]" ) ? enum_body
    """
    parser.ensure_token(TokenType.IDENTIFIER, "enum")
    name, type_params, docs = parse_typefunc_preamble(parser, True, allow_generics = False)
    type_args = None
    if parser.next_token_is(parser.GENERIC_OPEN_TOKEN):
        type_args = [ensure_typeexpr(parser)]
        parser.ensure_token(parser.GENERIC_CLOSE_TOKEN)

    symbols = parse_enum_body(parser)
    entity = tlenums.EnumType(name, None, symbols, type_args, annotations = annotations, docs = docs)
    parser.add_entity(name, entity)
    return entity

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
        symbols.append(tlenums.EnumSymbol(name, None, value, annotations, parser.last_docstring()))
        # consume comma silently
        parser.next_token_if(TokenType.COMMA, consume = True)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    return symbols

########################################################################
##          Union/Record and Field parsing
########################################################################

def parse_record_or_union(parser, is_external, annotations = None):
    constructor = parser.ensure_token(TokenType.IDENTIFIER)
    assert constructor in ("record", "union")

    name, type_params, docs = parse_typefunc_preamble(parser)
    fields = parse_record_body(parser)
    outtype = tlcore.make_type(constructor, name, fields, None, parent = parser.current_module, annotations = annotations, docs = docs)
    if type_params:
        outtype = tlcore.TypeFun(name, type_params, outtype, parent = parser.current_module, annotations = annotations, docs = docs)
    parser.add_entity(name, outtype)
    return outtype

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
    field_typeexpr = ensure_typeexpr(parser)
    # if we declared an inline Type then dont refer to it directly but via a Variable
    if type(field_typeexpr) is tlcore.Fun and field_typeexpr.name:
        field_typeexpr = tlcore.Variable(field_typeexpr.name)
    is_optional = False
    default_value = None

    if parser.next_token_is(TokenType.QMARK):
        is_optional = True

    if parser.next_token_is(TokenType.EQUALS):
        default_value = parser.ensure_literal_value()

    field = tlcore.TypeArg(field_name, field_typeexpr, is_optional, default_value, annotations, docstring)
    return field
