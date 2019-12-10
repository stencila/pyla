all: setup clean lint test build

setup:
	pip3 install --user --upgrade -r requirements-dev.txt

install:
	python3 setup.py install

lint:
	pylint stencila/pyla --max-line-length=120
	mypy stencila/pyla --ignore-missing-imports

test:
	tox

build:
	python3 setup.py sdist bdist_wheel

clean:
	rm -rf build dist .coverage htmlcov coverage.xml *.egg-info .tox **/__pycache__
