# Ultimate Media Downloader - Implementation Guide

## Quick Start

This guide provides a complete roadmap for implementing the backend architecture defined in the accompanying architecture documents.

---

## Architecture Documents

1. **BACKEND_ARCHITECTURE.md** - Core architecture, project structure, models, yt-dlp integration
2. **BACKEND_ARCHITECTURE_PART2.md** - Response models, queue system, download manager, file management
3. **BACKEND_ARCHITECTURE_PART3.md** - Complete API route handlers for all endpoints
4. **BACKEND_ARCHITECTURE_PART4.md** - Middleware, configuration, deployment, security

---

## Phase 1: Foundation Setup (Week 1)

### Day 1-2: Project Structure & Configuration

**Tasks:**
1. Create project directory structure
2. Set up virtual environment
3. Install dependencies
4. Configure environment variables
5. Set up logging

**Commands:**
```bash
# Create project
mkdir railway-yt-dlp-service && cd railway-yt-dlp-service

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create directory structure
mkdir -p app/{api/v1,models,services,middleware,utils,core}
mkdir -p tests/{unit,integration,e2e}
mkdir -p logs static

# Copy environment template
cp .env.example .env
# Edit .env with your configuration
```

**Files to Create:**
- `app/__init__.py`
- `app/config.py` (from Part 4)
- `app/core/exceptions.py` (from Part 4)
- `.env` (from `.env.example`)
- `requirements.txt` (from Part 4)

**Validation:**
```bash
# Test configuration loading
python -c "from app.config import get_settings; print(get_settings())"
```

---

### Day 3-4: Core Models

**Tasks:**
1. Implement request models
2. Implement response models
3. Add validation
4. Write unit tests for models

**Files to Create:**
- `app/models/__init__.py`
- `app/models/requests.py` (from Part 1)
- `app/models/responses.py` (from Part 2)

**Testing:**
```python
# tests/unit/test_models.py
from app.models.requests import DownloadRequest
from pydantic import ValidationError
import pytest

def test_download_request_valid():
    req = DownloadRequest(url="https://example.com/video")
    assert req.url == "https://example.com/video"

def test_download_request_invalid_url():
    with pytest.raises(ValidationError):
        DownloadRequest(url="not-a-url")
```

**Run Tests:**
```bash
pytest tests/unit/test_models.py -v
```

---

### Day 5-7: yt-dlp Integration

**Tasks:**
1. Implement YtdlpWrapper
2. Implement YtdlpOptionsBuilder
3. Test metadata extraction
4. Test format detection
5. Test download functionality

**Files to Create:**
- `app/services/__init__.py`
- `app/services/ytdlp_wrapper.py` (from Part 1)
- `app/services/ytdlp_options.py` (from Part 1)

**Testing:**
```python
# tests/unit/test_ytdlp_wrapper.py
import pytest
from pathlib import Path
from app.services.ytdlp_wrapper import YtdlpWrapper

@pytest.mark.asyncio
async def test_extract_info():
    wrapper = YtdlpWrapper(storage_dir=Path("/tmp/test"))
    info = await wrapper.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert info['id'] == 'dQw4w9WgXcQ'
    assert 'title' in info
```

---

## Phase 2: Core Services (Week 2)

### Day 1-3: Queue Manager & Job Processing

**Tasks:**
1. Implement QueueManager
2. Implement Job class
3. Add job lifecycle management
4. Test concurrent job processing

**Files to Create:**
- `app/services/queue_manager.py` (from Part 2)

**Testing:**
```python
# tests/unit/test_queue_manager.py
@pytest.mark.asyncio
async def test_submit_job():
    manager = QueueManager(max_workers=2)
    await manager.start()

    async def job_callback(job):
        return {"result": "success"}

    job_id = await manager.submit_job(
        job_type="test",
        payload={},
        callback=job_callback
    )

    assert job_id
    job = await manager.get_job(job_id)
    assert job.status == JobStatus.QUEUED

    await manager.shutdown()
```

---

### Day 4-5: File Management

**Tasks:**
1. Implement FileManager
2. Add auto-cleanup scheduler
3. Test deletion scheduling
4. Test storage stats

**Files to Create:**
- `app/services/file_manager.py` (from Part 2)

**Testing:**
```python
# tests/unit/test_file_manager.py
@pytest.mark.asyncio
async def test_schedule_deletion():
    manager = FileManager(storage_dir=Path("/tmp/test"))

    # Create test file
    test_file = Path("/tmp/test/test.txt")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")

    # Schedule deletion (1 second for testing)
    deletion_time = await manager.schedule_deletion(test_file, delay_hours=1/3600)

    # File should exist initially
    assert test_file.exists()

    # Wait for deletion
    await asyncio.sleep(2)

    # File should be deleted
    assert not test_file.exists()
```

---

### Day 6-7: Download Manager

**Tasks:**
1. Implement DownloadManager
2. Integrate all services
3. Test end-to-end download flow
4. Add webhook support

**Files to Create:**
- `app/services/download_manager.py` (from Part 2)
- `app/services/webhook_service.py`
- `app/services/auth_manager.py`

---

## Phase 3: API Layer (Week 3)

### Day 1-2: Main Application & Middleware

**Tasks:**
1. Implement FastAPI application
2. Add all middleware
3. Configure CORS
4. Set up lifespan handlers

**Files to Create:**
- `app/main.py` (from Part 1)
- `app/dependencies.py` (from Part 4)
- `app/middleware/auth.py` (from Part 4)
- `app/middleware/rate_limit.py` (from Part 4)
- `app/middleware/security.py` (from Part 4)
- `app/middleware/request_logger.py` (from Part 4)
- `app/middleware/error_handler.py` (from Part 4)

**Testing:**
```bash
# Start application
uvicorn app.main:app --reload

# Test in another terminal
curl http://localhost:8000/api/v1/health
```

---

### Day 3-5: API Endpoints

**Tasks:**
1. Implement download endpoints
2. Implement format detection
3. Implement playlist endpoints
4. Implement batch endpoints
5. Implement health/metrics

**Files to Create:**
- `app/api/__init__.py`
- `app/api/v1/__init__.py`
- `app/api/v1/router.py` (from Part 3)
- `app/api/v1/download.py` (from Part 3)
- `app/api/v1/formats.py` (from Part 3)
- `app/api/v1/playlist.py` (from Part 3)
- `app/api/v1/batch.py` (from Part 3)
- `app/api/v1/health.py` (from Part 3)

**Testing:**
```python
# tests/e2e/test_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_download():
    response = client.post(
        "/api/v1/download",
        headers={"X-API-Key": "test-key"},
        json={"url": "https://example.com/video"}
    )
    assert response.status_code == 201
    data = response.json()
    assert "request_id" in data
    assert data["status"] == "queued"
```

---

### Day 6-7: Integration Testing

**Tasks:**
1. Write integration tests
2. Test complete download flows
3. Test error scenarios
4. Performance testing

**Integration Tests:**
```python
# tests/integration/test_download_flow.py
@pytest.mark.asyncio
async def test_complete_download_flow():
    # 1. Submit download
    # 2. Poll status
    # 3. Download file
    # 4. Verify auto-deletion
    pass
```

---

## Phase 4: Deployment (Week 4)

### Day 1-2: Docker Setup

**Tasks:**
1. Create Dockerfile
2. Build and test image locally
3. Set up docker-compose for development
4. Optimize image size

**Files to Create:**
- `Dockerfile` (from Part 4)
- `docker-compose.yml`
- `.dockerignore`

**Commands:**
```bash
# Build image
docker build -t ultimate-downloader:latest .

# Run locally
docker run -p 8080:8080 \
  -e API_KEY=test-key \
  -v $(pwd)/data:/app/data \
  ultimate-downloader:latest

# Test
curl http://localhost:8080/api/v1/health
```

---

### Day 3-4: Railway Deployment

**Tasks:**
1. Configure Railway project
2. Set up volumes
3. Configure environment variables
4. Deploy and test

**Files to Create:**
- `railway.toml` (from Part 4)

**Deployment Steps:**

1. **Install Railway CLI:**
```bash
npm install -g @railway/cli
railway login
```

2. **Initialize Project:**
```bash
railway init
railway link
```

3. **Configure Volume:**
```bash
# In Railway dashboard:
# 1. Go to your service
# 2. Navigate to "Volumes"
# 3. Create new volume:
#    - Name: downloads-storage
#    - Mount path: /app/data
```

4. **Set Environment Variables:**
```bash
railway variables set API_KEY=your-secret-key-here
railway variables set STORAGE_DIR=/app/data
railway variables set WORKERS=4
railway variables set LOG_LEVEL=INFO
```

5. **Deploy:**
```bash
railway up
```

6. **Get URL:**
```bash
railway domain
# Or check dashboard for assigned domain
```

---

### Day 5-6: Monitoring & Observability

**Tasks:**
1. Set up Prometheus metrics
2. Configure logging
3. Set up alerts
4. Create dashboards

**Metrics to Monitor:**
- Request rate
- Error rate
- Download success rate
- Queue depth
- Storage usage
- API latency

**Prometheus Queries:**
```promql
# Request rate
rate(jobs_total[5m])

# Error rate
rate(jobs_total{status="failed"}[5m]) / rate(jobs_total[5m])

# Queue depth
jobs_in_flight

# Storage usage
storage_bytes_used / storage_bytes_total
```

---

### Day 7: Documentation

**Tasks:**
1. Generate OpenAPI docs
2. Write user guides
3. Create integration examples
4. Document deployment

**Auto-Generated API Docs:**
- Swagger UI: `https://your-app.railway.app/api/docs`
- ReDoc: `https://your-app.railway.app/api/redoc`
- OpenAPI JSON: `https://your-app.railway.app/api/openapi.json`

---

## Testing Strategy

### Unit Tests (80%+ Coverage)

```bash
# Run all unit tests
pytest tests/unit/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_ytdlp_wrapper.py -v

# Run with coverage
pytest --cov=app --cov-report=term-missing
```

### Integration Tests

```bash
# Run integration tests
pytest tests/integration/ -v

# Run with specific markers
pytest -m integration
```

### E2E Tests

```bash
# Run end-to-end tests
pytest tests/e2e/ -v

# Run against live API
LIVE_API_URL=https://your-app.railway.app pytest tests/e2e/
```

### Load Testing

```python
# locustfile.py
from locust import HttpUser, task, between

class DownloadUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_download(self):
        self.client.post(
            "/api/v1/download",
            headers={"X-API-Key": "test-key"},
            json={"url": "https://example.com/video"}
        )

    @task
    def check_health(self):
        self.client.get("/api/v1/health")
```

```bash
# Run load test
locust -f locustfile.py --host=http://localhost:8080
```

---

## Monitoring Checklist

### Application Metrics
- [ ] Request rate (req/sec)
- [ ] Response time (p50, p95, p99)
- [ ] Error rate (%)
- [ ] Download success rate (%)
- [ ] Queue depth
- [ ] Active downloads
- [ ] Storage usage

### System Metrics
- [ ] CPU usage
- [ ] Memory usage
- [ ] Disk I/O
- [ ] Network I/O
- [ ] Container restarts

### Alerts
- [ ] High error rate (> 5%)
- [ ] Slow response time (> 2s)
- [ ] Storage > 90% full
- [ ] Queue depth > 100
- [ ] Health check failures

---

## Security Checklist

### Authentication & Authorization
- [ ] API key authentication implemented
- [ ] Constant-time comparison for keys
- [ ] Rate limiting per IP and API key
- [ ] CORS properly configured

### Input Validation
- [ ] URL validation
- [ ] Domain allowlist (if configured)
- [ ] File size limits
- [ ] Timeout limits
- [ ] Path traversal prevention

### Security Headers
- [ ] X-Content-Type-Options
- [ ] X-Frame-Options
- [ ] X-XSS-Protection
- [ ] Strict-Transport-Security
- [ ] Content-Security-Policy

### Data Protection
- [ ] No personal data logging
- [ ] Secure file deletion
- [ ] HTTPS only
- [ ] Secure cookie handling

---

## Production Readiness Checklist

### Code Quality
- [ ] Type hints throughout
- [ ] Comprehensive tests (80%+ coverage)
- [ ] No linting errors
- [ ] Documentation complete

### Performance
- [ ] API response < 500ms (p95)
- [ ] Download success rate > 99%
- [ ] Handles 10+ concurrent downloads
- [ ] Auto-cleanup working

### Reliability
- [ ] Health checks passing
- [ ] Error handling comprehensive
- [ ] Graceful shutdown
- [ ] Auto-restart on failure

### Security
- [ ] All security headers present
- [ ] Authentication working
- [ ] Rate limiting active
- [ ] Input validation complete

### Monitoring
- [ ] Metrics exposed
- [ ] Logging configured
- [ ] Alerts set up
- [ ] Dashboard created

### Documentation
- [ ] API docs generated
- [ ] User guide written
- [ ] Integration examples
- [ ] Deployment guide

---

## Troubleshooting Guide

### Common Issues

**Issue: API returns 401 Unauthorized**
```bash
# Check API key is set
railway variables get API_KEY

# Verify header in request
curl -H "X-API-Key: your-key" https://your-app.railway.app/api/v1/health
```

**Issue: Downloads failing**
```bash
# Check yt-dlp version
railway run yt-dlp --version

# Check storage space
railway run df -h /app/data

# Check logs
railway logs
```

**Issue: High memory usage**
```bash
# Check active downloads
curl https://your-app.railway.app/api/v1/stats

# Reduce workers
railway variables set WORKERS=2
```

**Issue: Rate limiting too aggressive**
```bash
# Adjust limits
railway variables set RATE_LIMIT_PER_MINUTE=120
railway variables set RATE_LIMIT_PER_HOUR=2000
```

---

## Maintenance Tasks

### Daily
- [ ] Check health endpoint
- [ ] Monitor error rate
- [ ] Review logs for issues

### Weekly
- [ ] Clean up old job records
- [ ] Review storage usage
- [ ] Check for yt-dlp updates
- [ ] Review metrics

### Monthly
- [ ] Update dependencies
- [ ] Security audit
- [ ] Performance review
- [ ] Backup configuration

---

## Additional Resources

### API Client Examples

**Python:**
```python
import requests

API_URL = "https://your-app.railway.app/api/v1"
API_KEY = "your-api-key"

def download_video(url):
    response = requests.post(
        f"{API_URL}/download",
        headers={"X-API-Key": API_KEY},
        json={"url": url}
    )
    return response.json()

job = download_video("https://example.com/video")
print(f"Job ID: {job['request_id']}")
```

**JavaScript:**
```javascript
const API_URL = 'https://your-app.railway.app/api/v1';
const API_KEY = 'your-api-key';

async function downloadVideo(url) {
    const response = await fetch(`${API_URL}/download`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY
        },
        body: JSON.stringify({ url })
    });
    return response.json();
}

const job = await downloadVideo('https://example.com/video');
console.log(`Job ID: ${job.request_id}`);
```

**cURL:**
```bash
curl -X POST https://your-app.railway.app/api/v1/download \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"url": "https://example.com/video"}'
```

---

## Summary

This implementation guide provides a complete roadmap for building the Ultimate Media Downloader backend. Follow the phases sequentially, ensuring each component is tested before moving to the next.

**Total Timeline: 4 weeks**
- Week 1: Foundation (models, yt-dlp integration)
- Week 2: Core services (queue, file management, download manager)
- Week 3: API layer (endpoints, middleware, testing)
- Week 4: Deployment (Docker, Railway, monitoring)

**Key Success Factors:**
1. Test each component thoroughly
2. Follow the architecture documents exactly
3. Monitor metrics from day one
4. Document as you build
5. Security first, always

Good luck with your implementation!
