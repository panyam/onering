
from __future__ import absolute_import

import ipdb
from onering.dsl.parser.tokstream import TokenStream
from onering.dsl.errors import SourceException, UnexpectedTokenException
from onering.entities.modules import Module
from typelib.utils import FQN
from onering.dsl.lexer import Token, TokenType
from onering import errors

class Parser(TokenStream):
    """
    Parses a Onering compilation unit and extracts all records define in it.
    """

    GENERIC_OPEN_TOKEN = TokenType.LT
    GENERIC_CLOSE_TOKEN = TokenType.GT

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

        # The root module corresponds to the top level entity and has no name really
        self.root_module = None
        self.current_module = None
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

        from onering.dsl.parser.rules.modules import parse_module
        self.register_entity_parser("module", parse_module)

        from onering.dsl.parser.rules.functions import parse_function
        self.register_entity_parser("fun", parse_function)

        # from onering.dsl.parser.rules.platforms import parse_platform
        # self.register_entity_parser("platform", parse_platform)

        # from onering.dsl.parser.rules.transformers import parse_transformer_group
        # self.register_entity_parser("transformers", parse_transformer_group)

    def get_entity_parser(self, entity_class):
        return self._entity_parsers.get(entity_class, None)

    def register_entity_parser(self, keyword, parser):
        if keyword in ("import", "namespace"):
            raise Exception("Keyword '%s' is a reserved keyword" % keyword)
        self._entity_parsers[keyword] = parser

    def get_entity(self, key):
        """ Resolve an entity by key. 

        If the key is a fully qualified name then lookup starts from the context's root
        otherwise if it is not then first the current module is looked up and THEN
        from the context's root.  Other lookup strategies can be explored later on.
        """
        parts = key.split(".")
        entity = self.current_module.resolve_key_parts(parts)
        if not entity:
            entity = self.onering_context.global_module.resolve_key_parts(parts)
        return entity

    def get_typeref(self, fqn):
        """
        Get's the reference to a type type corresponding to the given fqn 
        if it exists otherwise returns an unresolved type as a place holder 
        until it can be resolved.
        """
        entity = self.get_entity(fqn)
        if not entity:
            entity = self.current_module.ensure_key(fqn.split("."))
        return entity

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

            module
        """
        def parse_namespace():
            """
            Parse the namespace for the current document.
            """
            if self.next_token_is(TokenType.IDENTIFIER, tok_value = "namespace"):
                self.namespace = self.ensure_fqn()
            self.consume_tokens(TokenType.SEMI_COLON)

        try:
            # parse_namespace()
            from onering.dsl.parser.rules.modules import parse_module_body
            self.current_module = self.root_module = Module(self.namespace)
            parse_module_body(self, self.root_module)
        except SourceException:
            raise
        except errors.OneringException, exc:
            # Change its message to reflect the line and col
            raise SourceException(self.line, self.column, exc.message)
        except:
            raise
        # Take care of injections!
        return self.root_module

    def push_module(self, fqn, annotations, docs):
        parts = fqn.split(".")
        last_module = self.current_module
        for index,part in enumerate(parts):
            if index == len(parts) - 1:
                self.current_module = Module(part, self.current_module, annotations, docs)
            else:
                self.current_module = Module(part, self.current_module)
        return last_module, self.current_module

    def pop_to_module(self, module):
        while self.current_module != module:
            self.current_module = self.current_module.parent
        return self.current_module

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

