.PHONY: help install install-dev test test-unit test-e2e test-cov test-fast \
        lint lint-fix format format-check typecheck typecheck-mypy typecheck-pyright \
        check clean clean-cache clean-all shell

VENV := .venv
PYTHON := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
PYRIGHT := $(VENV)/bin/pyright

SRC_DIR := src
TEST_DIR := tests
E2E_DIR := tests/e2e

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Installation:"
	@echo "  install          Install package"
	@echo "  install-dev      Install package with dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests (unit + e2e)"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-e2e         Run e2e tests only"
	@echo "  test-fast        Run tests without slow markers"
	@echo "  test-cov         Run tests with coverage report"
	@echo "  test-cov-html    Run tests with HTML coverage report"
	@echo ""
	@echo "Linting:"
	@echo "  lint             Run ruff linter"
	@echo "  lint-fix         Run ruff and auto-fix issues"
	@echo "  format           Format code with ruff"
	@echo "  format-check     Check code formatting without changes"
	@echo ""
	@echo "Type Checking:"
	@echo "  typecheck        Run all type checkers (mypy + pyright)"
	@echo "  typecheck-mypy   Run mypy type checker"
	@echo "  typecheck-pyright Run pyright type checker"
	@echo ""
	@echo "Combined:"
	@echo "  check            Run all checks (lint + typecheck + test-unit)"
	@echo "  check-all        Run all checks including e2e tests"
	@echo "  ci               Run CI checks (format-check + lint + typecheck + test-cov)"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean            Remove build artifacts"
	@echo "  clean-cache      Remove cache directories"
	@echo "  clean-all        Remove all generated files"

# Installation
install:
	$(VENV)/bin/pip install -e .

install-dev:
	$(VENV)/bin/pip install -e ".[dev]"

# Testing
test: test-unit test-e2e

test-unit:
	$(PYTEST) $(TEST_DIR) -v

test-e2e:
	$(PYTEST) $(E2E_DIR) -v

test-fast:
	$(PYTEST) $(TEST_DIR) -v -m "not slow"

test-cov:
	$(PYTEST) $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=term-missing

test-cov-html:
	$(PYTEST) $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

# Linting
lint:
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)

lint-fix:
	$(RUFF) check $(SRC_DIR) $(TEST_DIR) --fix

format:
	$(RUFF) format $(SRC_DIR) $(TEST_DIR)

format-check:
	$(RUFF) format $(SRC_DIR) $(TEST_DIR) --check

# Type Checking
typecheck: typecheck-mypy typecheck-pyright

typecheck-mypy:
	$(MYPY) $(SRC_DIR)

typecheck-pyright:
	$(PYRIGHT) $(SRC_DIR)

# Combined checks
check: lint typecheck test-unit

check-all: lint typecheck test

ci: format-check lint typecheck test-cov

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf $(SRC_DIR)/*.egg-info/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm E2E_TEST_RESULTS.md

clean-cache:
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .resume_cache/

clean-all: clean clean-cache
