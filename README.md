# 🐍 Pyla

#### Python interpreter for Stencila

[![Build Status](https://dev.azure.com/stencila/stencila/_apis/build/status/stencila.pyla?branchName=master)](https://dev.azure.com/stencila/stencila/_build/latest?definitionId=3&branchName=master)
[![Code coverage](https://codecov.io/gh/stencila/pyla/branch/master/graph/badge.svg)](https://codecov.io/gh/stencila/pyla)
[![PyPI](https://img.shields.io/pypi/v/stencila-pyla.svg)](https://pypi.org/project/stencila-pyla)
[![Docs](https://img.shields.io/badge/docs-latest-blue.svg)](https://stencila.github.io/pyla/)

This is the Python implementation of an interpreter capable of interpreting executable
documents defined in JSON using [Stencila Schema](https://stencila.github.io/schema/).

## Install

Pyla is available as a Python package,

```bash
pip3 install stencila-pyla
```

## Use

Once installed it can be used like this:

```bash
$ python3 -m stencila.pyla execute <inputfile> <outputfile> [parameters]
```

- `<inputfile>` and/or `<outputfile>` can be set to `-` to read from stdin and/or write to stdout (respectively).

- `[parameters]` is a list of parameters to pass to the document –- these will differ based on what the document defines.
They can be passed either by `--parameter_name=parameter_value` or `--parameter_name parameter_value`. Each parameter
must be named.

## Develop

There are three options to run the interpreter without installing this package (which can be useful when developing).

### Use `setup.py develop`

Run `python3 setup.py develop` which will link this library into your site packages directory. You can then execute
documents with the above command.

### Run `interpreter.py` directly

You can run the `interpreter.py` script directly, the arguments are the same as running as a module in the example
above except the first `execute` argument is omitted:

```bash
$ python3 stencila/pyla/interpreter.py <inputfile> <outputfile> [parameters]
```

### Change into `stencila` folder

You can run the interpreter as a module by changing into the `stencila` directory first, and then omitting the
`stencila` namespace:

```bash
$ cd stencila
$ python3 -m pyla execute <inputfile> <outputfile> [parameters]
```
