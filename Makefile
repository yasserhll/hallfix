.PHONY: install test lint format typecheck check

install:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy

check: lint typecheck test
