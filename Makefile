.PHONY: check-python test coverage run-demo benchmark-mock package-test docker-test

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
DOCKER ?= $(shell if command -v docker >/dev/null 2>&1; then command -v docker; elif test -x /Applications/Docker.app/Contents/Resources/bin/docker; then printf '%s' /Applications/Docker.app/Contents/Resources/bin/docker; else printf '%s' docker; fi)
DOCKER_BIN_DIR := $(dir $(DOCKER))

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

benchmark-mock: check-python
	PYTHONPATH=src $(PYTHON) -m cdavc.benchmark . \
		--tasks benchmarks/tasks.json \
		--mock \
		--seed 0 \
		--model mock-local \
		--quantisation mock \
		--version benchmark-v1 \
		--hardware "$(shell uname -srm)"

package-test: check-python
	$(PYTHON) -c 'import shutil; shutil.rmtree("/tmp/cdavc-package-test", ignore_errors=True)'
	$(PYTHON) -m pip install --no-deps --target /tmp/cdavc-package-test .
	PYTHONPATH=/tmp/cdavc-package-test $(PYTHON) -m cdavc --help

docker-test:
	PATH="$(DOCKER_BIN_DIR):$(PATH)" $(DOCKER) build --tag cdavc:test .
	PATH="$(DOCKER_BIN_DIR):$(PATH)" $(DOCKER) run --rm --network none cdavc:test
