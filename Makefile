.PHONY: install test lint format build docs clean all

# Install dev dependencies and pre-commit hooks
install:
	uv sync --python 3.12 --group dev --all-extras
	uv run pre-commit install

# Run tests with coverage
test:
	uv run pytest --cov=pagemodel --cov-report=term-missing

# Lint code
lint:
	uv run ruff check .

# Auto-format code
format:
	uv run ruff format .

# Build the package
build:
	uv build

# Build documentation
docs:
	uv run mkdocs build

# Remove build artifacts and caches
clean:
	rm -rf dist site .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

# Full check: install, lint, test, build, docs
all: install lint test build docs
