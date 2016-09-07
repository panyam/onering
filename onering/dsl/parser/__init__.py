
import ipdb
from tokstream import TokenStream
from onering.dsl.errors import SourceException, UnexpectedTokenException
from typelib import core as tlcore
from typelib import utils
from typelib import records
from typelib import annotations as tlannotations
from typelib import enums as tlenums
from onering.dsl.lexer import Token, TokenType
from onering.dsl import core
from onering import errors
from onering.core import derivations
from onering.core import transformers

from rules.misc import parse_namespace
from rules.misc import parse_declaration

class Parser(TokenStream):
    """
    Parses a Onering compilation unit and extracts all records define in it.
    """
    def __init__(self, instream, context):
        """
        Creates a parser.

        Params:

            instream    -   The input stream from which onering entities will be parsed and registered.
            context     -   The onering context into which all loaded entities will be registered into.
        """
        from onering.dsl import lexer
        super(Parser, self).__init__(lexer.Lexer(instream))
        self.document = core.Document()
        self.imports = []
        self._last_docstring = ""
        self.injections = {}
        self.onering_context = context
        self.lazy_resolution_enabled = True

    def get_type(self, fqn):
        """
        Get's the type corresponding to the given fqn if it exists
        otherwise returns an unresolved type as a place holder until
        it can be resolved.
        """
        t = self.onering_context.type_registry.get_type(fqn, nothrow = True)
        if not t:
            # TODO: if the fqn is actually NOT fully qualified, then
            # see if this matches any of the ones in the import decls

            fqn = self.normalize_fqn(fqn)
            t = self.onering_context.type_registry.get_type(fqn, nothrow = True)

            if not t:
                # Try with the namespace as well
                n,ns,fqn = utils.normalize_name_and_ns(fqn, self.document.namespace, ensure_namespaces_are_equal=False)
                t = self.onering_context.type_registry.get_type(fqn, nothrow = True)
                if not t:
                    t = self.onering_context.type_registry.register_type(fqn, None)
        return t

    def register_type(self, name, newtype):
        return self.onering_context.type_registry.register_type(name, newtype)

    def normalize_fqn(self, fqn):
        if "." in fqn:
            return fqn

        for imp in self.imports:
            if imp.endswith("." + fqn):
                return imp

        n,ns,fqn = utils.normalize_name_and_ns(fqn, self.document.namespace)
        return fqn

    def add_import(self, fqn):
        # see if a type needs to be created
        if not self.onering_context.type_registry.get_type(fqn, nothrow = True):
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

