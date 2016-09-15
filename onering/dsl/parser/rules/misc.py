
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
