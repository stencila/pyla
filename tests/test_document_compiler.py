import typing

from stencila.schema.json import dict_decode
from stencila.schema.types import Article, CodeChunk, CodeExpression, Parameter

from stencila.pyla.interpreter import DocumentCompiler
from stencila.pyla.parser import CodeChunkExecution


def test_compile_article():
    chunk_1_text = "a = 4"
    chunk_2_text = "invalid python code"
    chunk_3_text = "def somefunc(bad_param):\n    return bad_param"

    expr_1_text = "a * parameter_one"
    expr_2_text = "more invalid python code"

    article = dict_decode(
        {
            "type": "Article",
            "title": "Upcoming Temperatures",
            "authors": [],
            "content": [
                {
                    "type": "Parameter",
                    "name": "parameter_one",
                    "validator": {"type": "IntegerValidator"},
                },
                {"type": "Heading", "depth": 1, "content": ["A Heading"]},
                {
                    "type": "CodeChunk",
                    "text": "let a = 'I am JavaScript!'",
                    "programmingLanguage": "notpython",
                },
                {
                    "type": "CodeChunk",
                    "text": chunk_1_text,
                    "programmingLanguage": "python",
                },
                {
                    "type": "CodeChunk",
                    "text": chunk_2_text,
                    "programmingLanguage": "python",
                },
                {
                    "type": "CodeChunk",
                    "text": chunk_3_text,
                    "programmingLanguage": "python",
                    "declares": [
                        {
                            "type": "Function",
                            "name": "somefunc",
                            "parameters": [
                                {
                                    "type": "Parameter",
                                    "name": "bad_param",
                                    "isRequired": True,
                                }
                            ],
                        }
                    ],
                },
                {
                    "type": "CodeExpression",
                    "text": "invalid code",
                    "programmingLanguage": "notpython",
                },
                {
                    "type": "CodeExpression",
                    "text": expr_1_text,
                    "programmingLanguage": "python",
                },
                {
                    "type": "CodeExpression",
                    "text": expr_2_text,
                    "programmingLanguage": "python",
                },
            ],
        }
    )

    article = typing.cast(Article, article)

    dc = DocumentCompiler()
    dcr = dc.compile(article)
    assert len(dcr.parameters) == 1
    assert isinstance(dcr.parameters[0], Parameter)
    assert dcr.parameters[0].name == "parameter_one"

    assert len(dcr.code) == 5

    for c in dcr.code:
        if isinstance(c, CodeChunkExecution):
            c = c[0]
        assert c.programmingLanguage == "python"

    code_chunks = list(
        map(
            lambda c: c[0],
            filter(lambda ce: isinstance(ce, CodeChunkExecution), dcr.code),
        )
    )
    code_exprs = list(filter(lambda ce: isinstance(ce, CodeExpression), dcr.code))

    assert code_chunks[0].text == chunk_1_text
    assert code_chunks[1].text == chunk_2_text
    assert code_chunks[2].text == chunk_3_text

    assert code_exprs[0].text == expr_1_text
    assert code_exprs[1].text == expr_2_text


def test_import_appending():
    """
    Found imports in a piece of code should be added to the list of imports the code chunk already specifies.
    """
    c = CodeChunk(
        "import moda\nimport modb\nimport modc",
        imports=["modc", "modd"],
        programmingLanguage="python",
    )

    dc = DocumentCompiler()
    dc.compile(c)

    assert len(c.imports) == 4
    assert "moda" in c.imports
    assert "modb" in c.imports
    assert "modc" in c.imports
    assert "modd" in c.imports


def test_import_with_semaphore():
    """
    If a `CodeChunk`'s imports has an empty string element then no imports should be added to its list.
    """
    c = CodeChunk(
        "import moda\nimport modb",
        imports=["modc", "modd", ""],
        programmingLanguage="python",
    )

    dc = DocumentCompiler()
    dc.compile(c)

    assert len(c.imports) == 3
    assert "moda" not in c.imports
    assert "modb" not in c.imports
    assert "modc" in c.imports
    assert "modd" in c.imports
    assert "" in c.imports
