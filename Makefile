.PHONY: help setup install dev test coverage lint format typecheck clean docker-up docker-down frontend

# Default target
help:
	@echo "EntitySpine Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup       - Initial project setup"
	@echo "  make install     - Install dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev         - Start development server"
	@echo "  make frontend    - Start frontend dev server"
	@echo "  make test        - Run tests"
	@echo "  make coverage    - Run tests with coverage"
	@echo "  make lint        - Run linter"
	@echo "  make format      - Format code"
	@echo "  make typecheck   - Run type checker"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up   - Start Docker services"
	@echo "  make docker-down - Stop Docker services"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       - Remove build artifacts"

# =============================================================================
# Setup
# =============================================================================

setup: install
	@echo "Setting up pre-commit hooks..."
	pre-commit install
	@echo "Downloading SEC data..."
	python -m entityspine download
	@echo "Setup complete!"

install:
	@echo "Installing dependencies..."
	pip install -e ".[dev,api]"

# =============================================================================
# Development
# =============================================================================

dev:
	@echo "Starting development server..."
	uvicorn entityspine.api.app:app --reload --port 8000

frontend:
	@echo "Starting frontend dev server..."
	cd frontend && npm run dev

test:
	@echo "Running tests..."
	pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	pytest tests/ -v -m unit

test-integration:
	@echo "Running integration tests..."
	pytest tests/ -v -m integration

coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=entityspine --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

# =============================================================================
# Code Quality
# =============================================================================

lint:
	@echo "Running linter..."
	ruff check src/ tests/

format:
	@echo "Formatting code..."
	ruff format src/ tests/
	ruff check --fix src/ tests/

typecheck:
	@echo "Running type checker..."
	mypy src/entityspine

check: lint typecheck test
	@echo "All checks passed!"

# =============================================================================
# Docker
# =============================================================================

docker-up:
	@echo "Starting Docker services..."
	docker-compose -f docker/docker-compose.yml up -d

docker-down:
	@echo "Stopping Docker services..."
	docker-compose -f docker/docker-compose.yml down

docker-build:
	@echo "Building Docker image..."
	docker build -t entityspine:latest -f docker/Dockerfile .

docker-logs:
	docker-compose -f docker/docker-compose.yml logs -f

# =============================================================================
# Database
# =============================================================================

db-migrate:
	@echo "Running database migrations..."
	alembic upgrade head

db-rollback:
	@echo "Rolling back last migration..."
	alembic downgrade -1

db-reset:
	@echo "Resetting database..."
	docker-compose -f docker/docker-compose.yml down -v
	docker-compose -f docker/docker-compose.yml up -d postgres
	sleep 3
	alembic upgrade head

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"
