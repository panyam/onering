
from __future__ import absolute_import
import ipdb
from onering.dsl import errors
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations
from onering.utils.misc import FQN

########################################################################
##                  Module Parsing Rules
##
##  module := "module" name "{" 
##                  top_level_statements
##             "}"
## 
##  top_level_statements :=  type_statements
## 
########################################################################


def parse_module(parser, annotations, **kwargs):
    """ Parses a module definition and returns `Module` instance. """
    parser.ensure_token(TokenType.IDENTIFIER, "module")
    fqn = parser.ensure_fqn()
    last_module, module = parser.push_module(fqn, annotations, parser.last_docstring())
    parser.ensure_token(TokenType.OPEN_BRACE)
    parse_module_body(parser, module)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    parser.pop_to_module(last_module)
    return module

def parse_module_body(parser, module):
    """ Parses the body of a module. """
    while parse_declaration(parser, module):
        pass
    return module

def parse_declaration(parser, module):
    """
    Parse the declarations for the current document:

        declaration := import_statement | type_declaration
    """
    next = parser.peek_token()
    if next.tok_type == TokenType.EOS or next.tok_type == TokenType.CLOSE_BRACE:
        return False

    if next.tok_type == TokenType.IDENTIFIER and next.value == "import":
        parse_import(parser)
    else:
        from onering.dsl.parser.rules.types import parse_entity
        if not parse_entity(parser):
            raise errors.UnexpectedTokenException(parser.peek_token())
    parser.consume_tokens(TokenType.SEMI_COLON)
    return True

def parse_import(parser):
    """
    Parse import declarations of the form below and adds it to the current document.

        import IDENTIFIER ( "." IDENTIFIER ) * ( as IDENTIFIER ) ?
    """
    parser.ensure_token(TokenType.IDENTIFIER, "import")
    fqn = parser.ensure_fqn()
    alias = FQN(fqn, None).name
    if parser.next_token_is(TokenType.IDENTIFIER, "as"):
        # we also have an alias for the import
        alias = parser.ensure_token(TokenType.IDENTIFIER)
    parser.current_module.set_alias(alias, fqn)
    return fqn
