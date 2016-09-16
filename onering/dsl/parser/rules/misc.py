
from __future__ import absolute_import

from onering.dsl.lexer import Token, TokenType

def parse_namespace(parser):
    """
    Parse the namespace for the current document.
    """
    if parser.next_token_is(TokenType.IDENTIFIER, tok_value = "namespace"):
        parser.document.namespace = parser.ensure_fqn()
    parser.consume_tokens(TokenType.SEMI_COLON)

def parse_declaration(parser):
    """
    Parse the declarations for the current document:

        declaration := import_statement | type_declaration
    """
    next = parser.peek_token()
    if next.tok_type == TokenType.EOS:
        return False

    if next.tok_type == TokenType.IDENTIFIER and next.value == "import":
        parse_import_decl(parser)
    else:
        from onering.dsl.parser.rules.types import parse_type_decl
        parse_type_decl(parser)
    parser.consume_tokens(TokenType.SEMI_COLON)
    return True

def parse_import_decl(parser):
    """
    Parse import declarations of the form below and adds it to the current document.

        import IDENTIFIER ( "." IDENTIFIER ) *
    """
    parser.ensure_token(TokenType.IDENTIFIER, "import")
    fqn = parser.ensure_fqn()
    parser.add_import(fqn)
    return fqn

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

    from onering.core import projections
    out = projections.FieldPath(field_path_parts, selected_children)
    if out.is_blank: out = None
    return out
