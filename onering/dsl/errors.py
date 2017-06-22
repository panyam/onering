
from onering.core.errors import *

class SourceException(OneringException):
    def __init__(self, line, col, msg):
        self.line = line
        self.column = col
        self.message = msg
        message = "Line %d:%d - %s" % (line, col, msg)
        super(SourceException, self).__init__(message)

class UnexpectedTokenException(SourceException):
    def __init__(self, found_token, *expected_tokens):
        message = "Token encountered '%s', " % found_token.value
        if len(expected_tokens) == 1:
            message += "Expected: %s" % expected_tokens[0]
        else:
            message += "Expected one of (%s)" % ", ".join(["'%s'" % str(tok) for tok in expected_tokens])
        super(UnexpectedTokenException, self).__init__(found_token.line, found_token.col, message)
