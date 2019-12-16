"""Custom error classes"""

class CapabilityError(Exception):
    """
    Custom error class to indicate that an executor is not capable of performing a method call.

    Python implementation of Executa's
    [CapabilityError](https://github.com/stencila/executa/blob/v1.4.0/src/base/errors.ts#L57).
    Is translated to a JSON-RPC error with code `CapabilityError`.
    """

    def __init__(self, method: str, **kwargs):
        params = ', '.join(['{} = {}'.format(name, value) for name, value in kwargs.items()])
        super().__init__('Incapable of method "{}" with params "{}"'.format(method, params))
