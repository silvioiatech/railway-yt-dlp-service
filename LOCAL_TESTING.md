# Local Testing Guide - VSCode Dev Container

Complete guide for testing the Ultimate Media Downloader locally using VSCode Dev Containers.

## Prerequisites

- **VSCode** installed
- **Docker Desktop** running
- **Dev Containers extension** installed in VSCode
  - Install from: https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers

---

## Quick Start (5 Minutes)

### 1. Open in Dev Container

1. Open this project in VSCode
2. Press `F1` (or `Cmd+Shift+P` on Mac)
3. Type: **"Dev Containers: Reopen in Container"**
4. Wait 2-3 minutes for container to build

VSCode will automatically:
- Build the Docker container
- Install Python 3.11
- Install all dependencies from requirements.txt
- Install testing tools (pytest, pytest-cov)
- Configure Python environment

### 2. Run Quick Test

Once the container is ready, open a terminal in VSCode and run:

```bash
./test_local.sh
```

This script will:
- ✓ Verify Python version
- ✓ Check dependencies
- ✓ Set up environment
- ✓ Start the application
- ✓ Test all API endpoints
- ✓ Run unit tests
- ✓ Verify frontend works

**Expected output:**
```
==========================================
Ultimate Media Downloader - Local Testing
==========================================

1. Checking Python version...
Python 3.11.x
✓ Python version check

2. Checking dependencies...
✓ Dependencies installed

3. Setting up environment...
✓ Created .env from .env.local

4. Running deployment verification...
✓ Deployment verification

5. Starting application...
Application started with PID: 1234
✓ Service is ready!

6. Testing API endpoints...
  6.1. Health check...
       Response: {"status":"healthy","version":"3.1.0",...}
  ✓ Health check endpoint

  ... (more tests) ...

✓ Local testing complete!
```

---

## Manual Testing

### Option 1: Start Application Manually

```bash
# Copy environment file
cp .env.local .env

# Start the application
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

**Access:**
- **Frontend:** http://localhost:8080
- **API Docs:** http://localhost:8080/docs
- **Health Check:** http://localhost:8080/api/v1/health

### Option 2: Use Docker Compose (Outside Container)

```bash
# Build and start
docker-compose -f .devcontainer/docker-compose.yml up --build

# Access same URLs as above
```

---

## Testing Specific Features

### 1. Test Single Download

```bash
# Create download
curl -X POST http://localhost:8080/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
    "quality": "best"
  }'

# Response:
# {
#   "request_id": "abc123...",
#   "status": "queued",
#   "url": "https://...",
#   ...
# }

# Check status
curl http://localhost:8080/api/v1/downloads/abc123...
```

### 2. Test Batch Downloads

```bash
curl -X POST http://localhost:8080/api/v1/batch/download \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com/video1.mp4",
      "https://example.com/video2.mp4"
    ],
    "concurrency": 2
  }'

# Response:
# {
#   "batch_id": "batch_xyz...",
#   "total_jobs": 2,
#   ...
# }
```

### 3. Test Channel Browsing

```bash
curl "http://localhost:8080/api/v1/channel/info?url=https://www.youtube.com/@channelname&page=1&page_size=10"
```

### 4. Test Cookie Upload

```bash
# Create a test cookie file (Netscape format)
cat > /tmp/test_cookies.txt << 'EOF'
# Netscape HTTP Cookie File
.example.com    TRUE    /    FALSE    0    test_cookie    test_value
EOF

# Upload cookies
curl -X POST http://localhost:8080/api/v1/cookies \
  -H "Content-Type: application/json" \
  -d '{
    "method": "upload",
    "cookies_data": "# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tFALSE\t0\ttest_cookie\ttest_value"
  }'

# List cookies
curl http://localhost:8080/api/v1/cookies
```

### 5. Test Webhook Notifications

Start a webhook receiver:

```bash
# In a new terminal, start a simple webhook listener
python3 -c "
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        body = self.rfile.read(length).decode('utf-8')
        print(f'\n=== Webhook Received ===')
        print(f'Headers: {dict(self.headers)}')
        print(f'Body: {body}')
        print('========================\n')
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

server = HTTPServer(('0.0.0.0', 9000), WebhookHandler)
print('Webhook listener on http://localhost:9000')
server.serve_forever()
"
```

Then create a download with webhook:

```bash
curl -X POST http://localhost:8080/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
    "webhook_url": "http://host.docker.internal:9000/webhook"
  }'
```

---

## Running Tests

### Run All Tests

```bash
pytest tests/ -v --cov=app --cov-report=html
```

**Output:**
```
tests/test_api_batch.py::test_create_batch_download PASSED
tests/test_api_channel.py::test_get_channel_info PASSED
tests/test_api_cookies.py::test_upload_cookies PASSED
...
==================== 220 passed in 45.2s ====================

Coverage report: htmlcov/index.html
```

### Run Specific Test File

```bash
# Test batch downloads only
pytest tests/test_api_batch.py -v

# Test channel service only
pytest tests/test_services_channel.py -v

# Test webhooks only
pytest tests/test_services_webhook.py -v
```

### Run Tests with Coverage Report

```bash
pytest tests/ -v \
  --cov=app \
  --cov-report=html \
  --cov-report=term-missing

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Watch Mode (Auto-rerun on changes)

```bash
pip install pytest-watch

ptw tests/ -- -v
```

---

## Debugging in VSCode

### 1. Debug Configuration

VSCode is already configured with debug settings. Press `F5` to start debugging.

### 2. Manual Debug Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI: Debug",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8080",
        "--reload"
      ],
      "jinja": true,
      "justMyCode": false,
      "env": {
        "REQUIRE_API_KEY": "false",
        "API_KEY": "test",
        "STORAGE_DIR": "/tmp/railway-downloads",
        "PUBLIC_BASE_URL": "http://localhost:8080",
        "DEBUG": "true"
      }
    },
    {
      "name": "Pytest: Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "${file}",
        "-v",
        "-s"
      ],
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

### 3. Set Breakpoints

1. Click in the gutter next to line numbers to set breakpoints
2. Press `F5` to start debugging
3. Trigger the endpoint with curl or the web UI
4. VSCode will pause at breakpoints

---

## Environment Variables

### Default Development Settings

Located in `.env.local`:

```bash
# Authentication (disabled for testing)
REQUIRE_API_KEY=false
API_KEY=test-key-local-development

# Storage
STORAGE_DIR=/tmp/railway-downloads
FILE_RETENTION_HOURS=1.0

# Features
ALLOW_YT_DOWNLOADS=true
WEBHOOK_ENABLE=true

# Concurrency
WORKERS=2
MAX_CONCURRENT_DOWNLOADS=5

# Debug
DEBUG=true
LOG_LEVEL=DEBUG
```

### Override for Testing

Create `.env` to override defaults:

```bash
cp .env.local .env

# Edit .env with your custom values
nano .env
```

---

## Troubleshooting

### Issue: Port 8080 Already in Use

**Solution:**
```bash
# Find process using port 8080
lsof -ti:8080

# Kill the process
kill -9 $(lsof -ti:8080)

# Or use a different port
uvicorn app.main:app --host 0.0.0.0 --port 8888 --reload
```

### Issue: Import Errors

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "fastapi|uvicorn|pydantic|pydantic-settings"
```

### Issue: Storage Permission Errors

**Solution:**
```bash
# Create storage directory with correct permissions
mkdir -p /tmp/railway-downloads
chmod 755 /tmp/railway-downloads

# Or use a different directory
export STORAGE_DIR=/tmp/test-downloads
mkdir -p $STORAGE_DIR
```

### Issue: Tests Failing

**Solution:**
```bash
# Run with verbose output
pytest tests/ -v -s --tb=long

# Run specific failing test
pytest tests/test_api_batch.py::test_create_batch_download -v -s

# Clean test cache
rm -rf .pytest_cache __pycache__ tests/__pycache__
```

### Issue: Container Won't Build

**Solution:**
```bash
# Rebuild without cache
# In VSCode: F1 → "Dev Containers: Rebuild Container Without Cache"

# Or manually:
docker-compose -f .devcontainer/docker-compose.yml build --no-cache
```

### Issue: Dependencies Not Installing

**Solution:**
```bash
# Inside container, reinstall
pip install --no-cache-dir -r requirements.txt

# Verify Python version
python3 --version  # Should be 3.11+

# Check pip version
pip --version
```

---

## Performance Testing

### Load Testing with Apache Bench

```bash
# Install ab (if not available)
apt-get update && apt-get install -y apache2-utils

# Test health endpoint
ab -n 1000 -c 10 http://localhost:8080/api/v1/health

# Test download creation
ab -n 100 -c 5 -p /tmp/request.json -T application/json \
  http://localhost:8080/api/v1/download
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Profile specific function
python -m memory_profiler app/services/download_service.py
```

---

## Next Steps After Local Testing

Once local testing passes:

### 1. Run Pre-Deployment Verification

```bash
python3 verify_deployment.py
```

All checks should pass.

### 2. Test Frontend Manually

Open http://localhost:8080 and test:
- ✓ Single download
- ✓ Channel browsing
- ✓ Batch operations
- ✓ Cookie management
- ✓ Job history
- ✓ Real-time progress

### 3. Prepare for Railway Deployment

```bash
# Commit changes
git add .
git commit -m "Ready for deployment: all local tests passing"

# Push to trigger Railway deployment
git push origin main
```

### 4. Monitor Railway Deployment

After pushing:
1. Check Railway logs for startup messages
2. Verify health endpoint returns healthy
3. Test frontend at your Railway URL
4. Run smoke tests against production

---

## Quick Reference

### Start Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Run All Tests
```bash
pytest tests/ -v --cov=app --cov-report=html
```

### Run Quick Test Script
```bash
./test_local.sh
```

### Check Logs
```bash
tail -f /tmp/app.log
```

### Access Points
- **Frontend:** http://localhost:8080
- **API Docs:** http://localhost:8080/docs
- **Health:** http://localhost:8080/api/v1/health
- **Metrics:** http://localhost:8080/metrics

---

## Support

If you encounter issues:

1. Check application logs: `/tmp/app.log`
2. Run verification: `python3 verify_deployment.py`
3. Check Railway logs if deploying
4. Review error messages in test output

---

**Happy Testing!** 🚀
