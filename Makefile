.PHONY: help install install-dev sync test test-unit test-e2e test-cov lint format format-check type-check check clean run server pre-commit-install pre-commit-run

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	uv sync

install-dev: ## Install with dev and test dependencies
	uv sync --group dev --group test

sync: ## Sync all dependency groups
	uv sync --group dev --group test

# Testing
test: ## Run unit tests (mocked, no Resend needed)
	uv run pytest tests/ -m "not e2e" -v

test-unit: ## Run unit tests (alias for test)
	uv run pytest tests/ -m "not e2e" -v

test-e2e: ## Run E2E tests (requires RESEND_E2E=1 + live API key)
	RESEND_E2E=1 uv run pytest tests/e2e/ -v -m e2e

test-cov: ## Run unit tests with coverage
	uv run pytest tests/ -m "not e2e" --cov=src/resend_blade_mcp --cov-report=term-missing -v

# Code quality
lint: ## Run ruff linter
	uv run ruff check src/ tests/

format: ## Format code with ruff
	uv run ruff format src/ tests/

format-check: ## Check formatting without changes
	uv run ruff format --check src/ tests/

type-check: ## Run mypy type checking
	uv run mypy src/resend_blade_mcp

check: lint format-check type-check ## Run all quality checks
	@echo "All quality checks passed!"

# Pre-commit
pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-run: ## Run pre-commit on all files
	uv run pre-commit run --all-files

# Running
run: ## Start the MCP server (stdio transport)
	uv run resend-blade-mcp

server: run ## Alias for run

# Cleanup
clean: ## Remove build artifacts and caches
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
