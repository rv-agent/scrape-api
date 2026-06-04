# Makefile for ScrapeAPI

.PHONY: help install dev test lint format clean docker-up docker-down

# Default target
help:
	@echo "ScrapeAPI - Available commands:"
	@echo ""
	@echo "  make install      Install dependencies"
	@echo "  make dev          Run development server"
	@echo "  make test         Run tests"
	@echo "  make lint         Run linters"
	@echo "  make format       Format code"
	@echo "  make clean        Clean build artifacts"
	@echo "  make docker-up    Start Docker services"
	@echo "  make docker-down  Stop Docker services"

# Install dependencies
install:
	pip install -r requirements.txt
	playwright install chromium

# Run development server
dev:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest tests/ -v --cov=src --cov-report=html

# Run linters
lint:
	ruff check src/ tests/
	mypy src/

# Format code
format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ *.egg-info htmlcov/ .coverage .pytest_cache .mypy_cache

# Docker commands
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Run with Docker
docker-dev:
	docker-compose -f docker-compose.yml up --build
