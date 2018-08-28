
from __future__ import absolute_import
from ipdb import set_trace
from onering import utils
from onering.dsl import errors
from onering.dsl.parser.rules.types import ensure_typeexpr
from onering.dsl.lexer import Token, TokenType
from onering.dsl.parser.rules.annotations import parse_annotations

########################################################################
##          Fun type and definition parsing rules
########################################################################

def parse_function(parser, is_external, annotations, **kwargs):
    """Parses a function declaration.

    function        :=  function_type function_body ? 
    function_type   :=  "fun" name<IDENT>   "(" input_params ")" ? ( ":" output_type )
    function_body   := "{" stream_statement * "}"
    """
    docs = parser.last_docstring()
    parser.ensure_token(TokenType.IDENTIFIER, "fun")

    from onering.dsl.parser.rules.types import parse_typefunc_preamble
    func_name, type_params, docs = parse_typefunc_preamble(parser, name_required = True)
    func_fqn = ".".join([parser.current_module.fqn, func_name])
    input_typeargs, output_typearg = parse_function_signature(parser)
    input_types, input_params = map(list, zip(*input_typeargs))
    output_type, output_param = output_typearg

    parent = parser.current_module if func_name else None
    fun_type = tccore.make_fun_type(None, input_types, output_type)
    fun_expr = None
    if not is_external:
        from onering.dsl.parser.rules.exprs import parse_expr
        fun_expr = parse_expr(parser)
    function = tccore.Fun(input_params, fun_expr, func_fqn, fun_type).set_annotations(annotations).set_docs(docs)
    function.return_param = output_param

    if type_params:
        function.fqn = None
        function = tccore.Quant(type_params, function, func_fqn).set_annotations(annotations).set_docs(docs)

    parser.add_entity(func_name, function)
    parser.onering_context.fgraph.register(function)
    return function

def parse_function_signature(parser, require_param_name = True):
    """Parses the type signature declaration in a function declaration:

        function_signature      ::  input_params ? ( ":" (output_typeexpr ( "as" varname<IDENT> ) ? ) ?

        input_type_signature    ::  "(" param_decls ? ")"

        param_decls             ::  param_decl ( "," param_decl ) *

        param_decl              ::  ( param_name<IDENT> ":" ) ?   // if param names are optional
                                        param_type

    Returns:
        Returns the input typeexpr list and the output typeexpr (both being optional)
    """

    # First read the input params
    input_params = []
    if parser.next_token_is(TokenType.OPEN_PAREN):
        while not parser.peeked_token_is(TokenType.CLOSE_PAREN):
            input_params.append(parse_param_declaration(parser, require_param_name))

            # Consume the COMMA
            if parser.next_token_is(TokenType.COMMA):
                pass
        parser.ensure_token(TokenType.CLOSE_PAREN)

    # Now read the output type (if any)
    output_typearg = None
    if parser.next_token_is(TokenType.ARROW):
        output_typeexpr = None
        output_varname = "dest"
        output_typeexpr = ensure_typeexpr(parser)
        if parser.next_token_is(TokenType.IDENTIFIER, "as"):
            output_varname = parser.ensure_token(TokenType.IDENTIFIER)
        output_typearg = tccore.Ref(output_typeexpr), output_varname
    return input_params, output_typearg 

def parse_param_declaration(parser, require_name = True):
    """
        param_declaration := annotations ?
                             ( name<IDENTIFIER> ":" ) ?
                             type_decl
                             "?" ?                      // Optionality
                             ( "=" literal_value ) ?
    """
    annotations = parse_annotations(parser)
    docstring = parser.last_docstring()

    param_name = None
    if require_name:
        param_name = parser.ensure_token(TokenType.IDENTIFIER)
        parser.ensure_token(TokenType.COLON)
    elif parser.peeked_token_is(TokenType.IDENTIFIER) and \
                parser.peeked_token_is(TokenType.COLON, offset = 1):
        param_name = parser.ensure_token(TokenType.IDENTIFIER)
        parser.ensure_token(TokenType.COLON)

    param_typeexpr  = ensure_typeexpr(parser)
    # if we declared an inline Type then dont refer to it directly but via a Var
    if param_typeexpr.fqn and not param_typeexpr.isa(tccore.Var) and not param_typeexpr.isa(tccore.AliasType):
        param_typeexpr = tccore.make_type_var(param_typeexpr.name)
    is_optional     = parser.next_token_is(TokenType.QMARK)
    default_value   = None
    if parser.next_token_is(TokenType.EQUALS):
        default_value = parser.ensure_literal_value()
    out = tccore.Ref(param_typeexpr, annotations, docstring)
    out.annotations.add(tccore.Annotation("typecube.field.is_optional", is_optional))
    out.annotations.add(tccore.Annotation("typecube.field.default_value", default_value))
    return out, param_name

########################################################################
##          Parsing of quantifier specialization rules.
########################################################################

def parse_quant_spec(parser, is_external, annotations, **kwargs):
    """Parses a function declaration.

    quant_spec  := func_fqn "<" type_param_values ">" "=" var_or_fun
    """
    assert not is_external, "Quantifier specializations cannot be external.  They *may* point to external functions."
    docs = parser.last_docstring()
    parser.ensure_token(TokenType.IDENTIFIER, "funi")

    func_fqn = parser.ensure_fqn()
    if "." not in func_fqn:
        func_fqn = ".".join([parser.current_module.fqn, func_fqn])
    type_values = []
    parser_ensure_token(parser.GENERIC_OPEN_TOKEN)
    while not parser.peeked_token_is(parser.GENERIC_CLOSE_TOKEN):
        type_values.append(ensure_typeexpr(parser))
        # Consume the COMMA
        if parser.next_token_is(TokenType.COMMA):
            pass
    parser_ensure_token(parser.GENERIC_CLOSE_TOKEN)
    parser_ensure_token(TokenType.EQUALS)
    expr = parser.parse_expr()

    quant = parser.global_module.get_parent(func_fqn)
    assert quant and quant.isa(tccore.Quant), "Specialization ONLY allowed for Quantifiers"
    quant.addcase((type_values, expr))
    return quant
