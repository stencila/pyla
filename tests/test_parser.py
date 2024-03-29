import typing

from stencila.schema.types import (
    ArrayValidator,
    BooleanValidator,
    CodeChunk,
    Function,
    IntegerValidator,
    NumberValidator,
    Parameter,
    StringValidator,
    TupleValidator,
    ValidatorTypes,
    Variable,
)

from stencila.pyla.parser import (
    CodeChunkParser,
    CodeChunkParseResult,
    annotation_name_to_validator,
)

ASSIGNMENT_CODE = """
# this code assigns variables
a = 5
b = 6
a = 7
c: int = 8
c = 9
c: int = 10
def test_func():
    d = 4
e = b'abc123'
"""

FUNCTION_CODE = """
# this code defines functions with various types of arguments
def basic():
    return 1
    
    
def standard_args(a, b, c):
    return 2
    
    
def variable_args(d, e, *args, **kwargs):
    return 3
    
    
def default_args(f = 1, g = 'foo'):
    return 4

    
def annotated_types(h: int, j: str = 'bar') -> bool:
    return True


def named_constants(t = True, f = False, n = None):
    return False


def function_defaults(v = somefunc()):
    return 0

def basic():  # don't add it twice
    return 2
"""

USES_CODE = """
# this code uses a lot of variables in different ways
a + b
d + e + f
g - h
i - j - k
l / m
n / o / p
q * r
s * t * u
v or w
x and y
z | aa
bb ^ cc
dd & ee
ff.gg
hh[ii]
jj.kk.ll
mm % nn
"""

OPEN_CODE = """
# this code has calls to open(), both in the main level and in defined functions

f = open('read1')  # no mode, assumed to be read

with open('read2', 'r')  as f:  # open with ContextManager and mode
    a = f.read()
    
open('write', 'w')  # is a write, don't include

open('readwrite', 'r+')  # read and write, include file 

open('unknownmode', r)  # variable mode, don't know what it is, skip

open(file='kwread')  # kwargs testing
open('kwread2', mode='r')
open(file='kwread3', mode='r')
open(file='kwread4', mode='r+')

open('kwwrite', mode='w')
open(file='kwwrite2', mode='w')
open(file=1, mode='w')  # should never happen but needed for full code coverage

open(v)  # don't know the actual file name since it's a variable, don't include
open(v.y)
open(v['y'])

def open_func():
    open('readinfunc')  # should traverse into function defs to find opens

"""

IMPORT_CODE = """
from abc import deff
from foo.bar import baz
import rex
"""

COLLECTIONS_CODE = """
# this code assigns collections with variables, so they must be in the 'uses' result

[a, b, c, {d: e, f: g, h: somefunc(i)}]
[j, k, {l: m, n: o[p][q]}, anotherfunc(r)]
(s, t, {u: v}, [w, x, lastfunc(y[z])])
{'foo': 'bar'}  # shouldn't be in 'uses'
"""

SLICES_CODE = """
# this code checks for parsing of different ways of slicing array to 'uses'

a[b]
a[c:d]
a[d:e:f]
"""

ALTERS_CODE = """
# this code alters properties/items on existing variables

g: SomeType = SomeType()
g.i = 10 # should not be moved to alters

a.b.c = '123'
a.d = '456'
c['d'][3] = 456
h[5][6] = 9

d[f] = 4
f.g = 5  # f should be moved to alters
"""

AUG_ASSIGNMENT_CODE = """
# augmented assignment is e.g. increment/decrement (a += 1  / b -= 1)
a += 1
b -= func_call(c)
d[f] += 1
g.h -= 10
"""

CONDITIONAL_CODE = """
# test out ifs and while

if a > b:
    c = 1
elif d < e < f:
    g = 2
else:
    h = 3
    
while i:
    j = 4
else:
    k = 5
    
# test pass statement
if True:
    pass
"""

FOR_CODE = """
for a in range(10):
    print("{}".format(d))
    break
else:
    print(e)
    
for b in range(10):
    continue
"""

EXCEPT_CODE = """
try:
    a = 3
except ValueError as f:
    b = 4
except:
    c = 5
else:
    d = 6
finally:
    e = 7
"""


def parse_code(code: str) -> CodeChunkParseResult:
    return CodeChunkParser().parse(CodeChunk(code))


def check_result_fields_empty(
    result: CodeChunkParseResult, non_empty_fields: typing.List[str]
) -> None:
    for name, value in result.to_dict().items():
        if name in non_empty_fields:
            continue
        if isinstance(value, list):
            assert len(value) == 0, "{} is not empty".format(name)


def check_parameter(
    p: Parameter,
    name: str,
    isRequired: bool,
    default: typing.Any,
    validator: typing.Optional[typing.Type[ValidatorTypes]],
) -> None:
    assert p.name == name
    assert p.isRequired == isRequired
    assert p.default == default
    if validator is not None:
        assert isinstance(p.validator, validator)


def test_variable_parsing() -> None:
    """
    Test that assignments without annotations are extracted into `assigns` and assignments with are to `declares.`

    Also test that:
     - function definitions are recorded as declarations (basic test just to have a function body to parse, actual
        function parsing tests are in test_function_def_parsing)
     - variables that are reassigned are only recorded once
     - assignment/declarations in function definitions are not recorded
    """
    parse_result = parse_code(ASSIGNMENT_CODE)

    assert len(parse_result.declares) == 2
    assert type(parse_result.declares[0]) == Variable
    assert parse_result.declares[0].name == "c"
    assert type(parse_result.declares[0].validator) == IntegerValidator

    assert (
        type(parse_result.declares[1]) == Function
    )  # The correctness of parsing the function is tested elsewhere

    assert parse_result.assigns == ["a", "b", "e"]

    check_result_fields_empty(parse_result, ["declares", "assigns"])


def test_function_def_parsing():
    parse_result = parse_code(FUNCTION_CODE)

    (
        basic,
        standard_args,
        variable_args,
        default_args,
        annotated_types,
        named_constants,
        function_defaults,
    ) = parse_result.declares

    for fn in parse_result.declares:
        assert isinstance(fn, Function)
        if fn != annotated_types:
            assert fn.returns is None

    assert basic.name == "basic"
    assert len(basic.parameters) == 0

    assert standard_args.name == "standard_args"
    assert len(standard_args.parameters) == 3
    check_parameter(standard_args.parameters[0], "a", True, None, None)
    check_parameter(standard_args.parameters[1], "b", True, None, None)
    check_parameter(standard_args.parameters[2], "c", True, None, None)

    assert variable_args.name == "variable_args"
    assert len(variable_args.parameters) == 4
    check_parameter(variable_args.parameters[0], "d", True, None, None)
    check_parameter(variable_args.parameters[1], "e", True, None, None)

    check_parameter(variable_args.parameters[2], "args", False, None, None)
    assert variable_args.parameters[2].isVariadic is True
    assert not variable_args.parameters[2].isExtensible

    check_parameter(variable_args.parameters[3], "kwargs", False, None, None)
    assert not variable_args.parameters[3].isVariadic
    assert variable_args.parameters[3].isExtensible is True

    assert default_args.name == "default_args"
    assert len(default_args.parameters) == 2
    check_parameter(default_args.parameters[0], "f", False, 1, None)
    check_parameter(default_args.parameters[1], "g", False, "foo", None)

    assert annotated_types.name == "annotated_types"
    assert len(annotated_types.parameters) == 2
    assert isinstance(annotated_types.returns, BooleanValidator)
    check_parameter(annotated_types.parameters[0], "h", True, None, IntegerValidator)
    check_parameter(annotated_types.parameters[1], "j", False, "bar", StringValidator)

    assert named_constants.name == "named_constants"
    assert len(named_constants.parameters) == 3
    check_parameter(named_constants.parameters[0], "t", False, True, None)
    check_parameter(named_constants.parameters[1], "f", False, False, None)
    check_parameter(named_constants.parameters[2], "n", False, None, None)

    assert function_defaults.name == "function_defaults"
    assert len(function_defaults.parameters) == 1
    check_parameter(function_defaults.parameters[0], "v", False, None, None)

    check_result_fields_empty(parse_result, ["declares"])


def test_uses_parsing():
    parse_result = parse_code(USES_CODE)

    check_result_fields_empty(parse_result, ["uses"])

    uses = [
        "a",
        "b",
        "d",
        "e",
        "f",
        "g",
        "h",
        "i",
        "j",
        "k",
        "l",
        "m",
        "n",
        "o",
        "p",
        "q",
        "r",
        "s",
        "t",
        "u",
        "v",
        "w",
        "x",
        "y",
        "z",
        "aa",
        "bb",
        "cc",
        "dd",
        "ee",
        "ff",
        "hh",
        "ii",
        "jj",
        "mm",
        "nn",
    ]

    assert sorted(uses) == sorted(parse_result.uses)


def test_parsing_error():
    parse_result = parse_code("this is invalid python++ code")

    assert parse_result.error.errorType == "SyntaxError"
    assert parse_result.error.errorMessage == "invalid syntax (<unknown>, line 1)"


def test_reads_parsing():
    c = CodeChunk(OPEN_CODE)
    ccp = CodeChunkParser()
    parse_result = ccp.parse(c)

    filenames = [
        "read1",
        "read2",
        "readwrite",
        "kwread",
        "kwread2",
        "kwread3",
        "kwread4",
        "readinfunc",
    ]

    assert sorted(filenames) == sorted(parse_result.reads)


def test_imports_parsing():
    parse_result = parse_code(IMPORT_CODE)

    assert ["abc", "foo.bar", "rex"] == sorted(parse_result.imports)

    check_result_fields_empty(parse_result, ["imports"])


def test_collections_parsing():
    parse_result = parse_code(COLLECTIONS_CODE)

    assert [chr(c) for c in range(ord("a"), ord("z") + 1)] == sorted(parse_result.uses)

    check_result_fields_empty(parse_result, ["uses"])


def test_slices_parsing():
    parse_result = parse_code(SLICES_CODE)

    assert [chr(c) for c in range(ord("a"), ord("f") + 1)] == sorted(parse_result.uses)

    check_result_fields_empty(parse_result, ["uses"])


def test_alters_parsing():
    parse_result = parse_code(ALTERS_CODE)

    assert ["a", "c", "d", "f", "h"] == sorted(parse_result.alters)

    assert len(parse_result.declares) == 1
    assert parse_result.declares[0].name == "g"

    check_result_fields_empty(parse_result, ["alters", "declares"])


def test_aug_assignment_parsing():
    parse_result = parse_code(AUG_ASSIGNMENT_CODE)

    assert ["a", "b", "d", "g"] == sorted(parse_result.alters)
    assert ["c", "f"] == sorted(parse_result.uses)

    check_result_fields_empty(parse_result, ["alters", "uses"])


def test_conditional_code_parsing():
    parse_result = parse_code(CONDITIONAL_CODE)

    assert ["a", "b", "d", "e", "f", "i"] == sorted(parse_result.uses)
    assert ["c", "g", "h", "j", "k"] == sorted(parse_result.assigns)

    check_result_fields_empty(parse_result, ["assigns", "uses"])


def test_for_parsing():
    parse_result = parse_code(FOR_CODE)

    assert ["a", "b"] == parse_result.assigns
    assert ["d", "e"] == sorted(parse_result.uses)

    check_result_fields_empty(parse_result, ["assigns", "uses"])


def test_except_parsing():
    parse_result = parse_code(EXCEPT_CODE)
    assert ["a", "b", "c", "d", "e"] == sorted(parse_result.assigns)

    check_result_fields_empty(parse_result, ["assigns"])


def test_annotation_parsing():
    assert annotation_name_to_validator(None) is None
    assert isinstance(annotation_name_to_validator("bool"), BooleanValidator)
    assert isinstance(annotation_name_to_validator("str"), StringValidator)
    assert isinstance(annotation_name_to_validator("int"), IntegerValidator)
    assert isinstance(annotation_name_to_validator("float"), NumberValidator)
    assert isinstance(annotation_name_to_validator("list"), ArrayValidator)
    assert isinstance(annotation_name_to_validator("tuple"), TupleValidator)


def test_lambda_parsing():
    # a basic lambda
    lambda_code = """d = lambda x: x * e"""
    parse_result = parse_code(lambda_code)
    assert ["e"] == parse_result.uses
    assert ["d"] == parse_result.assigns

    check_result_fields_empty(parse_result, ["uses", "assigns"])


def test_comprehension_parsing():
    list_comprehension_code = """
# list comprehension
a = [lambda b, c: b * c * f * g for d, e in some_array if d > h]
i = [j for j in some_other_array]
"""

    dict_comprehension_code = (
        """a = {b: lambda c: c * d for b in some_other_array if d < e}"""
    )

    parse_result = parse_code(list_comprehension_code)
    assert ["a", "i"] == sorted(parse_result.assigns)
    assert ["f", "g", "h", "some_array", "some_other_array"] == sorted(
        parse_result.uses
    )
    check_result_fields_empty(parse_result, ["uses", "assigns"])

    parse_result = parse_code(dict_comprehension_code)
    assert ["a"] == parse_result.assigns
    assert ["d", "e", "some_other_array"] == sorted(parse_result.uses)
    check_result_fields_empty(parse_result, ["uses", "assigns"])

    set_comprehension_code = """a = {b for b in final_array if b > c}"""
    parse_result = parse_code(set_comprehension_code)
    assert ["a"] == parse_result.assigns
    assert ["c", "final_array"] == sorted(parse_result.uses)
    check_result_fields_empty(parse_result, ["uses", "assigns"])


def test_unary_op():
    parse_result = parse_code("x = not y")
    assert ["x"] == parse_result.assigns
    assert ["y"] == parse_result.uses
    check_result_fields_empty(parse_result, ["uses", "assigns"])

    parse_result = parse_code("x = not (a or b)")
    assert ["x"] == parse_result.assigns
    assert ["a", "b"] == sorted(parse_result.uses)
    check_result_fields_empty(parse_result, ["uses", "assigns"])
