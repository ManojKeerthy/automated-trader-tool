# ==============================================================================
# TradeCraft — Cross-Platform Task Runner
# ==============================================================================
# Requires: make (available via choco/brew/apt)
# Alternative: use the commands directly from your shell.
# ==============================================================================

.PHONY: help setup db-up db-down db-reset lint typecheck test test-unit test-integration format clean

help: ## Show available commands
	@echo "TradeCraft Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

setup: ## Initial project setup
	python -m venv .venv
	@echo "Activate virtual environment:"
	@echo "  Windows:  .venv\\Scripts\\activate"
	@echo "  macOS/Linux: source .venv/bin/activate"
	@echo "Then run: pip install -e '.[dev]'"

db-up: ## Start PostgreSQL via Docker Compose
	docker compose up -d postgres

db-down: ## Stop PostgreSQL
	docker compose down

db-reset: ## Reset database (DESTRUCTIVE)
	docker compose down -v
	docker compose up -d postgres

lint: ## Run linters
	python -m ruff check src/ tests/

typecheck: ## Run type checker
	python -m mypy src/

test: ## Run all tests
	python -m pytest tests/ -v

test-unit: ## Run unit tests only
	python -m pytest tests/unit/ -v

test-integration: ## Run integration tests only
	python -m pytest tests/integration/ -v

format: ## Auto-format code
	python -m ruff format src/ tests/
	python -m ruff check --fix src/ tests/

clean: ## Remove build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .pytest_cache/ .mypy_cache/ htmlcov/ .coverage
