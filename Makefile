.PHONY: test run-demo docker-test

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

run-demo:
	PYTHONPATH=src python3 -m cdavc.cli examples/demo/task_graph.json \
		--provider mock \
		--mock-response examples/demo/responses/bad.json \
		--mock-response examples/demo/responses/good.json

docker-test:
	docker build --tag cdavc:test .
	docker run --rm --network none cdavc:test
