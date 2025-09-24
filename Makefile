.PHONY: dev test build run clean lint format

# Development
dev:
	docker-compose up --build

dev-logs:
	docker-compose logs -f yt-dlp-service

# Testing
test:
	python -m pytest tests/ -v

test-coverage:
	python -m pytest tests/ --cov=. --cov-report=html

# Building
build:
	docker build -t yt-dlp-streaming-service .

# Running
run: build
	docker run -p 8080:8080 --env-file .env yt-dlp-streaming-service

# Utilities
clean:
	docker system prune -f
	docker-compose down -v

lint:
	python -m flake8 .
	python -m mypy .

format:
	python -m black .
	python -m isort .

# Setup
setup:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# Rclone setup helpers
rclone-config:
	rclone config

rclone-test:
	rclone ls $(RCLONE_REMOTE_DEFAULT): || echo "Configure your rclone remote first with 'make rclone-config'"