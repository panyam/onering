
from __future__ import absolute_import
import ipdb
from onering import utils
from onering.dsl.errors import SourceException, UnexpectedTokenException
from onering.dsl.lexer import Token, TokenType
from onering.core import interfaces
from onering.core import exprs as orexprs
from onering.dsl.parser.rules.annotations import parse_annotations
from onering.dsl.parser.rules.misc import parse_field_path

########################################################################
##          Interface Parsing Rules
########################################################################

def parse_interface(parser, annotations, typereffed_fqn = None, parent_interface = None):
    """
    Parses interface declarations

        interface name<IDENT>    "{" interface_decl * "}"
    """
    parser.ensure_token(TokenType.IDENTIFIER, "interface")
    fqn = utils.FQN(parser.ensure_token(TokenType.IDENTIFIER), parser.namespace).fqn
    print "Parsing new interface: '%s'" % fqn

    interface = interfaces.Interface(fqn, parent = parent_interface,
                                     annotations = annotations,
                                     docs = parser.last_docstring())
    parser.onering_context.register_interface(interface)

    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        # We can have functions or interfaces here
        annotations = parse_annotations(parser)
        if parser.peeked_token_is(TokenType.IDENTIFIER, "func"):
            # parse a function that goes in this interface
            interface.add_function(parse_named_function(parser, annotations))
        else:
            # parse a child interface
            interface.add_child(parse_interface(parser, annotations, interface))
    parser.ensure_token(TokenType.CLOSE_BRACE)

    return interface

def parse_named_function(parser, annotations):
    """Parses a function.

    **Rule:**

        "func"  name<IDENT>  "(" param_name ":" param_type ( "," param_name ":" param_type ) * ")" ( "=>" output_type ) ?
    """
    parser.ensure_token(TokenType.IDENTIFIER, "func")
