
from __future__ import absolute_import

import ipdb
from typecube import core as tccore
from typecube import ext as tcext
from onering.dsl.parser.tokstream import TokenStream
from onering.dsl import errors
from onering.dsl.lexer import Token, TokenType

class Parser(TokenStream):
    """
    Parses a Onering compilation unit and extracts all records define in it.
    """

    GENERIC_OPEN_TOKEN = TokenType.LT
    GENERIC_CLOSE_TOKEN = TokenType.GT

    def __init__(self, lexer_or_stream, context, root_module = None):
        """
        Creates a parser.

        Params:

            instream    -   The input stream from which onering entities will be parsed and registered.
            context     -   The onering context into which all loaded entities will be registered into.
            root_module -   The module underwhich all declarations will be added/loaded.
        """
        lexer_or_stream
        from onering.dsl import lexer
        if type(lexer_or_stream) is not lexer.Lexer:
            lexer_or_stream = lexer.Lexer(lexer_or_stream, source_uri = None)
        super(Parser, self).__init__(lexer_or_stream)

        # The root module corresponds to the top level entity and has no name really
        self.current_module = self.root_module = root_module or context.global_module
        self._entity_parsers = {}
        self.found_entities = {}
        self._last_docstring = ""
        self.injections = {}
        self.onering_context = context
        self.use_default_parsers()

    def use_default_parsers(self):
        from onering.dsl.parser.rules.types import parse_alias_decl
        self.register_entity_parser("alias", parse_alias_decl)

        from onering.dsl.parser.rules.types import parse_record_or_union
        self.register_entity_parser("record", parse_record_or_union)
        self.register_entity_parser("union", parse_record_or_union)

        from onering.dsl.parser.rules.types import parse_enum
        self.register_entity_parser("enum", parse_enum)

        from onering.dsl.parser.rules.modules import parse_module
        self.register_entity_parser("module", parse_module)

        from onering.dsl.parser.rules.functions import parse_function, parse_quant_spec
        self.register_entity_parser("fun", parse_function)
        self.register_entity_parser("funi", parse_quant_spec)

    def get_entity_parser(self, entity_class):
        return self._entity_parsers.get(entity_class, None)

    def register_entity_parser(self, keyword, parser):
        self._entity_parsers[keyword] = parser

    def add_entity(self, name, entity):
        if name:
            parent_fqn = self.current_module.fqn
            fqn = parent_fqn + "." + name
            assert fqn not in self.found_entities, "Entity '%s' already exists in module '%s'" % (name, parent_fqn)
            self.found_entities[fqn] = entity
            self.current_module.add(name, entity)

    def last_docstring(self, reset = True):
        out = self._last_docstring
        if reset:
            self._last_docstring = ""
        return out

    def reset_last_docstring(self):
        self._last_docstring = ""

    def ensure_literal_value(self):
        from onering.dsl.parser.rules.exprs import parse_expr
        return parse_expr(self)

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
        try:
            # parse_namespace()
            from onering.dsl.parser.rules.modules import parse_module_body
            parse_module_body(self, self.root_module)
        except errors.SourceException:
            raise
        except errors.OneringException, exc:
            # Change its message to reflect the line and col
            raise errors.SourceException(self.line, self.column, exc.message)
        except:
            raise
        return self.root_module

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

