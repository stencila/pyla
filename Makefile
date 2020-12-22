all: format lint test build docs

setup:
	pip3 install --user --upgrade -r requirements-dev.txt

install:
	python3 setup.py install

format:
	black --exclude setup.py .
	isort .

lint:
	black --exclude setup.py --check .
	isort . --check
	pylint stencila/pyla
	mypy stencila/pyla --ignore-missing-imports
	pydocstyle

test:
	tox

build:
	python3 setup.py sdist bdist_wheel
.PHONY: build

docs:
	python3 -m sphinx docs docs/_build
.PHONY: docs

clean:
	rm -rf build dist .coverage htmlcov coverage.xml *.egg-info .tox **/__pycache__ docs/_build
