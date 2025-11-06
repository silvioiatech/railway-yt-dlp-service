# Dev Container Setup Guide

This dev container provides a complete development environment for the Railway yt-dlp Service.

## Quick Start

### 1. Open in Dev Container

**Option A: Using VS Code**
1. Install the "Dev Containers" extension in VS Code
2. Open this project folder
3. Press `F1` and select "Dev Containers: Reopen in Container"
4. Wait for the container to build and dependencies to install

**Option B: Using Command Palette**
- `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
- Type "Reopen in Container"
- Select the option

### 2. Verify Setup

Once inside the container, open a terminal and run:

```bash
# Check Python version
python --version  # Should show Python 3.11.x

# Verify dependencies
pip list | grep fastapi
pip list | grep yt-dlp

# Run health check
curl http://localhost:8080/api/v1/health
```

### 3. Run the Application

The application starts automatically with hot-reload enabled. Access it at:
- **API**: http://localhost:8080
- **Docs**: http://localhost:8080/docs
- **Health**: http://localhost:8080/api/v1/health

To manually restart:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_batch_service.py

# Run with verbose output
pytest -v

# Run and watch for changes
pytest-watch
```

### 5. Access Test Reports

After running tests with coverage:
```bash
# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## What's Included

### Pre-installed Tools
- Python 3.11
- Git & GitHub CLI
- FastAPI & Uvicorn
- yt-dlp
- pytest & testing tools
- Code formatters (Black, isort, Ruff)

### VS Code Extensions
- Python language support
- Pylance (type checking)
- Black formatter
- isort (import organizer)
- Ruff (linter)
- YAML & TOML support
- Docker support

### Environment Variables

The dev container comes pre-configured with:
- `REQUIRE_API_KEY=false` - No auth required for testing
- `DEBUG=true` - Verbose logging
- `LOG_LEVEL=DEBUG` - Detailed logs
- `STORAGE_DIR=/app/data` - Download storage
- `MAX_CONCURRENT_DOWNLOADS=3` - Concurrent job limit

See `docker-compose.yml` for full configuration.

## Common Tasks

### Test a Download

```bash
# Using curl
curl -X POST http://localhost:8080/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "best"
  }'

# Or use Python
python examples/webhook_example.py
```

### Check Logs

```bash
# View application logs
tail -f logs/app.log

# View specific download logs
curl http://localhost:8080/api/v1/downloads/{request_id}/logs
```

### Debug Issues

```bash
# Check service health
curl http://localhost:8080/api/v1/health

# View Prometheus metrics
curl http://localhost:8080/metrics

# List downloaded files
ls -la /app/data/downloads/
```

### Format Code

```bash
# Format with Black
black app/ tests/

# Sort imports
isort app/ tests/

# Lint with Ruff
ruff check app/ tests/
```

## Storage Locations

- **Downloads**: `/app/data/downloads/`
- **Logs**: `/workspace/logs/`
- **Test Coverage**: `/workspace/htmlcov/`
- **Workspace**: `/workspace/`

## Troubleshooting

### Container Won't Start
1. Check Docker is running
2. Try rebuilding: "Dev Containers: Rebuild Container"
3. Check logs in VS Code Output panel

### Port Already in Use
```bash
# Find process using port 8080
lsof -i :8080

# Kill the process
kill -9 <PID>
```

### Dependencies Missing
```bash
# Reinstall dependencies
pip install -r requirements.txt -r requirements-test.txt
```

### Permission Issues
```bash
# Fix ownership (run as root)
chown -R vscode:vscode /workspace
```

## Next Steps

1. Read the [API Reference](../docs/api/API_REFERENCE_COMPLETE.md)
2. Check the [Architecture](../docs/architecture/ARCHITECTURE_README.md)
3. Review [Testing Guide](../tests/README.md)
4. Explore [Examples](../examples/)

## Tips

- The container auto-reloads on code changes
- Use integrated terminal for better experience
- Coverage reports auto-generate in `htmlcov/`
- Logs persist in the workspace `logs/` directory
- Downloads are stored in Docker volume for persistence
