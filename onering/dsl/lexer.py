
import cStringIO
import ipdb
import os
import shlex
from enum import Enum

class TokenType(Enum):
    EOS                 = "<EOS>"

    IDENTIFIER          = "<IDENT>"
    STRING              = "<STR>"
    NUMBER              = "<NUM>"
    COMMENT             = "<COMMENT>"

    # Special chars/operators etc
    STREAM              = "=>"
    EQUALS              = "="
    COLON               = ":"
    SEMI_COLON          = ";"
    SLASH               = "/"
    QUESTION            = "?"
    DOT                 = "."
    HASH                = "#"
    AT                  = "@"
    COMMA               = ","
    OPEN_PAREN          = "("
    CLOSE_PAREN         = ")"
    OPEN_SQUARE         = "["
    CLOSE_SQUARE        = "]"
    OPEN_BRACE          = "{"
    CLOSE_BRACE         = "}"
    MINUS               = "-"
    STAR                = "*"
    DOTDOT              = ".."
    DOTDOTDOT           = "..."


class Token(object):
    def __init__(self, tok_type, position, length = None, value = None, line = 0, col = 0):
        self._position = position
        self._line = line
        self._col = col
        self.tok_type = tok_type
        if value is None:
            value = tok_type.value
        if length is None:
            length = len(value)
        self._length = length
        self.value = value
        # print "Returning Token: %s" % repr(self)

    @property
    def line(self):
        return self._line

    @property
    def col(self):
        return self._col

    @property
    def position(self):
        return self._position

    @property
    def length(self):
        return self._length

    @property
    def endpos(self):
        return self.position + self.length

    def __repr__(self):
        if self.value:
            return "<[%d-%d], Line: %d, Col: %d, %s - %s>" % (self.position, self.endpos, self.line, self.col, self.tok_type, self.value)
        else:
            return "<[%d-%d], Line: %d, Col: %d, %s>" % (self.position, self.endpos, self.line, self.col, self.tok_type)

class Lexer(object):
    """
    Tokenizers an input stream containing Onering records and returns the tokens.
    """
    def __init__(self, instream):
        if type(instream) in (str, unicode):
            instream = cStringIO.StringIO(instream)
        self.instream = instream
        self.next_pos = 0
        self.next_line = 1
        self.next_col  = 1
        self.buffer = ""
        self.end_reached = False
        self.comments_enabled = True

    def _ensure_buffer(self, size = 1):
        buff_len = len(self.buffer)
        if buff_len < size:
            if self.end_reached:
                return False
            num_bytes = size - buff_len
            readchars = self.instream.read(max(num_bytes, 64))
            self.buffer += readchars
            self.end_reached = len(readchars) < num_bytes
        return len(self.buffer) >= size

    def _read_buffer(self, size):
        """
        Reads upto size characters from the buffer.  If the buffer has less than size bytes
        in it, only those are returned.  It is upto the caller to call _ensure_buffer to 
        ensure there is enough data in the buffer.
        """
        out, self.buffer = self.buffer[:size], self.buffer[size:]
        return out

    def matches_symbol(self, symbol, peek = False):
        l = len(symbol)
        if not self._ensure_buffer(l):
            # Not enough data so it cant match
            return False
        for i,ch in enumerate(symbol):
            if self.buffer[i] != ch:
                return False
        if not peek:
            # consume it
            self.get_chars(l)
        return True

    def matches_func(self, func, peek = True):
        ch,_,_,_ = self.get_chars(peek = True)
        if not ch or not func(ch):
            return None
        if not peek:
            # matches so pop
            return self.get_chars()
        return True

    def get_chars(self, nchars = 1, peek = False):
        curr_col = self.next_col
        curr_pos = self.next_pos
        curr_line = self.next_line
        self._ensure_buffer(nchars)
        if peek:
            out = self.buffer[:nchars]
        else:
            out = self._read_buffer(nchars)
            for i,ch in enumerate(out):
                self.next_pos += 1
                self.next_col += 1
                if ch == "\n":
                    self.next_line += 1
                    self.next_col = 0
        return (out, curr_pos, curr_line, curr_col)

    def read_till(self, delim_str, include):
        """
        Reads and returns everything until the delimiter string is countered.  If include is true then the delimiter string is also included in the output.
        """
        out = ""
        while self.has_more:
            if self.matches_symbol("\\"):
                self.out += "\\"
                ch,_,_,_ = self.get_chars()
                out += ch
            elif not self.matches_symbol(delim_str):
                ch,_,_,_ = self.get_chars()
                out += ch
            else:
                if include:
                    out += delim_str
                return out
        raise Exception("EOF Reached.  Expected '%s'" % delim_str)
    
    @property
    def has_more(self):
        return self.buffer or not self.end_reached

    def __iter__(self):
        return self

    def next(self):
        while self.has_more:
            curr_pos, curr_line, curr_col = self.next_pos, self.next_line, self.next_col
            curr_tok_value = ""
            def make_token(toktype, value = None, length = None):
                return Token(toktype, curr_pos, value = value, line = curr_line, col = curr_col, length = length)

            if self.matches_symbol("["):
                return make_token(TokenType.OPEN_SQUARE)
            elif self.matches_symbol(']'):
                return make_token(TokenType.CLOSE_SQUARE)
            elif self.matches_symbol('{'):
                return make_token(TokenType.OPEN_BRACE)
            elif self.matches_symbol('}'):
                return make_token(TokenType.CLOSE_BRACE)
            elif self.matches_symbol('('):
                return make_token(TokenType.OPEN_PAREN)
            elif self.matches_symbol(')'):
                return make_token(TokenType.CLOSE_PAREN)
            elif self.matches_symbol(','):
                return make_token(TokenType.COMMA)
            elif self.matches_symbol('...'):
                return make_token(TokenType.DOTDOTDOT)
            elif self.matches_symbol('..'):
                return make_token(TokenType.DOTDOT)
            elif self.matches_symbol('.'):
                return make_token(TokenType.DOT)
            elif self.matches_symbol('?'):
                return make_token(TokenType.QUESTION)
            elif self.matches_symbol('@'):
                return make_token(TokenType.AT)
            elif self.matches_symbol('#'):
                # We have a parser directive
                curr_tok_value = self.read_till("\n", include = False)
                return make_token(TokenType.HASH, curr_tok_value)
            elif self.matches_symbol('=>'):
                return make_token(TokenType.STREAM)
            elif self.matches_symbol('='):
                return make_token(TokenType.EQUALS)
            elif self.matches_symbol(':'):
                return make_token(TokenType.COLON)
            elif self.matches_symbol(';'):
                return make_token(TokenType.SEMI_COLON)
            elif self.matches_symbol('-'):
                return make_token(TokenType.MINUS)
            elif self.matches_symbol('*'):
                return make_token(TokenType.STAR)
            elif self.matches_func(str.isdigit):
                while self.matches_func(str.isdigit):
                    nextch,_,_,_ = self.get_chars()
                    curr_tok_value += nextch
                return make_token(TokenType.NUMBER, curr_tok_value, len(curr_tok_value))
            elif self.matches_func(lambda x: x == "_" or x.isalpha()):
                while self.matches_func(lambda x: x == "_" or x.isalnum()):
                    nextch,_,_,_ = self.get_chars()
                    curr_tok_value += nextch
                return make_token(TokenType.IDENTIFIER, curr_tok_value)

            if self.comments_enabled:
                if self.matches_symbol("//"):
                    # SINGLE LINE COMMENT, read till end of line
                    curr_tok_value = "//" + self.read_till("\n", include = False)
                    return make_token(TokenType.COMMENT, curr_tok_value)
                elif self.matches_symbol("/*"):
                    # MULTI LINE COMMENT - read till the next "*/"
                    curr_tok_value = "/*" + self.read_till("*/", include = True)
                    return make_token(TokenType.COMMENT, curr_tok_value)

            if self.matches_symbol("/"):
                return make_token(TokenType.SLASH)
            elif self.matches_symbol("'"):
                curr_pos, curr_line, curr_col = self.next_pos, self.next_line, self.next_col
                curr_tok_value = self.read_till("'", include = False)
                return make_token(TokenType.STRING, curr_tok_value)
            elif self.matches_symbol('"'):
                curr_pos, curr_line, curr_col = self.next_pos, self.next_line, self.next_col
                curr_tok_value = self.read_till('"', include = False)
                return make_token(TokenType.STRING, curr_tok_value)
            elif self.matches_func(str.isspace, peek = False):
                # do nothing
                pass
            else:
                raise Exception("Line %d, Column %d: Invalid character encountered: '%s'" % (curr_line, curr_col, self.get_chars(peek = True)[0]))
        raise StopIteration 
