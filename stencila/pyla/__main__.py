"""
__main__.py can be executed (once this library is installed) like this:

python3 -m stencila.pyla execute <inputfile> <outputfile> [parameters]

See README.md for more information.

Warning: `eval` and `exec` are used to run code in the document. Don't execute documents that you haven't verified
yourself.
"""

import logging
from sys import argv, stderr

from .interpreter import Interpreter
from .servers import StdioServer
from .system import deregister, register

# Send logs to stderr so that there it does not interfere with
# JSON-RPC comms using length-prefixed streams over stdio.
logging.basicConfig(stream=stderr, level=logging.DEBUG)

command = argv[1] if len(argv) > 1 else ""
if command == "serve":
    StdioServer(Interpreter()).start()
elif command == "register":
    register()
elif command == "deregister":
    deregister()
else:
    stderr.write('Unknown command "{}"\n'.format(command))
