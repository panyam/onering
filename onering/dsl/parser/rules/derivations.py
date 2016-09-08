
from onering import utils
from onering.dsl.lexer import Token, TokenType
from onering.core import derivations

from annotations import parse_annotations
from types import parse_any_type_decl

########################################################################
##          Derivation and Projection Parsing
########################################################################

def parse_derivation(parser, annotations = []):
    """
    Parses a derivation

    derivation := "derive" FQN derivation_header derivation_body
    """
    parser.ensure_token(TokenType.IDENTIFIER, "derive")

    n = parser.ensure_token(TokenType.IDENTIFIER)
    ns = parser.document.namespace
    n,ns,fqn = utils.normalize_name_and_ns(n, ns)
    print "Parsing new derivation: '%s'" % fqn

    derivation = derivations.Derivation(fqn, None, annotations = annotations, docs = parser.last_docstring())
    parse_derivation_header(parser, derivation)
    parse_derivation_body(parser, derivation)
    parser.onering_context.register_derivation(derivation)


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
        source_type = parser.get_type(source_fqn)
        assert source_type != None, "Source type must be in registry even if it is unresolved"
        derivation.add_source_record(source_fqn, source_type, source_alias)
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

    parser.ensure_token(TokenType.CLOSE_BRACE)
    return derivation

def parse_projection(parser, parent_entity, allow_renaming = True,
                     allow_optionality = True, allow_default_value = True):
    """
    Parse a field projection:

        projection_source projection_target
    """
    annotations = parse_annotations(parser)
    projection = derivations.Projection(parent_entity, None, None, None, annotations)
    parse_projection_source(parser, projection)
    if projection.field_path is None or not projection.field_path.has_children:
        parse_projection_target(parser, projection,
                                allow_optionality = allow_optionality,
                                allow_default_value = allow_default_value)
    parser.consume_tokens(TokenType.SEMI_COLON)
    return projection

def parse_projection_source(parser, projection, allow_renaming = True):
    """
    Parse a field projection source:
        projection :=   field_path "/" *
                    |   field_path "/" "(" IDENTIFIER ( "," IDENTIFIER ) * ")"
                    |   field_path ( "as" IDENTIFIER ) ? 
    """
    projection.field_path = parse_field_path(parser)
    if projection.field_path:
        if allow_renaming:
            # Now check for renaming ie "as" <newname>
            if parser.next_token_is(TokenType.IDENTIFIER, "as"):
                projection.target_name = parser.ensure_token(TokenType.IDENTIFIER)

def parse_projection_target(parser, parent_projection,
                            allow_retyping = True, allow_optionality = True, allow_default_value = True):
    """
    Parse a field projection target:
        projection :=   (
                            ( ":" ( any_type_decl | record_type_body ) )
                            | 
                            type_streaming_declaration
                        ) ?
                        "?" ?
                        ( "=" literal_value ) ?
    """
    target_type = None
    is_optional = None
    default_value = None
    projection_type = derivations.PROJECTION_TYPE_PLAIN

    # Check if we have a mutation or a type declaration            
    if allow_retyping:
        if parser.next_token_is(TokenType.COLON):
            if parser.peeked_token_is(TokenType.IDENTIFIER):
                projection_type = derivations.PROJECTION_TYPE_RETYPE
                target_type = parse_any_type_decl(parser)
                # TODO: Investigate if and when we should parent record here
            else:
                raise UnexpectedTokenException(parser.peek_token(), TokenType.IDENTIFIER)
        elif parser.next_token_is(TokenType.STREAM):
            # We have an inline derivation
            new_record_name = None
            if parser.peeked_token_is(TokenType.IDENTIFIER):
                new_record_name = parser.next_token().value

            derivation = derivations.Derivation(new_record_name, parent_projection)
            target_type = parse_derivation_body(parser, derivation)
            projection_type = derivations.PROJECTION_TYPE_DERIVATION
        elif parser.peeked_token_is(TokenType.OPEN_SQUARE):
            # We have type streaming with bound param names
            projection_type, target_type = parse_type_stream_decl(parser, parent_projection)

    # check optionality
    if allow_optionality:
        if parser.next_token_is(TokenType.QUESTION):
            is_optional = True

    # Check for default value
    if allow_default_value:
        if parser.next_token_is(TokenType.EQUALS):
            default_value = parser.ensure_literal_value()

    parent_projection.target_type = target_type
    parent_projection.is_optional = is_optional
    parent_projection.default_value = default_value
    parent_projection.projection_type = projection_type

def parse_field_path(parser, allow_abs_path = True, allow_child_selection = True):
    """
    Parses a field path of the form:

        field_path  := "/" ?
                       ( IDENTIFIER ( "/" IDENTIFIER ) * ) ?
                       ( "/" ( " * " | "(" IDENTIFIER ( ", " IDENTIFIER ) * ")" ) ) ?
            
    """
    # negates_inclusion = parser.next_token_is(TokenType.MINUS)
    field_path_parts = []

    # If absolute path then
    starts_with_slash = False
    if allow_abs_path:
        starts_with_slash = parser.next_token_is(TokenType.SLASH)

    # read field_path parts
    # field path parts could have following
    if parser.peeked_token_is(TokenType.IDENTIFIER):
        field_path_parts.append(parser.ensure_fqn())
        while parser.peeked_token_is(TokenType.SLASH):
            tok = parser.next_token()
            if not parser.peeked_token_is(TokenType.IDENTIFIER):
                parser.unget_token(tok)
                break
            field_path_parts.append(parser.ensure_token(TokenType.IDENTIFIER))

    # check for multi part includes
    selected_children = None
    if allow_child_selection:
        if parser.next_token_is(TokenType.SLASH) or (starts_with_slash and not field_path_parts):
            if parser.next_token_is(TokenType.OPEN_PAREN):
                selected_children = []
                while not parser.next_token_is(TokenType.CLOSE_PAREN):
                    if parser.next_token_is(TokenType.STAR):
                        selected_children = "*"
                        parser.ensure_token(TokenType.CLOSE_PAREN)
                        break
                    else:
                        name = parser.ensure_token(TokenType.IDENTIFIER)
                        selected_children.append(name)
                        if parser.next_token_is(TokenType.COMMA):
                            parser.ensure_token(TokenType.IDENTIFIER, peek = True)
            else:
                raise UnexpectedTokenException(parser.peek_token(), TokenType.STAR, TokenType.OPEN_BRACE)

    if starts_with_slash:
        field_path_parts.insert(0, "")
    out = derivations.FieldPath(field_path_parts, selected_children)
    if out.is_blank: out = None
    return out

def parse_type_stream_decl(parser, parent_projection):
    """
    Parses a type stream declaration:


        type_stream_decl := "[" arglist "]" "=>" TYPE<IDENTIFIER> "[" derivations "]" 
    """
    # Parse the argument list of what is being streamed
    param_names = []
    if parser.next_token_is(TokenType.OPEN_SQUARE):
        param_names = parser.read_ident_list(TokenType.COMMA)
        parser.ensure_token(TokenType.CLOSE_SQUARE)

    parser.ensure_token(TokenType.STREAM)

    children = []

    # There MUST be a type constructor
    type_constructor = parser.ensure_fqn()

    parser.ensure_token(TokenType.OPEN_SQUARE)

    annotations = parse_annotations(parser)
    while not parser.peeked_token_is(TokenType.CLOSE_SQUARE):
        if parser.peeked_token_is(TokenType.OPEN_BRACE):
            # Then we have a complete derivation body
            derivation = derivations.Derivation(None, None, annotations = annotations, docs = parser.last_docstring())
            parse_derivation_body(parser, derivation)
            children.append(derivation)
        else:
            # TODO - Need annotations?
            projection = parse_projection(parser, parent_entity = parent_projection, allow_renaming = False,
                                          allow_optionality = False, allow_default_value = False)
            children.append(projection)
        # Consume a comma silently 
        parser.next_token_if(TokenType.COMMA, consume = True)
        annotations = parse_annotations(parser)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    target_type = derivations.TypeStreamDeclaration(type_constructor, param_names, children)
    return derivations.PROJECTION_TYPE_STREAMING, target_type
