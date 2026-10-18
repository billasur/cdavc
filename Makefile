.PHONY: test run-demo package-test docker-test

PYTHON ?= python3.11

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

run-demo:
	PYTHONPATH=src $(PYTHON) -m cdavc.cli examples/demo/task_graph.json \
		--provider mock \
		--mock-response examples/demo/responses/bad.json \
		--mock-response examples/demo/responses/good.json

package-test:
	$(PYTHON) -c 'import shutil; shutil.rmtree("/tmp/cdavc-package-test", ignore_errors=True)'
	$(PYTHON) -m pip install --no-deps --target /tmp/cdavc-package-test .
	PYTHONPATH=/tmp/cdavc-package-test $(PYTHON) -m cdavc --help

docker-test:
	docker build --tag cdavc:test .
	docker run --rm --network none cdavc:test
