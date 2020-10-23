import json
from io import BytesIO
from unittest import mock

import pytest
from stencila.schema.types import CodeChunk, CodeExpression

from stencila.pyla.interpreter import Interpreter
from stencila.pyla.servers import (
    JsonRpcErrorCode,
    StreamServer,
    encode_int,
    message_read,
    message_write,
    read_one,
)


def test_read_message():
    """Test that a message written to a stream is read correctly by the server."""
    input_str = BytesIO()
    output_str = BytesIO()
    server = StreamServer(Interpreter(), input_str, output_str)

    message_write(input_str, "Hello server, my old friend")
    input_str.seek(0)

    assert next(server.read_message()) == "Hello server, my old friend"


def test_write_message():
    """Test that a message that the server writes to a stream can be read back out."""
    input_str = BytesIO()
    output_str = BytesIO()
    server = StreamServer(Interpreter(), input_str, output_str)

    server.write_message("I've come to .send() to you again")

    output_str.seek(0)

    assert message_read(output_str) == "I've come to .send() to you again"


def test_lps_encoding():
    """Test various numbers are encoding by the `encode_int` function correctly."""
    for encoded, raw in (
        (b"\x01", 1),
        (b"\x80\x02", 256),
        (b"\x80\x08", 1024),
        (b"\x80\x80\x04", 65536),
    ):
        assert encoded == encode_int(raw)


def test_eof_read():
    """Test that EOFError is raised at the end of the stream read."""
    stream = BytesIO()
    with pytest.raises(EOFError):
        read_one(stream)


def test_receive_message_manifest():
    """Test receiving a manifest message."""
    server = StreamServer(Interpreter(), BytesIO(), BytesIO())
    response = server.receive_message(json.dumps({"id": 10, "method": "manifest",}))
    decoded = json.loads(response)
    assert decoded == {
        "jsonrpc": "2.0",
        "id": 10,
        "result": Interpreter.MANIFEST,
        "error": None,
    }


def test_receive_message_execute():
    """Test receiving an execute method, the execute method of the interpreter should be called with the node."""
    interpreter = Interpreter()
    interpreter.execute = mock.MagicMock(name="execute", return_value="executed-code")

    server = StreamServer(interpreter, BytesIO(), BytesIO())
    response = server.receive_message(
        json.dumps({"id": 11, "method": "execute", "params": {"node": "code-node"}})
    )
    decoded = json.loads(response)
    assert decoded == {
        "jsonrpc": "2.0",
        "id": 11,
        "result": "executed-code",
        "error": None,
    }
    interpreter.execute.assert_called_with("code-node")


def test_receive_message_execute_without_node():
    """Test that JsonRpcError with code JsonRpcErrorCode.InvalidParams is returned if node is missing/None"""
    server = StreamServer(Interpreter(), BytesIO(), BytesIO())
    response = server.receive_message(
        json.dumps({"id": 12, "method": "execute", "params": {}})
    )
    decoded = json.loads(response)
    assert decoded == {
        "jsonrpc": "2.0",
        "id": 12,
        "result": None,
        "error": {
            "code": JsonRpcErrorCode.InvalidParams.value,
            "message": 'Invalid params: "node" is missing',
            "data": None,
        },
    }


def test_receive_message_with_invalid_json():
    """Test that a JsonRpcError with code JsonRpcErrorCode.ParseError is returned if JSON is not valid."""
    server = StreamServer(Interpreter(), BytesIO(), BytesIO())
    response = server.receive_message("not a valid json")
    decoded = json.loads(response)
    assert decoded == {
        "jsonrpc": "2.0",
        "id": None,
        "result": None,
        "error": {
            "code": JsonRpcErrorCode.ParseError.value,
            "message": "Parse error: Expecting value: line 1 column 1 (char 0)",
            "data": None,
        },
    }


def test_receive_message_with_unknown_method():
    """Test that a JsonRpcError with code JsonRpcErrorCode.MethodNotFound is returned if method is not valid."""
    server = StreamServer(Interpreter(), BytesIO(), BytesIO())
    response = server.receive_message(
        json.dumps({"id": 13, "method": "not-real", "params": {}})
    )
    decoded = json.loads(response)
    assert decoded == {
        "jsonrpc": "2.0",
        "id": 13,
        "result": None,
        "error": {
            "code": JsonRpcErrorCode.MethodNotFound.value,
            "message": "Method not found: not-real",
            "data": None,
        },
    }


def test_receive_message_with_capability_error():
    """Test that a JsonRpcError with code JsonRpcErrorCode.CapabilityError is returned when not capable."""
    server = StreamServer(Interpreter(), BytesIO(), BytesIO())
    response = server.receive_message(
        json.dumps(
            {
                "id": 13,
                "method": "compile",
                "params": {
                    "node": {
                        "type": "CodeChunk",
                        "programmingLanguage": "foo",
                        "text": "bar",
                    }
                },
            }
        )
    )
    decoded = json.loads(response)
    assert decoded["error"]["code"] == JsonRpcErrorCode.CapabilityError.value
    assert decoded["error"]["message"].startswith(
        'Capability error: Incapable of method "compile"'
    )


def test_receive_message_with_internal_server_error():
    """Test that a JsonRpcError with code JsonRpcErrorCode.ServerError if some other exception occurs"""
    interpreter = Interpreter()
    interpreter.execute = mock.MagicMock(
        name="execute", side_effect=ValueError("test exception")
    )
    server = StreamServer(interpreter, BytesIO(), BytesIO())
    response = server.receive_message(
        json.dumps({"id": 13, "method": "execute", "params": {"node": "code-node"}})
    )
    decoded = json.loads(response)
    assert decoded == {
        "jsonrpc": "2.0",
        "id": 13,
        "result": None,
        "error": {
            "code": JsonRpcErrorCode.ServerError.value,
            "message": "Internal error: test exception",
            "data": None,
        },
    }


@mock.patch("stencila.pyla.servers.dict_decode", name="dict_decode")
def test_execute_code_chunk(dict_decode):
    """Test execution of a CodeChunk (with some mocks)"""
    interpreter = mock.MagicMock(spec=Interpreter, name="interpreter")
    server = StreamServer(interpreter, BytesIO(), BytesIO())
    cc = CodeChunk("1+1")
    dict_decode.return_value = cc
    server.receive_message(
        json.dumps({"id": 13, "method": "execute", "params": {"node": "cc"}})
    )
    interpreter.execute.assert_called_with(cc)


@mock.patch("stencila.pyla.servers.dict_decode", name="dict_decode")
def test_execute_code_expr(dict_decode):
    """Test execution of a CodeExpression (with some mocks)"""
    interpreter = mock.MagicMock(spec=Interpreter, name="interpreter")
    server = StreamServer(interpreter, BytesIO(), BytesIO())
    ce = CodeExpression("1+1")
    dict_decode.return_value = ce
    server.receive_message(
        json.dumps({"id": 13, "method": "execute", "params": {"node": "ce"}})
    )
    interpreter.execute.assert_called_with(ce)
