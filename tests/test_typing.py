
from ipdb import set_trace
from typecube.core import *
from typecube import defaults
from typecube import checkers
from typecube import errors

def test_basic_validation():
    checkers.type_check(defaults.Int, 50)
    checkers.type_check(defaults.String, "hello")
    checkers.type_check(defaults.Float, 50.5)

    try: checkers.type_check(defaults.Int, 50.5)
    except errors.ValidationError as ve: pass

    try: checkers.type_check(defaults.String, 50)
    except errors.ValidationError as ve: pass

def test_record_creation():
    Pair = RecordType("Pair")                   \
                .add(defaults.Int, "first")     \
                .add(defaults.String, "second")
    checkers.type_check(Pair, {'first': 1, 'second': '2'})

def test_tuple_creation():
    MyTuple = TupleType("MyTuple")              \
                .add(defaults.Int)              \
                .add(defaults.Float)            \
                .add(defaults.String)
    checkers.type_check(MyTuple, (1, 2.4, "Hello"))

def test_array_checking():
    at = defaults.Array[defaults.Int]
    checkers.type_check(at, [1,2,3,4,5])
    try:
        checkers.type_check(at, [1,2,3,4,5.0])
        assert False
    except errors.ValidationError as ve:
        pass

def test_dict_checking():
    dt = defaults.Map[defaults.String, defaults.Int]
    checkers.type_check(dt, dict(a = 1, b = 2, c = 3))
    try:
        checkers.type_check(dt, dict(a = 1, b = 2, c = 3.0))
        assert False
    except errors.ValidationError as ve:
        pass

def test_typeapp_creation():
    # Pair<F,S> { first : F, second : S}
    Pair = RecordType("Pair", ["F", "S"])       \
                    .add(TypeVar("F"), "first") \
                    .add(TypeVar("S"), "second")
    checkers.type_check(Pair[defaults.Int, defaults.String], {'first': 1, 'second': '2'})

def test_typeapp_with_unbound_type():
    # Pair<F,S> { first : F, second : S}
    Pair = RecordType("Pair", ["F", "S"])       \
                    .add(TypeVar("F"), "first") \
                    .add(TypeVar("S"), "second")
    try:
        checkers.type_check(Pair, {'first': 1, 'second': '2'})
        assert False
    except errors.ValidationError as ve: pass

def test_record_to_object():
    """ Here we want to create "native" classes out of Types so we can do something
    useful with instances of these types.

    Some examples are taking a type and use an instance of it in a function, 
    serialize it to some representation, deserialize some representation to
    an instance of the type.
    """
    pass
