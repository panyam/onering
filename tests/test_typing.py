
from ipdb import set_trace
from onering.common import errors
from onering.typing.core import *
from onering.typing import checkers
from . import default_types as defaults

def test_basic_validation():
    checkers.type_check(defaults.Int, 50, None)
    checkers.type_check(defaults.String, "hello", None)
    checkers.type_check(defaults.Float, 50.5, None)

    try: checkers.type_check(defaults.Int, 50.5, None)
    except errors.ValidationError as ve: pass

    try: checkers.type_check(defaults.String, 50, None)
    except errors.ValidationError as ve: pass

def test_record_creation():
    Pair = RecordType()                         \
                .add(defaults.Int, "first")     \
                .add(defaults.String, "second")
    checkers.type_check(Pair, {'first': 1, 'second': '2'}, None)

def test_tuple_creation():
    MyTuple = TupleType()              \
                .add(defaults.Int)              \
                .add(defaults.Float)            \
                .add(defaults.String)
    checkers.type_check(MyTuple, (1, 2.4, "Hello"), None)

def test_array_checking():
    at = defaults.Array[defaults.Int]
    checkers.type_check(at, [1,2,3,4,5], None)
    try:
        checkers.type_check(at, [1,2,3,4,5.0], None)
        assert False
    except errors.ValidationError as ve:
        pass

def test_recursive_types():
    TL = TypeVar("ListNode")["T"]
    ListNode = RecordType(["T"]).add_multi(
                "T", "value",
                defaults.Ref[TL], "next")

    TL = TypeVar("TreeNode")["T"]
    TreeNode = RecordType(["T"]).add_multi(
                "T", "value",
                defaults.Ref[TL], "left",
                defaults.Ref[TL], "right")

def test_dict_checking():
    dt = defaults.Map[defaults.String, defaults.Int]
    checkers.type_check(dt, dict(a = 1, b = 2, c = 3), None)
    try:
        checkers.type_check(dt, dict(a = 1, b = 2, c = 3.0), None)
        assert False
    except errors.ValidationError as ve:
        pass

def test_typeapp_creation():
    # Pair<F,S> { first : F, second : S}
    Pair = RecordType(["F", "S"])       \
                    .add(TypeVar("F"), "first") \
                    .add(TypeVar("S"), "second")
    checkers.type_check(Pair[defaults.Int, defaults.String], {'first': 1, 'second': '2'}, None)

def test_typeapp_with_unbound_type():
    # Pair<F,S> { first : F, second : S}
    Pair = RecordType(["F", "S"])       \
                    .add(TypeVar("F"), "first") \
                    .add(TypeVar("S"), "second")
    try:
        checkers.type_check(Pair, {'first': 1, 'second': '2'}, None)
        assert False
    except errors.ValidationError as ve: pass

def test_typeapps_partial():
    TheType = NativeType(["A", "B", "C", "D", "E", "F"])
    t1 = TheType[defaults.Int]

def test_typeapps_dup_binding():
    try:
        TheType = NativeType(["A", "B", "C", "D", "E", "F"])
        TheType[defaults.Int].apply(A = defaults.Int)
        assert False
    except errors.ORException as ve: pass

def test_typeapps_applying_for_typevar():
    A = TypeVar("A")
    TheType = A[defaults.Int]
    assert TheType.root_type == A
    assert len(A.args) == 0
    assert len(TheType.unused_values) == 1 and TheType.unused_values[0] == defaults.Int
    assert len(TheType.param_values) == 0

def test_typeapps_too_many_bindings():
    TheType = NativeType(["A", "B", "C"])
    T1 = TheType[defaults.Int, defaults.String, defaults.Float]
    try:
        T1[defaults.Int]
        assert False
    except errors.ORException as ve: pass

def test_typeapps_key_binding_for_typevar():
    try:
        TheType = TypeVar("A")
        TypeApp(TheType).apply(A = defaults.Int)
        assert False
    except errors.ORException as ve: pass
