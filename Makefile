.PHONY: install install-openai install-all test ingest search lint format clean

install:
	pip install -e ".[dev]"

install-openai:
	pip install -e ".[dev,openai]"

test:
	pytest tests/ -v

ingest:
	python3 -m cli.app ingest --spec data/sample_specs/orders-api.yaml --source data/sample_source/ --tests data/sample_features/ --karate-examples data/karate_syntax_examples/

search:
	@if [ -z "$(QUERY)" ]; then echo "Usage: make search QUERY=\"your query\""; exit 1; fi
	python3 -m cli.app retrieve "$(QUERY)"

clean:
	rm -rf .pytest_cache
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf chroma_data/
