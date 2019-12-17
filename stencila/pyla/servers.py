"""
Module for server classes.
"""

import sys

import enum
import json
import logging
import typing
from socket import socket
from stencila.schema.types import Node
from stencila.schema.util import from_dict, object_encode

from .errors import CapabilityError
from .interpreter import Interpreter

StreamType = typing.Union[typing.BinaryIO, socket]


def rpc_json_object_encode(node: Node) -> typing.Union[dict, str]:
    """Like `stencila.schema.util.object_encode` but with support for JsonRpcError."""
    if isinstance(node, JsonRpcError):
        return {
            'code': node.code.value,
            'message': str(node),
            'data': node.data
        }

    return object_encode(node)


def to_json(node: Node) -> str:
    """Convert a node including JsonRrpcErrors, to JSON"""
    return json.dumps(node, default=rpc_json_object_encode, indent=2)


def data_to_bytes(data: typing.Any) -> bytes:
    """Convert `data` to `bytes`."""
    return bytes((data,))


def encode_int(number: int) -> bytes:
    """Pack `number` into varint bytes"""
    buf = b''
    while True:
        to_write = number & 0x7f
        number >>= 7
        if number:
            buf += data_to_bytes(to_write | 0x80)
        else:
            buf += data_to_bytes(to_write)
            break
    return buf


def read_one(stream: StreamType) -> int:
    """Read a byte from the file (as an integer).

    Raises EOFError if the stream ends while reading bytes.
    """
    char = stream_read(stream, 1)
    if not char:
        raise EOFError('Unexpected EOF while reading bytes')
    return ord(char)


def read_length_prefix(stream: StreamType) -> int:
    """Read a varint from `stream`"""
    shift = 0
    result = 0
    while True:
        i = read_one(stream)
        result |= (i & 0x7f) << shift
        shift += 7
        if not i & 0x80:
            break

    return result


def get_stream_buffer(stream: typing.BinaryIO) -> typing.BinaryIO:
    """Get the buffer from a stream, if it exists."""
    buffer = getattr(stream, 'buffer', None)
    return buffer if buffer else stream


def io_read(stream: typing.BinaryIO, count: int) -> bytes:
    """Read `count` bytes from `stream` or its underlying buffer if it exists."""
    return get_stream_buffer(stream).read(count)


def io_write(stream: typing.BinaryIO, message: bytes) -> None:
    """Write to `stream` or its underlying buffer if it exists."""
    stream = get_stream_buffer(stream)
    stream.write(message)
    stream.flush()


def stream_read(stream: StreamType, count: int) -> bytes:
    """Abstract reading from stream to work with IO (buffered/unbuffered) and sockets."""
    if isinstance(stream, socket):
        return stream.recv(count)

    return io_read(stream, count)


def stream_write(stream: StreamType, message: bytes) -> None:
    """Abstract writing to stream to work with IO (buffered/unbuffered) and sockets."""
    if isinstance(stream, socket):
        stream.send(message)
    else:
        io_write(stream, message)


def message_read(stream: StreamType) -> str:
    """Read a length-prefixed message from the stream"""
    message_len = read_length_prefix(stream)
    return stream_read(stream, message_len).decode('utf8')


def message_write(stream: StreamType, message: str) -> None:
    """Write a length-prefixed message to the stream."""
    bites = message.encode('utf8')
    stream_write(stream, encode_int(len(bites)))
    stream_write(stream, bites)


class JsonRpcErrorCode(enum.Enum):
    """
    Error codes defined in JSON-RPC 2.0

    Codes -32000 to -32099	are reserved for implementation-defined server-errors.

    Python implementation of Executa's
    [JsonRpcErrorCode](https://github.com/stencila/executa/blob/v1.0.0/src/base/JsonRpcError.ts#L14).
    """

    """
    Invalid JSON was received by the server.
    An error occurred on the server while parsing the JSON text.
    """
    ParseError = -32700

    """The JSON sent is not a valid Request object."""
    InvalidRequest = -32600

    """The method does not exist / is not available."""
    MethodNotFound = -32601

    """Invalid method parameter(s)."""
    InvalidParams = -32602

    """Internal JSON-RPC error."""
    InternalError = -32603

    """Generic server error."""
    ServerError = -32000

    """Capability error."""
    CapabilityError = -32005


class JsonRpcError(Exception):
    """
    A JSON-RPC error that may be part of a response

    Python implementation of Executa's
    [JsonRpcError](https://github.com/stencila/executa/blob/v1.0.0/src/base/JsonRpcError.ts).
    """

    """
    A number that indicates the error type that occurred.
    This MUST be an integer.
    """
    code: JsonRpcErrorCode

    """
    A primitive or structured value that contains additional information about the error.
    This may be omitted.
    The value of this member is defined by the server (e.g. detailed error information,
    nested errors etc.).
    """
    data: typing.Any

    def __init__(self, code: JsonRpcErrorCode, message: str, data: typing.Any = None):
        super().__init__(message)
        self.code = code
        self.data = data


class StreamServer:
    """
    A server that communicates using length-prefixed JSON-RPC messages over streams or sockets.

    Python implementation of Executa's
    [StreamServer](https://github.com/stencila/executa/blob/v1.0.0/src/stdio/StreamServer.ts#L10)
    """

    interpreter: Interpreter
    input_stream: StreamType
    output_stream: StreamType

    def __init__(self, interpreter: Interpreter, input_stream: StreamType, output_stream: StreamType) -> None:
        self.interpreter = interpreter
        self.input_stream = input_stream
        self.output_stream = output_stream

    def read_message(self) -> typing.Iterable[str]:
        """Read a length-prefixed message from the input stream then repeat."""
        while True:
            yield message_read(self.input_stream)

    def write_message(self, message: str) -> None:
        """Write a length-prefixed message to the output stream."""
        message_write(self.output_stream, message)

    def receive_message(self, message: str) -> str:
        """
        Receive a JSON-RPC request and send back a JSON-RPC response.

        The response may have a JSON-RPC `error` if the request was bad.

        Python implementation of Executa's
        [Server.receive](https://github.com/stencila/executa/blob/v1.0.1/src/base/Server.ts#L61).
        """
        request_id = None
        result = None
        error = None

        try:
            try:
                request = json.loads(message)
            except Exception as exc:
                raise JsonRpcError(JsonRpcErrorCode.ParseError, 'Parse error: {}'.format(exc))

            request_id = request.get('id')
            method = request.get('method')
            params = request.get('params')

            if method == 'manifest':
                result = Interpreter.MANIFEST
            elif method in ('compile', 'execute'):
                node = params.get('node')
                if node is None:
                    raise JsonRpcError(JsonRpcErrorCode.InvalidParams, 'Invalid params: "node" is missing')
                node = from_dict(node)
                result = self.interpreter.compile(node) if method == 'compile' else self.interpreter.execute(node)
            else:
                raise JsonRpcError(JsonRpcErrorCode.MethodNotFound, 'Method not found: {}'.format(method))
        except JsonRpcError as exc:
            error = exc
        except CapabilityError as exc:
            error = JsonRpcError(JsonRpcErrorCode.CapabilityError, 'Capability error: {}'.format(exc))
        except Exception as exc:  # pylint: disable=broad-except
            logging.exception(exc)
            error = JsonRpcError(JsonRpcErrorCode.ServerError, 'Internal error: {}'.format(exc))

        response: typing.Dict[str, typing.Any] = {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': result,
            'error': error
        }

        return to_json(response)

    def start(self) -> None:
        """
        Run the server in a loop forever (since the `read_message` generator never finishes).
        """
        for message in self.read_message():
            response = self.receive_message(message)
            self.write_message(response)


class StdioServer(StreamServer):
    """
    A `StreamServer` that uses `stdio` as the transport.

    Python implementation of Executa's
    [StdioServer](https://github.com/stencila/executa/blob/v1.0.0/src/stdio/StdioServer.ts#L12)
    """

    def __init__(self, interpreter: Interpreter):
        super().__init__(interpreter, sys.stdin.buffer, sys.stdout.buffer)
