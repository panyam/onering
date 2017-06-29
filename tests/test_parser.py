
from onering.dsl.parser import Parser

def test_parse_annotation():
    content = "@hello("world")"
    parser = Parser(content, context)
