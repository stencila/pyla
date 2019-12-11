"""
__main__.py can be executed (once this library is installed) like this:

python3 -m stencila.pyla execute <inputfile> <outputfile> [parameters]

See README.md for more information.

Warning: `eval` and `exec` are used to run code in the document. Don't execute documents that you haven't verified
yourself.
"""

import logging
from sys import argv, stderr

from .system import register, deregister
from .interpreter import Interpreter, execute_from_cli
from .servers import StdioServer


def cli_execute():
    """Execute an executable document, delegating to the execute_from_cli function."""
    execute_from_cli(argv[2:])


def cli_compile():
    """Compile an executable document by delegating to the execute_from_cli function with the `compile_only` flag."""
    execute_from_cli(argv[2:], True)

def main():
    """The main entry point to this module, read the first CLI arg and call out to the corresponding function."""
    command = argv[1] if len(argv) > 1 else ''

    # Send logs to stderr so that there it does not interfere with
    # JSON-RPC comms using length-prefixed streams over stdio.
    logging.basicConfig(stream=stderr, level=logging.DEBUG)

    if command == 'execute':
        cli_execute()
    elif command == 'compile':
        cli_compile()
    elif command == 'serve':
        StdioServer(Interpreter()).start()
    elif command == 'register':
        register()
    elif command == 'deregister':
        deregister()
    else:
        stderr.write('Unknown command "{}"\n'.format(command))


if __name__ == '__main__':
    main()
