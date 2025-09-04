# Railway yt-dlp Service Makefile

.PHONY: help install install-dev test lint format clean run docker-build docker-run

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ --cov=app --cov-report=html --cov-report=term

lint: ## Run linting checks
	black --check app.py tests/
	isort --check app.py tests/
	flake8 app.py tests/

format: ## Format code
	black app.py tests/
	isort app.py tests/

clean: ## Clean up temporary files
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf logs/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

run: ## Run the development server
	PUBLIC_FILES_DIR=/tmp/public python app.py

run-prod: ## Run with production-like settings
	PUBLIC_FILES_DIR=/tmp/public \
	API_KEY=dev-api-key \
	LOG_LEVEL=INFO \
	python app.py

docker-build: ## Build Docker image
	docker build -t railway-yt-dlp-service .

docker-run: ## Run Docker container
	docker run -p 8000:8000 \
		-e PUBLIC_FILES_DIR=/app/public \
		railway-yt-dlp-service

setup-dev: install-dev ## Set up development environment
	pre-commit install
	@echo "Development environment ready!"
	@echo "Run 'make run' to start the development server"

check: lint test ## Run all checks (lint + test)

all: clean install-dev check ## Clean, install, and run all checks