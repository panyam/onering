import ipdb
from lexer import Token, TokenType
from core import UnexpectedTokenException

class TokenStream(object):
    """
    A token stream is a wrapper over a lexer that provides some nice capabilities like buffering, 
    lookahead, ungetting etc.
    """
    def __init__(self, lexer):
        self.peeked_tokens = []
        self.lexer = lexer

    def unget_token(self, token):
        self.peeked_tokens.append(token)

    def peek_token(self):
        return self.next_token(True)

    def next_token(self, peek = False):
        try:
            if not self.peeked_tokens:
                self.peeked_tokens.append(self.lexer.next())
            out = self.peeked_tokens[-1]
            if not peek:
                self.peeked_tokens.pop()
            return out
        except StopIteration, si:
            # we are done
            return Token(TokenType.EOS, -1)

    def next_token_if(self, tok_type, tok_value = None, consume = False, ignore_comment = True):
        """
        Returns the next token if it matches a particular type and value otherwise returns None.
        """
        next_tok = self.peek_token()
        while next_tok.tok_type in (TokenType.COMMENT, TokenType.HASH):
            # Save the last docstring encountered as it can
            # be used as a docstring for the next entity that
            # needs it.
            if next_tok.tok_type == TokenType.COMMENT:
                self._last_docstring = next_tok.value
                if ignore_comment:
                    self.next_token()
                    next_tok = self.peek_token()
                else:
                    # dont ignore comment so break out to be treated
                    # as a real token
                    break
            else:
                self.process_directive(next_tok.value)
                self.next_token()
                next_tok = self.peek_token()

        if next_tok.tok_type != tok_type:
            return None

        if tok_value is not None and next_tok.value != tok_value:
            return None

        if consume:
            self.next_token()
        return next_tok

    def peeked_token_is(self, tok_type, tok_value = None, ignore_comment = True):
        """
        Returns true (WITHOUT consuming the token) if the next token matches the given token type and the 
        value if it is specified.
        """
        next_tok = self.next_token_if(tok_type, tok_value, False, ignore_comment)
        return next_tok is not None

    def next_token_is(self, tok_type, tok_value = None, ignore_comment = True):
        """
        Returns true (and consumes the token) if the next token matches the given token type and the 
        value if it is specified.
        """
        next_tok = self.next_token_if(tok_type, tok_value, True, ignore_comment)
        return next_tok is not None

    def ensure_token(self, tok_type, tok_value = None, peek = False):
        """
        If the next token is not of the given type an exception is raised
        otherwise the token's value is returned.  Note that a token's value
        can be None and this is still valid.
        """
        if not self.peeked_token_is(tok_type, tok_value):
            raise UnexpectedTokenException(self.peek_token(), tok_type)
        if peek:
            return self.peek_token().value
        else:
            return self.next_token().value

    def consume_tokens(self,tok_type):
        """
        Silently consume and ignore a list of tokens of the given type.
        """
        while self.next_token_if(tok_type, consume = True) is not None: pass
