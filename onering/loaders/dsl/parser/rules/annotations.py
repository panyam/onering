from __future__ import absolute_import
from onering.dsl.lexer import Token, TokenType

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
    return tlannotations.Annotations(out)

def parse_annotation(parser):
    """
    Parse an annotation:
        annotation :=   leaf_annotation     |
                        compound_annotation

        leaf_annotation := "@" FQN "=" ( NUMBER | STRING )
        compound_annotaiton := "@" FQN "(" parameters ")"
        parameter_exprs := FQN | FQN "=" ( NUMBER, STRING, FQN )
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

        compound_annotation_body := "(" ( param_spec ( "," param_spec ) * ) ? ")"
                                 |  "(" expression ")"

        param_spec := name ( "=" expression ) ?
    """
    param_specs = []
    parser.ensure_token(TokenType.OPEN_PAREN)
    if parser.peeked_token_is(TokenType.IDENTIFIER):
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
        out = tlannotations.Annotation(fqn, param_specs = param_specs)
    elif not parser.peeked_token_is(TokenType.CLOSE_PAREN):
        out = tlannotations.Annotation(fqn, value = parser.ensure_literal_value())

    parser.ensure_token(TokenType.CLOSE_PAREN)
    return out
