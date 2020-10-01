# 🐍 Pyla

#### Python interpreter for executable documents

[![Build Status](https://dev.azure.com/stencila/stencila/_apis/build/status/stencila.pyla?branchName=master)](https://dev.azure.com/stencila/stencila/_build/latest?definitionId=3&branchName=master)
[![Code coverage](https://codecov.io/gh/stencila/pyla/branch/master/graph/badge.svg)](https://codecov.io/gh/stencila/pyla)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
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

Register Pyla so that it can be discovered by other executors on your machine, 

```bash
python3 -m stencila.pyla register
```

Then, if you have [`executa`](https://github.com/stencila/executa) installed then you can run it using the `repl` command and specifying `python` as the starting language,

```bash
executa repl python
```

## Develop

### setup

To install the packages needed for development, run `make setup` or,

```bash
pip3 install --user --upgrade -r requirements-dev.txt
```

### Code formatting

We use [Black](https://github.com/psf/black) to maintain a consistent code formatting style. To run it use `black .` or `make format`.

### Running

There are two options to run the interpreter without installing this package (which can be useful when developing).

#### Use `setup.py develop`

Run `python3 setup.py develop` which will link this library into your site packages directory. You can then execute
documents with the above command.


#### Change into `stencila` folder

You can run the interpreter as a module by changing into the `stencila` directory first, and then omitting the
`stencila` namespace:

```bash
$ cd stencila
$ python3 -m pyla execute <inputfile> <outputfile> [parameters]
```
