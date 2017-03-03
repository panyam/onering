
from __future__ import absolute_import

import ipdb
from onering.dsl.parser.tokstream import TokenStream
from onering.dsl.errors import SourceException, UnexpectedTokenException
from typelib import utils
from onering.dsl.lexer import Token, TokenType
from onering import errors

from onering.dsl.parser.rules.misc import parse_namespace, parse_declaration

class Parser(TokenStream):
    """
    Parses a Onering compilation unit and extracts all records define in it.
    """
    def __init__(self, lexer_or_stream, context):
        """
        Creates a parser.

        Params:

            instream    -   The input stream from which onering entities will be parsed and registered.
            context     -   The onering context into which all loaded entities will be registered into.
        """
        lexer_or_stream
        from onering.dsl import lexer
        if type(lexer_or_stream) is not lexer.Lexer:
            lexer_or_stream = lexer.Lexer(lexer_or_stream, source_uri = None)
        super(Parser, self).__init__(lexer_or_stream)
        self.namespace = None
        self.imports = []
        self._entity_parsers = {}
        self._last_docstring = ""
        self.injections = {}
        self.onering_context = context
        self.use_default_parsers()

    def use_default_parsers(self):
        from onering.dsl.parser.rules.types import parse_typeref_decl
        self.register_entity_parser("typeref", parse_typeref_decl)

        from onering.dsl.parser.rules.types import parse_record
        self.register_entity_parser("record", parse_record)

        from onering.dsl.parser.rules.types import parse_enum
        self.register_entity_parser("enum", parse_enum)

        from onering.dsl.parser.rules.interfaces import parse_interface
        self.register_entity_parser("interface", parse_interface)

        from onering.dsl.parser.rules.derivations import parse_derivation
        self.register_entity_parser("derive", parse_derivation)

        from onering.dsl.parser.rules.platforms import parse_platform
        self.register_entity_parser("platform", parse_platform)

        from onering.dsl.parser.rules.transformers import parse_transformer_group
        self.register_entity_parser("transformers", parse_transformer_group)

    def get_entity_parser(self, entity_class):
        return self._entity_parsers.get(entity_class, None)

    def register_entity_parser(self, keyword, parser):
        if keyword in ("import", "namespace"):
            raise Exception("Keyword '%s' is a reserved keyword" % keyword)
        self._entity_parsers[keyword] = parser

    def get_typeref(self, fqn):
        """
        Get's the reference to a type type corresponding to the given fqn 
        if it exists otherwise returns an unresolved type as a place holder 
        until it can be resolved.
        """
        tref = self.onering_context.type_registry.get_typeref(fqn, nothrow = True)
        if not tref:
            # TODO: if the fqn is actually NOT fully qualified, then
            # see if this matches any of the ones in the import decls

            fqn = self.normalize_fqn(fqn)
            tref = self.onering_context.type_registry.get_typeref(fqn, nothrow = True)

            if not tref:
                # Try with the namespace as well
                fqn = utils.FQN(fqn, self.namespace, ensure_namespaces_are_equal=False).fqn
                tref = self.onering_context.type_registry.get_typeref(fqn, nothrow = True)
                if not tref:
                    tref = self.onering_context.type_registry.register_type(fqn, None)
        return tref

    def register_type(self, name, newtype):
        return self.onering_context.type_registry.register_type(name, newtype, overwrite = True)

    def normalize_fqn(self, fqn):
        if "." in fqn:
            return fqn

        for imp in self.imports:
            if imp.endswith("." + fqn):
                return imp

        fqn = utils.FQN(fqn, self.namespace).fqn
        return fqn

    def add_import(self, fqn, alias):
        # see if a type needs to be created
        if not self.onering_context.type_registry.get_typeref(fqn, nothrow = True):
            self.onering_context.type_registry.register_type(fqn, None)
        self.imports.append(fqn)

    def last_docstring(self, reset = True):
        out = self._last_docstring
        if reset:
            self._last_docstring = ""
        return out

    def reset_last_docstring(self):
        self._last_docstring = ""

    def read_ident_list(self, delim = TokenType.COMMA):
        names = [self.ensure_token(TokenType.IDENTIFIER)]
        while self.next_token_is(delim):
            names.append(self.ensure_token(TokenType.IDENTIFIER))
        return names

    def ensure_literal_value(self):
        if self.peeked_token_is(TokenType.NUMBER):
            # TODO: handle long vs int vs float etc
            return self.ensure_token(TokenType.NUMBER)
        elif self.peeked_token_is(TokenType.STRING):
            return self.ensure_token(TokenType.STRING)
        elif self.peeked_token_is(TokenType.IDENTIFIER):
            return self.ensure_fqn()
        elif self.peeked_token_is(TokenType.OPEN_SQUARE):
            raise errors.OneringException("Json Array literals not yet implemented")
        elif self.peeked_token_is(TokenType.OPEN_BRACE):
            raise errors.OneringException("Json Dict literals not yet implemented")
        else:
            raise UnexpectedTokenException(self.peek_token(), TokenType.STRING, TokenType.NUMBER, TokenType.IDENTIFIER)

    def ensure_fqn(self, delim_token = None):
        """
        Expects and parses a fully qualified name defined as:

            IDENT ( <delim> IDENT ) *
        """
        delim_token = delim_token or TokenType.DOT
        fqn = self.ensure_token(TokenType.IDENTIFIER)

        # no comments inside FQNs
        # self.lexer.comments_enabled = False
        while self.peeked_token_is(delim_token):
            tok = self.next_token()
            if self.peeked_token_is(TokenType.IDENTIFIER):
                fqn += "." + self.next_token().value
            else:
                self.unget_token(tok)
                break
        # self.lexer.comments_enabled = True
        return fqn

    def parse(self):
        """
        Parses a Onering compilation unit.

        compilation_unit := 
            namespace_decl ?

            (import_decl | type_decl) *
        """
        try:
            parse_namespace(self)
            while parse_declaration(self):
                pass
        except SourceException:
            raise
        except errors.OneringException, exc:
            # Change its message to reflect the line and col
            raise SourceException(self.line, self.column, exc.message)
        except:
            raise
        # Take care of injections!

    def process_directive(self, command):
        parts = [c.strip() for c in command.split(" ") if c.strip()]
        if parts:
            if parts[0] == "inject":
                # add to an injection
                if len(parts) != 4:
                    raise errors.OneringException("'inject' directive usage: 'inject <MasterType> with <DerivedType>'")
                self.injections[parts[3]] = parts[1]
            else:
                raise errors.OneringException("Invalid directive: '%s'" % command)

