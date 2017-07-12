
from ipdb import set_trace
from typecube import core as tlcore
from typecube.ext import IntType, StringType, Literal
from onering.dsl.parser import Parser
from onering.core.context import OneringContext
from onering.dsl.parser.rules.annotations import parse_annotation
from onering.dsl.parser.rules.modules import parse_module

def new_parser(content, context = None):
    if context is None:
        context = OneringContext()
    return Parser(content, context)

def test_parse_annotation_leaf():
    # Test leaf annotations
    content = """@hello("world")"""
    annotation = parse_annotation(new_parser(content))
    assert annotation.name == "hello"
    assert type(annotation.value) is Literal
    assert annotation.value.value == "world"

def test_parse_annotation_compound():
    # Test compound annotations
    content = """ @name(one = 1, two = 2, three = "three") """
    annotation = parse_annotation(new_parser(content))
    assert annotation.name == "name"
    assert issubclass(annotation.value.__class__, dict)
    assert annotation.has_params
    assert len(annotation.params) == 3
    assert annotation.params["one"].equals(Literal(1, IntType))
    assert annotation.params["two"].equals(Literal(2, IntType))
    assert annotation.params["three"].equals(Literal("three", StringType))

def test_parse_annotation_no_duplicates():
    content = """ @name(one = 1, one = 2) """
    try:
        annotation = parse_annotation(new_parser(content))
        assert False, "Should have failed on duplication"
    except:
        pass


def test_module_parsing():
    content = """
    module a.b {
    }
    """

    parser = new_parser(content)
    context = parser.onering_context
    module = parse_module(parser, None)
    assert module.fqn == "a.b"
    assert context.global_module.get("a.b") == module

def test_module_parsing_multi():
    content = """
    module a.b { }
    module c.d { }
    """

    parser = new_parser(content)
    context = parser.onering_context
    module = parse_module(parser, None)
    assert module.fqn == "a.b"
    assert context.global_module.get("a.b") == module

    module = parse_module(parser, None)
    assert module.fqn == "c.d"
    assert context.global_module.get("c.d") == module

def test_enum_parsing():
    content = """
    enum test {
        a = 1
        b = 1
    }
    """

    parser = new_parser(content)
    context = parser.onering_context
    parser.parse()
    entity = context.global_module.get("test")
    assert entity.constructor == "enum"
    assert entity.args[0].name == "a"
    assert entity.args[1].name == "b"

def test_record_parsing():
    content = """
    record Record {
        a : int

        b : string

        c : record {
            x : int
            y : bool
        }
    }
    """

    parser = new_parser(content)
    context = parser.onering_context
    parser.parse()
    entity = context.global_module.get("Record")
    assert entity.constructor == "record"
    assert entity.name == "Record"
    assert entity.args[0].name == "a"
    assert entity.args[1].name == "b"
    assert entity.args[2].name == "c"
    assert entity.args[2].type_expr.constructor == "record"
    assert entity.args[2].type_expr.name == None

