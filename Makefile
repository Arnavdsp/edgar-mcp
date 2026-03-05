.PHONY: lint test docker-build
lint:
	uv run ruff check src tests evals
test:
	uv run pytest -q
docker-build:
	docker build -t edgar-mcp:dev .
