all: setup clean lint format test build docs

setup:
	pip3 install --user --upgrade -r requirements-dev.txt

install:
	python3 setup.py install

lint:
	pylint stencila/pyla
	mypy stencila/pyla --ignore-missing-imports

format:
	black --exclude setup.py .

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
