
class Document(object):
    """
    A Onering document that contains a bunch of imports followed by one or more type definitions.
    """
    def __init__(self):
        self.namespace = None
        self.imports = []
        self.declarations = {}

class TypeDeclaration(object):
    """
    A Onering type declaration.   Types could be records, enums, unions or others defined
    in the datatypes.
    """
    def __init__(self, name, docstring = "", annotations = []):
        self.name = name
        self.docstring = docstring
        self.annotations = annotations

class UnexpectedTokenException(Exception):
    def __init__(self, found_token, *expected_tokens):
        message = "Line %d:%d - Token encountered '%s', " % (found_token.line, found_token.col, found_token.value)
        if len(expected_tokens) == 1:
            message += "Expected: %s" % expected_tokens[0]
        else:
            message += "Expected one of (%s)" % ", ".join(["'%s'" % str(tok) for tok in expected_tokens])
        Exception.__init__(self, message)
