# 🚀 Dev Container Quick Reference

## Getting Started

### Open in Dev Container
1. **Command Palette**: `Cmd+Shift+P` → "Dev Containers: Reopen in Container"
2. Wait for build and dependencies to install
3. Container starts with app running on http://localhost:8080

---

## Common Commands

### Application
```bash
# Start app with hot-reload
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Using the helper script
./.devcontainer/dev-test.sh --run

# View API docs
open http://localhost:8080/docs
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_batch_service.py -v

# Run specific test
pytest tests/unit/test_batch_service.py::test_function_name -v

# Using the helper script
./.devcontainer/dev-test.sh --coverage
```

### Code Quality
```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
ruff check app/ tests/

# All at once
./.devcontainer/dev-test.sh --format --lint
```

### Verification
```bash
# Verify setup
python .devcontainer/verify-setup.py

# Check health
curl http://localhost:8080/api/v1/health
```

---

## VS Code Tasks

Press `Cmd+Shift+P` → "Tasks: Run Task" → Select:

- **Run Application** - Start FastAPI with hot-reload
- **Run Tests** - Execute all tests
- **Run Tests with Coverage** - Generate coverage report
- **Format Code** - Auto-format with Black & isort
- **Lint Code** - Check with Ruff
- **Verify Dev Setup** - Check environment
- **Install Dependencies** - Update packages
- **View Logs** - Tail application logs

---

## Debugging

### Start Debugging
1. Set breakpoints in code
2. Press `F5` or Run → Start Debugging
3. Choose configuration:
   - **Python: FastAPI** - Debug the app
   - **Python: pytest (All Tests)** - Debug all tests
   - **Python: pytest (Current File)** - Debug current test file

### Debug Shortcuts
- `F5` - Start/Continue
- `F10` - Step Over
- `F11` - Step Into
- `Shift+F11` - Step Out
- `F9` - Toggle Breakpoint

---

## Testing API Endpoints

### Using curl
```bash
# Submit download
curl -X POST http://localhost:8080/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "best"
  }'

# Check status
curl http://localhost:8080/api/v1/downloads/{request_id}

# View logs
curl http://localhost:8080/api/v1/downloads/{request_id}/logs

# Health check
curl http://localhost:8080/api/v1/health
```

### Using Python
```python
import httpx

# Submit download
response = httpx.post(
    "http://localhost:8080/api/v1/download",
    json={"url": "...", "format": "best"}
)
print(response.json())
```

---

## File Locations

| Purpose | Location |
|---------|----------|
| Downloads | `/app/data/downloads/` |
| Logs | `/workspace/logs/` |
| Coverage Reports | `/workspace/htmlcov/` |
| Tests | `/workspace/tests/` |
| Application | `/workspace/app/` |

---

## Environment Variables

All configured in `docker-compose.yml`:
- `DEBUG=true` - Verbose logging
- `REQUIRE_API_KEY=false` - No auth needed
- `MAX_CONCURRENT_DOWNLOADS=3` - Parallel jobs
- `FILE_RETENTION_HOURS=1.0` - Auto-delete after 1h

---

## Troubleshooting

### Container won't start
```bash
# Rebuild container
Cmd+Shift+P → "Dev Containers: Rebuild Container"
```

### Dependencies missing
```bash
pip install -r requirements.txt -r requirements-test.txt
```

### Port already in use
```bash
# Find process
lsof -i :8080
# Kill it
kill -9 <PID>
```

### Clear test artifacts
```bash
rm -rf htmlcov/ .coverage .pytest_cache/ __pycache__/
```

---

## Useful Links

- **API Docs**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **Health**: http://localhost:8080/api/v1/health
- **Metrics**: http://localhost:8080/metrics

---

## Pro Tips

✅ Tests auto-discover in `/workspace/tests/`  
✅ Hot-reload watches for file changes  
✅ Coverage reports open with `open htmlcov/index.html`  
✅ Use VS Code tasks for common operations  
✅ Breakpoints work in both app and tests  
✅ Logs persist in `/workspace/logs/`

---

**Need Help?** Check `.devcontainer/README.md` for detailed documentation.
