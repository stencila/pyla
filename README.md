# Pyla: Python Interpreter for Code Types of Stencila Schema

This is the Python implementation of an interpreter capable of interpreting executable
documents in defined in JSON using [Stencila Schema](https://stencila.github.io/schema/).

## Interpreter

Once installed it can be used like this:

```bash
$ python3 -m stencila.pyla execute <inputfile> <outputfile> [parameters]
```

`inputfile` and/or `outputfile` can be set to `-` to read from stdin and/or write to stdout (respectively).

`[parameters]` is a list of parameters to pass to the document –- these will differ based on what the document defines.
They can be passed either by `--parameter_name=parameter_value` or `--parameter_name parameter_value`. Each parameter
must be named.

### Usage in Development

There are three options to run the interpreter without installing this package (which can be useful when developing).

#### setup.py develop

Run `python3 setup.py develop` which will link this library into your site packages directory. You can then execute
documents with the above Interpreter command.

#### Run interpreter.py directly

You can run the `interpreter.py` script directly, the arguments are the same as running as a module in the example
above except the first `execute` argument is omitted:

```bash
$ python3 pyla/stencila/pyla/interpreter.py <inputfile> <outputfile> [parameters]
```

### cd into stencila directory

You can run the interpreter as a module by changing into the `stencila` directory first, and then omitting the
`stencila` namespace:

```bash
$ cd pyla/stencila
$ python3 -m pyla execute <inputfile> <outputfile> [parameters]
```
