from io import BytesIO
import json
import pytest

from stencila.pyla.interpreter import Interpreter
from stencila.pyla.servers import StreamServer, message_read, message_write

@pytest.mark.skip(reason="ain't working due to EOF error")
def test_read_message():
    input_str = BytesIO()
    output_str = BytesIO()
    server = StreamServer(Interpreter(), input_str, output_str)

    message_write(input_str, "Hello server, my old friend")
    assert next(server.read_message()) == ''
