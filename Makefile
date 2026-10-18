.PHONY: check-python test coverage run-demo package-test docker-test

PYTHON ?= python3

check-python:
	$(PYTHON) -c 'import sys; assert sys.version_info >= (3, 11), "CD-AVC requires Python 3.11+"'

test: check-python
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

coverage: check-python
	PYTHONPATH=src $(PYTHON) -m coverage run --source=src/cdavc -m unittest discover -s tests
	$(PYTHON) -m coverage report -m

run-demo:
	PYTHONPATH=src $(PYTHON) -m cdavc.cli examples/demo/task_graph.json \
		--provider mock \
		--mock-response examples/demo/responses/bad.json \
		--mock-response examples/demo/responses/good.json

package-test: check-python
	$(PYTHON) -c 'import shutil; shutil.rmtree("/tmp/cdavc-package-test", ignore_errors=True)'
	$(PYTHON) -m pip install --no-deps --target /tmp/cdavc-package-test .
	PYTHONPATH=/tmp/cdavc-package-test $(PYTHON) -m cdavc --help

docker-test:
	docker build --tag cdavc:test .
	docker run --rm --network none cdavc:test
