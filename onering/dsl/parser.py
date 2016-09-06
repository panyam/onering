
import ipdb
import core
from tokstream import TokenStream
from errors import SourceException, UnexpectedTokenException
from typelib import core as tlcore
from typelib import utils
from typelib import records
from typelib import annotations as tlannotations
from typelib import enums as tlenums
from lexer import Token, TokenType
from onering import errors
from onering.core import derivations
from onering.core import transformers

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
        import lexer
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
        try:
            parse_compilation_unit(self)
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

########################################################################
##          Production rules
########################################################################

def parse_compilation_unit(parser):
    """
    Parses a Onering compilation unit.

    compilation_unit := 
        NAMESPACE_DECL ?

        (IMPORT_DECL | TYPE_DECL) *
    """
    parse_namespace(parser)
    while parse_declaration(parser): pass

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

########################################################################
##          Type declaration parsing rules
########################################################################

def parse_type_decl(parser):
    """
    Parses top level type declarations:

        type_declaration := annotation * ( typeref_decl | complex_type_decl)
    """
    annotations = parse_annotations(parser)
    type_class = parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    if type_class == "typeref":
        return parse_typeref_decl(parser, annotations)
    elif type_class == "derive":
        return parse_derivation(parser, annotations)
    elif type_class == "transformers":
        parse_transformers_decl(parser, annotations)
    else:
        return parse_complex_type_decl(parser, annotations)

def parse_typeref_decl(parser, annotations):
    """
    Parses typeref declaration of the form:

        "typeref" <name> "=" type_data
    """
    docstring = parser.last_docstring()
    parser.ensure_token(TokenType.IDENTIFIER, "typeref")
    name = parser.ensure_token(TokenType.IDENTIFIER)
    parser.ensure_token(TokenType.EQUALS)
    target_type = parse_any_type_decl(parser)

    # What should the type decl be here?
    name, namespace, fqn = utils.normalize_name_and_ns(name, parser.document.namespace)
    parser.register_type(fqn, target_type)
    return fqn

def parse_any_type_decl(parser, annotations = []):
    next_token = parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    if next_token == "array":
        return parse_array_type_decl(parser, annotations)
    elif next_token == "map":
        return parse_map_type_decl(parser, annotations)
    elif next_token in [ "record", "enum", "union" ]:
        return parse_complex_type_decl(parser, annotations)
    else:
        return parse_primitive_type(parser, annotations)

def parse_primitive_type(parser, annotations = []):
    parser.ensure_token(TokenType.IDENTIFIER, peek = True)
    fqn = parser.ensure_fqn()
    # if this type exists in the type registry use this type
    # otherwise register as an unresolved type and proceed
    return parser.get_type(fqn)

def parse_array_type_decl(parser, annotations = []):
    parser.ensure_token(TokenType.IDENTIFIER, "array")
    parser.ensure_token(TokenType.OPEN_SQUARE)
    target_type = parse_any_type_decl(parser)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    return tlcore.ListType(target_type, annotations = annotations, docs = parser.last_docstring())

def parse_map_type_decl(parser, annotations = []):
    parser.ensure_token(TokenType.IDENTIFIER, "map")
    parser.ensure_token(TokenType.OPEN_SQUARE)
    key_type = parse_any_type_decl(parser)
    parser.ensure_token(TokenType.COMMA)
    value_type = parse_any_type_decl(parser)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    return tlcore.MapType(key_type, value_type, annotations = annotations, docs = parser.last_docstring())

def parse_complex_type_decl(parser, annotations = []):
    type_class = parser.ensure_token(TokenType.IDENTIFIER)
    if type_class not in ["union", "enum", "record"]:
        raise UnexpectedTokenException(parser.peek_token(), "union", "enum", "record")

    newtype = fqn = None
    if parser.peeked_token_is(TokenType.IDENTIFIER):
        # we have a name
        n = parser.ensure_token(TokenType.IDENTIFIER)
        ns = parser.document.namespace
        n,ns,fqn = utils.normalize_name_and_ns(n, ns)

    if type_class == "enum":
        newtype = tlenums.EnumType(annotations = annotations, docs = parser.last_docstring())
        if fqn:
            newtype = parser.register_type(fqn, newtype)
            newtype.type_data.fqn = fqn
        parse_enum_body(parser, newtype)
    elif type_class == "union":
        newtype = tlcore.UnionType([], annotations = annotations, docs = parser.last_docstring())
        if fqn:
            newtype = parser.register_type(fqn, newtype)
        parse_union_body(parser, newtype)
    elif type_class == "record":
        newtype = records.RecordType(records.Record(fqn, None, None), annotations = annotations, docs = parser.last_docstring())
        record_data = newtype.type_data
        if fqn:
            newtype = parser.register_type(fqn, newtype)
            print "Parsing new record: '%s'" % fqn

        parse_record_body(parser, newtype)

        # Try for a resolution if we dont want lazy evaluation
        if not parser.lazy_resolution_enabled:
            newtype.resolve(parser.onering_context.type_registry, parser.resolver)
    else:
        assert False

    assert newtype is not None, "A type was NOT parsed"
    return newtype

########################################################################
##          Enum and Union parsing
########################################################################

def parse_enum_body(parser, enum_type):
    """
    Parse the body of an enum declaration:

        "{" enum_symbols + "}"
    """
    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        annotations = parse_annotations(parser)
        symbol = parser.ensure_token(TokenType.IDENTIFIER)
        enum_type.type_data.add_symbol(symbol, annotations, parser.last_docstring)
        # consume comma silently
        parser.next_token_if(TokenType.COMMA, consume = True)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    return enum_type

def parse_union_body(parser, union_type):
    """
    Parse the body of an union declaration:
        "{" any_type_decl + "}"
    """
    parser.ensure_token(TokenType.OPEN_SQUARE)
    while not parser.peeked_token_is(TokenType.CLOSE_SQUARE):
        child_type = parse_any_type_decl(parser)
        union_type.add_child(child_type)
        parser.next_token_if(TokenType.COMMA, consume = True)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    return union_type


########################################################################
##          Record and Field parsing
########################################################################

def parse_record_body(parser, parent_record):
    """
    Parses the body of a record declaration:

        record_type_body := "{" ( annotation * field_declaration ) * "}"

    """
    parser.ensure_token(TokenType.OPEN_BRACE)

    # read annotations as they can be used by ... or field projections
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        # read a field projection
        parse_field_declaration(parser, parent_record)

    parser.ensure_token(TokenType.CLOSE_BRACE)
    return parent_record

def parse_field_declaration(parser, parent_record):
    """
        field_declaration := annotations ? IDENTIFIER ":" type_decl "?" ? ( "=" literal_value ) ?
    """
    annotations = parse_annotations(parser)
    docstring = parser.last_docstring()
    field_name = parser.ensure_token(TokenType.IDENTIFIER)
    parser.ensure_token(TokenType.COLON)
    field_type = parse_any_type_decl(parser)
    is_optional = False
    default_value = None

    if parser.next_token_is(TokenType.QUESTION):
        is_optional = True

    if parser.next_token_is(TokenType.EQUALS):
        default_value = parser.ensure_literal_value()

    child_data = records.FieldData(field_name, parent_record, is_optional, default_value)
    parent_record.add_child(field_type, field_name, docstring, annotations, child_data)

########################################################################
##          Derivation and Projection Parsing
########################################################################
def parse_derivation(parser, annotations = []):
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

        derivation_header := ( ":" source_fqn ("as" IDENTIFIER) ? ( "," source_fqn ("as" IDENTIFIER) ) *
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

        derivation_body := "{" ( annotations ? field_projection ) * "}"
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
        elif parser.peeked_token_is(TokenType.STREAM):
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

    projections = []

    # There MUST be a type constructor
    type_constructor = parser.ensure_fqn()

    parser.ensure_token(TokenType.OPEN_SQUARE)

    while not parser.peeked_token_is(TokenType.CLOSE_SQUARE):
        # in a declaration within a type value of a type stream, we wont allow optionality
        # or default values as it just wont make sense.
        if parser.peeked_token_is(TokenType.OPEN_BRACE):
            # Inject a COLON so we can treat it as a projection target
            parser.unget_token(Token(TokenType.COLON, -1))
        ipdb.set_trace()
        projection = parse_projection(parser, parent_entity = parent_projection, allow_renaming = False,
                                      allow_optionality = False, allow_default_value = False)
        projections.append(projection)
        # Consume a comma silently 
        parser.next_token_if(TokenType.COMMA, consume = True)
    parser.ensure_token(TokenType.CLOSE_SQUARE)
    target_type = derivations.TypeStreamDeclaration(type_constructor, param_names, projections)
    projection_type = derivations.PROJECTION_TYPE_STREAMING
    return projection_type, target_type

########################################################################
##          Transformer Parsing Rules
########################################################################

def parse_transformers_decl(parser, annotations):
    """
    Parses transformer declarations

        transformers name<IDENT>    "{" transformer_decl * "}"
    """
    parser.ensure_token(TokenType.IDENTIFIER, "transformers")
    n = parser.ensure_token(TokenType.IDENTIFIER)
    ns = parser.document.namespace
    n,ns,fqn = utils.normalize_name_and_ns(n, ns)
    print "Parsing new transformer: '%s'" % fqn

    transformer_group = transformers.TransformerGroup(fqn, annotations = annotations, docs = parser.last_docstring())
    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        # read a transformer
        transformer = parse_transformer(parser, transformer_group)
        transformer_group.add_transformer(transformer)

    parser.onering_context.register_transformer_group(transformer_group)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    return transformer_group

def parse_transformer(parser, transformer_group):
    """
    Parses a single transformer declaration

        src_type_fqn<IDENT> "=> dest_type_fqn<IDENT> "{" transformer_rule * "}"
    """
    annotations = parse_annotations(parser)
    src_fqn = parser.ensure_fqn()
    parser.ensure_token(TokenType.STREAM)
    dest_fqn = parser.ensure_fqn()

    src_type = parser.get_type(src_fqn)
    dest_type = parser.get_type(dest_fqn)

    transformer = transformers.Transformer(fqn = None,
                                           src_type = src_type,
                                           dest_type = dest_type,
                                           group = transformer_group,
                                           annotations = annotations,
                                           docs = parser.last_docstring())

    parser.ensure_token(TokenType.OPEN_BRACE)
    while not parser.peeked_token_is(TokenType.CLOSE_BRACE):
        # read a transformer
        statement = parse_transformer_rule(parser)
        transformer.add(statement)
    parser.ensure_token(TokenType.CLOSE_BRACE)
    parser.consume_tokens(TokenType.SEMI_COLON)
    return transformer

def parse_transformer_rule(parser):
    """
    Parses a single transformer rule.

        transformer_rule := let_statment | stream_expr

        let_statement := "let" stream_expr

        stream_expr := expr ( => expr ) * => expr
    """
    annotations = parse_annotations(parser)

    if parser.next_token_is(TokenType.IDENTIFIER, "let"):
        stmt = parse_expression(parser)
        stmt.is_temporary = True
    else:
        stmt = parse_expression(parser)

    # An expression must have more than 1 expression
    if stmt.next is None:
        raise errors.OneringException("An exception stream must have more than one expression")

    # ensure last var IS a variable expression
    if not isinstance(stmt.last, transformers.VariableExpression):
        raise errors.OneringException("Final target of an expression MUST be a variable")

    parser.consume_tokens(TokenType.SEMI_COLON)
    return stmt

def parse_expression(parser):
    """
    Parse a function call expression or a literal.

        expr := literal
                list_expression
                dict_expression
                tuple_expression
                dot_delimited_field_path
                stream_expr
                func_fqn "(" ")"
                func_fqn "(" expr ( "," expr ) * ")"
    """
    out = None
    if parser.peeked_token_is(TokenType.NUMBER):
        out = transformers.LiteralExpression(parser.next_token())
    elif parser.peeked_token_is(TokenType.STRING):
        out = transformers.LiteralExpression(parser.next_token())
    elif parser.peeked_token_is(TokenType.OPEN_SQUARE):
        # Read a list
        out = parse_list_expression(parser)
    elif parser.peeked_token_is(TokenType.OPEN_BRACE):
        out = parse_struct_expression(parser)
    elif parser.peeked_token_is(TokenType.OPEN_PAREN):
        out = parse_tuple_expression(parser)
    elif parser.next_token_is(TokenType.DOLLAR):
        # then we MUST have an IDENTIFIER
        if parser.peeked_token_is(TokenType.NUMBER):
            source = parser.ensure_token(TokenType.NUMBER)
        else:
            source = parse_field_path(parser, allow_abs_path = False, allow_child_selection = False)
        out = transformers.VariableExpression(source, from_source = False)
    elif parser.peeked_token_is(TokenType.IDENTIFIER):
        # See if we have a function call or a var or a field path
        source = parse_field_path(parser, allow_abs_path = False, allow_child_selection = False)
        out = transformers.VariableExpression(source)

        func_args = []
        if parser.peeked_token_is(TokenType.OPEN_PAREN):
            # function expression, so ensure field path has only one entry
            if source.length > 1:
                raise errors.OneringException("Fieldpaths cannot be used as functions")

            # Treat the source as a function name that will be resolved later on
            source = source.get(0)
            parser.ensure_token(TokenType.OPEN_PAREN)
            while not parser.peeked_token_is(TokenType.CLOSE_PAREN):
                # read another expression
                expr = parse_expression(parser)
                func_args.append(expr)
                if parser.next_token_is(TokenType.COMMA):
                    # TODO: ensure next val is an IDENTIFIER or a literal value
                    # Right now lack of this check wont break anything but 
                    # will allow "," at the end which is a bit, well rough!
                    pass
            parser.ensure_token(TokenType.CLOSE_PAREN)
            out = transformers.FunctionExpression(source, func_args)
    else:
        raise UnexpectedTokenException(parser.peek_token(),
                                       TokenType.STRING, TokenType.NUMBER,
                                       TokenType.OPEN_BRACE, TokenType.OPEN_SQUARE,
                                       TokenType.LT)

    # if the next is a "=>" then start streaming!
    if parser.peeked_token_is(TokenType.STREAM):
        parser.ensure_token(TokenType.STREAM)
        out.next = parse_expression(parser)
    return out

def parse_tuple_expression(parser):
    parser.ensure_token(TokenType.OPEN_PAREN)
    exprs = []
    if not parser.next_token_is(TokenType.CLOSE_PAREN):
        expr = parse_expression(parser)
        exprs = [expr]
        while parser.next_token_is(TokenType.COMMA):
            expr = parse_expression(parser)
            exprs.append(expr)
        parser.ensure_token(TokenType.CLOSE_PAREN)
    return transformers.TupleExpression(exprs)

########################################################################
##          Annotation Parsing Rules
########################################################################

def parse_annotations(parser):
    """
    Parse a list of annotations
    """
    out = []
    while parser.peeked_token_is(TokenType.AT):
        out.append(parse_annotation(parser))
    return out

def parse_annotation(parser):
    """
    Parse an annotation:
        annotation :=   leaf_annotation     |
                        compound_annotation

        leaf_annotation := "@" FQN "=" ( NUMBER | STRING )
        compound_annotaiton := "@" FQN "(" parameters ")"
        parameter_expressions := FQN | FQN "=" ( NUMBER, STRING, FQN )
    """
    parser.ensure_token(TokenType.AT)
    fqn = parser.ensure_fqn()
    if parser.peeked_token_is(TokenType.EQUALS):
        return parse_leaf_annotation_body(parser, fqn)
    elif parser.peeked_token_is(TokenType.OPEN_PAREN):
        return parse_compound_annotation_body(parser, fqn)
    else:
        return tlannotations.Annotation(fqn)

def parse_leaf_annotation_body(parser, fqn):
    """
    Parses leaf annotations of the form:

        "=" value
    """
    parser.ensure_token(TokenType.EQUALS)
    value = parser.ensure_literal_value()
    return tlannotations.Annotation(fqn, value = value)

def parse_compound_annotation_body(parser, fqn):
    """
    Parses compound annotation body of the form:

        "(" ( param_spec ( "," param_spec ) * ) ? ")"
        param_spec := name ( "=" value ) ?
    """
    param_specs = []
    parser.ensure_token(TokenType.OPEN_PAREN)
    while parser.peeked_token_is(TokenType.IDENTIFIER):
        param_name = parser.ensure_fqn()
        param_value = None
        if parser.next_token_is(TokenType.EQUALS):
            param_value = parser.ensure_literal_value()
            param_specs.append((param_name, param_value))
        else:
            param_specs.append((None, param_name))

        if parser.next_token_is(TokenType.COMMA):
            parser.ensure_token(TokenType.IDENTIFIER, peek = True)

    parser.ensure_token(TokenType.CLOSE_PAREN)
    return tlannotations.Annotation(fqn, param_specs = param_specs)
