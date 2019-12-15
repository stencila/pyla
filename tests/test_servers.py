from io import BytesIO
import json
import pytest
from unittest import mock

from stencila.schema.types import CodeChunk, CodeExpression

from stencila.pyla.interpreter import Interpreter
from stencila.pyla.servers import StreamServer, message_read, message_write, read_one, encode_int, JsonRpcErrorCode


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
    for encoded, raw in ((b'\x01', 1), (b'\x80\x02', 256), (b'\x80\x08', 1024), (b'\x80\x80\x04', 65536)):
        assert encoded == encode_int(raw)


def test_eof_read():
    """Test that EOFError is raised at the end of the stream read."""
    stream = BytesIO()
    with pytest.raises(EOFError):
        read_one(stream)


def test_receive_message_manifest():
    """Test receiving a manifest message."""
    message = json.dumps({
        'id': 10,
        'method': 'manifest',
    })

    input_str = BytesIO()
    output_str = BytesIO()
    server = StreamServer(Interpreter(), input_str, output_str)
    response = server.receive_message(message)
    decoded = json.loads(response)
    assert decoded == {
        'jsonrpc': '2.0',
        'id': 10,
        'result': {
            'capabilities': {
                'manifest': True,
                'execute': True
            }
        },
        'error': None
    }


def test_receive_message_execute():
    """Test receiving an execute method, the execute_node method should be called with the node."""
    message = json.dumps({
        'id': 11,
        'method': 'execute',
        'params': {
            'node': 'code-node'
        }
    })

    input_str = BytesIO()
    output_str = BytesIO()
    server = StreamServer(Interpreter(), input_str, output_str)
    server.execute_node = mock.MagicMock(name='execute_node', return_value='executed-code')

    response = server.receive_message(message)
    decoded = json.loads(response)
    assert decoded == {
        'jsonrpc': '2.0',
        'id': 11,
        'result': 'executed-code',
        'error': None
    }
    server.execute_node.assert_called_with('code-node')


def test_receive_message_execute_without_node():
    """Test that JsonRpcError with code JsonRpcErrorCode.InvalidParams is returned if node is missing/None"""
    message = json.dumps({
        'id': 12,
        'method': 'execute',
        'params': {
        }
    })

    input_str = BytesIO()
    output_str = BytesIO()
    server = StreamServer(Interpreter(), input_str, output_str)

    response = server.receive_message(message)
    decoded = json.loads(response)
    assert decoded == {
        'jsonrpc': '2.0',
        'id': 12,
        'result': None,
        'error': {
            'code': JsonRpcErrorCode.InvalidParams.value,
            'message': 'Invalid params: "node" is missing',
            'data': None
        }
    }


def test_receive_message_with_invalid_json():
    """Test that a JsonRpcError with code JsonRpcErrorCode.ParseError is returned if JSON is not valid."""
    input_str = BytesIO()
    output_str = BytesIO()
    server = StreamServer(Interpreter(), input_str, output_str)

    response = server.receive_message("not a valid json")
    decoded = json.loads(response)
    assert decoded == {
        'jsonrpc': '2.0',
        'id': None,
        'result': None,
        'error': {
            'code': JsonRpcErrorCode.ParseError.value,
            'message': 'Parse error: Expecting value: line 1 column 1 (char 0)',
            'data': None
        }
    }


def test_receive_message_with_unknown_method():
    """Test that a JsonRpcError with code JsonRpcErrorCode.MethodNotFound is returned if method is not valid."""
    message = json.dumps({
        'id': 13,
        'method': 'not-real',
        'params': {
        }
    })

    input_str = BytesIO()
    output_str = BytesIO()
    server = StreamServer(Interpreter(), input_str, output_str)

    response = server.receive_message(message)
    decoded = json.loads(response)
    assert decoded == {
        'jsonrpc': '2.0',
        'id': 13,
        'result': None,
        'error': {
            'code': JsonRpcErrorCode.MethodNotFound.value,
            'message': 'Method not found: not-real',
            'data': None
        }
    }


def test_receive_message_with_internal_server_error():
    """Test that a JsonRpcError with code JsonRpcErrorCode.ServerError if some other exception occurs"""
    message = json.dumps({
        'id': 13,
        'method': 'execute',
        'params': {
            'node': 'code-node'
        }
    })

    input_str = BytesIO()
    output_str = BytesIO()
    server = StreamServer(Interpreter(), input_str, output_str)

    server.execute_node = mock.MagicMock(name='execute_node', side_effect=ValueError('test exception'))

    response = server.receive_message(message)
    decoded = json.loads(response)
    assert decoded == {
        'jsonrpc': '2.0',
        'id': 13,
        'result': None,
        'error': {
            'code': JsonRpcErrorCode.ServerError.value,
            'message': 'Internal error: test exception',
            'data': None
        }
    }


@mock.patch('stencila.pyla.servers.simple_code_chunk_parse', name='simple_code_chunk_parse')
@mock.patch('stencila.pyla.servers.from_dict', name='from_dict')
def test_execute_code_chunk(from_dict, simple_code_chunk_parse):
    """Test execution of a CodeChunk (with some mocks)"""
    cc = CodeChunk('1+1')

    from_dict.return_value = cc
    node = {'node': 'node_value'}

    input_str = BytesIO()
    output_str = BytesIO()
    interpreter = mock.MagicMock(spec=Interpreter, name='interpreter')
    server = StreamServer(interpreter, input_str, output_str)
    executed = server.execute_node(node)

    from_dict.assert_called_with(node)
    simple_code_chunk_parse.assert_called_with(cc)
    interpreter.execute.assert_called_with([simple_code_chunk_parse.return_value], {})

    assert executed == cc



@mock.patch('stencila.pyla.servers.from_dict', name='from_dict')
def test_execute_code_expr(from_dict):
    """Test execution of a CodeExpression (with some mocks)"""
    ce = CodeExpression('1+1')

    from_dict.return_value = ce
    node = {'node': 'node_value'}

    input_str = BytesIO()
    output_str = BytesIO()
    interpreter = mock.MagicMock(spec=Interpreter, name='interpreter')
    server = StreamServer(interpreter, input_str, output_str)
    executed = server.execute_node(node)

    from_dict.assert_called_with(node)
    interpreter.execute.assert_called_with([ce], {})

    assert executed == ce

