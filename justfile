# EntitySpine Justfile
# Run with: just <recipe>
# Install just: https://github.com/casey/just

# Default recipe - show help
default:
    @just --list

# =============================================================================
# Setup
# =============================================================================

# Initial project setup
setup: install
    pre-commit install
    @echo "✓ Setup complete!"

# Install dependencies
install:
    pip install -e ".[dev]"

# Install all extras
install-full:
    pip install -e ".[full,dev]"

# =============================================================================
# Development
# =============================================================================

# Run all tests
test:
    pytest tests/ -v

# Run tests with coverage
coverage:
    pytest tests/ --cov=entityspine --cov-report=html --cov-report=term-missing
    @echo "Coverage report: htmlcov/index.html"

# Run specific test file
test-file FILE:
    pytest {{FILE}} -v

# Run tests matching pattern
test-match PATTERN:
    pytest tests/ -v -k "{{PATTERN}}"

# =============================================================================
# Code Quality
# =============================================================================

# Run linter
lint:
    ruff check src/ tests/

# Fix linting issues
lint-fix:
    ruff check src/ tests/ --fix

# Format code
fmt:
    ruff format src/ tests/

# Check formatting without changes
fmt-check:
    ruff format src/ tests/ --check

# Run type checker
typecheck:
    mypy src/entityspine

# Run all checks (lint + typecheck + test)
check: lint typecheck test

# =============================================================================
# Build & Publish
# =============================================================================

# Build package
build:
    python -m build

# Check package before upload
check-dist:
    twine check dist/*

# Upload to PyPI (requires PYPI_API_TOKEN)
publish: build check-dist
    twine upload dist/*

# Upload to TestPyPI
publish-test: build check-dist
    twine upload --repository testpypi dist/*

# =============================================================================
# Cleanup
# =============================================================================

# Remove build artifacts
clean:
    rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove all generated files including venv
clean-all: clean
    rm -rf .venv/

# =============================================================================
# Examples
# =============================================================================

# Run end-to-end example
example-e2e:
    python examples/01_end_to_end_sec_filing_to_kg.py

# Run SEC tickers example
example-tickers:
    python examples/02_load_sec_company_tickers.py

# Run all examples
examples:
    @echo "Running all examples..."
    python examples/01_end_to_end_sec_filing_to_kg.py
    python examples/02_load_sec_company_tickers.py
    python examples/03_entity_identifier_claims.py
    python examples/04_knowledge_graph_relationships.py
    python examples/05_filing_facts_ingestion.py

# =============================================================================
# Documentation
# =============================================================================

# Serve docs locally (if using mkdocs)
docs-serve:
    mkdocs serve

# Build docs
docs-build:
    mkdocs build
