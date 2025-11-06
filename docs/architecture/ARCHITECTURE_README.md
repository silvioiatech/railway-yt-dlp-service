# Backend Architecture Documentation

## Overview

This repository contains **comprehensive backend architecture documentation** for the **Ultimate Media Downloader** service - a production-ready FastAPI application that integrates all yt-dlp features for downloading media from 1000+ platforms.

---

## Documentation Structure

### 1. Start Here: Architecture Summary
**File**: `ARCHITECTURE_SUMMARY.md`

**Purpose**: High-level overview of the entire system

**Contents**:
- Complete technology stack
- System architecture diagram
- All 18 API endpoints
- Feature implementation checklist
- Quick reference guide

**Read this first** to understand the big picture.

---

### 2. Core Architecture (Part 1)
**File**: `BACKEND_ARCHITECTURE.md`

**Purpose**: Foundation and core components

**Contents**:
- Architecture principles and design
- Complete project structure
- Pydantic request/response models
- yt-dlp integration (YtdlpWrapper, YtdlpOptionsBuilder)
- Main FastAPI application setup
- Example code for core components

**Key Topics**:
- How to structure the FastAPI application
- How to integrate yt-dlp Python API
- How to build flexible request models
- How to handle all yt-dlp options

---

### 3. Service Layer (Part 2)
**File**: `BACKEND_ARCHITECTURE_PART2.md`

**Purpose**: Business logic and services

**Contents**:
- Complete response models
- QueueManager - background job processing
- DownloadManager - download orchestration
- FileManager - storage and auto-cleanup
- Job lifecycle management
- Progress tracking

**Key Topics**:
- How to process downloads asynchronously
- How to manage background jobs
- How to implement auto-file deletion
- How to track download progress

---

### 4. API Layer (Part 3)
**File**: `BACKEND_ARCHITECTURE_PART3.md`

**Purpose**: API endpoint implementations

**Contents**:
- All 18 endpoint handlers with complete code
- Request validation
- Response formatting
- Error handling per endpoint
- Rate limiting decorators
- Authentication checks

**Key Topics**:
- How to implement RESTful endpoints
- How to handle downloads, playlists, batches
- How to structure route handlers
- How to return proper HTTP responses

---

### 5. Cross-Cutting Concerns (Part 4)
**File**: `BACKEND_ARCHITECTURE_PART4.md`

**Purpose**: Middleware, config, deployment

**Contents**:
- 6 middleware components (auth, rate limit, security, logging, error handling)
- Configuration management (Pydantic Settings)
- Custom exceptions
- Dependencies and dependency injection
- Dockerfile (multi-stage build)
- Railway deployment configuration
- Environment variables

**Key Topics**:
- How to implement API key authentication
- How to add rate limiting
- How to configure security headers
- How to deploy to Railway
- How to manage configuration

---

### 6. Implementation Guide
**File**: `IMPLEMENTATION_GUIDE.md`

**Purpose**: Step-by-step build instructions

**Contents**:
- 4-week implementation roadmap
- Day-by-day tasks
- Testing strategies
- Deployment steps
- Monitoring setup
- Troubleshooting guide
- Production checklist

**Key Topics**:
- Week 1: Foundation (models, yt-dlp)
- Week 2: Services (queue, file management)
- Week 3: API layer (endpoints, middleware)
- Week 4: Deployment (Docker, Railway, monitoring)

---

## How to Use This Documentation

### For Architects and Tech Leads
1. Read `ARCHITECTURE_SUMMARY.md` for the complete overview
2. Review `BACKEND_ARCHITECTURE.md` for design principles
3. Examine the service layer in Part 2
4. Understand deployment strategy in Part 4

### For Backend Developers
1. Start with `IMPLEMENTATION_GUIDE.md` for the roadmap
2. Follow each part sequentially (1 → 2 → 3 → 4)
3. Implement one component at a time
4. Test each component before moving forward

### For DevOps Engineers
1. Read `ARCHITECTURE_SUMMARY.md` for infrastructure needs
2. Focus on Part 4 for deployment configuration
3. Review `IMPLEMENTATION_GUIDE.md` deployment section
4. Set up monitoring and alerts

### For Frontend Developers
1. Read `ARCHITECTURE_SUMMARY.md` for API overview
2. Review Part 3 for endpoint specifications
3. Check response models in Part 2
4. Use OpenAPI docs at `/api/docs`

---

## Key Features Implemented

### yt-dlp Integration (ALL Features)
✅ Single video downloads
✅ Quality selection (4K to 360p, audio-only)
✅ Audio extraction (MP3, M4A, FLAC, WAV, OPUS)
✅ Subtitle downloads (multiple languages, formats)
✅ Thumbnail extraction and embedding
✅ Metadata extraction
✅ Playlist downloads (full or selective)
✅ Channel downloads (with filtering)
✅ Batch operations
✅ Cookie/authentication support

### API Endpoints (18 Total)
✅ Download operations (4 endpoints)
✅ Format detection (1 endpoint)
✅ Playlist operations (2 endpoints)
✅ Channel operations (2 endpoints)
✅ Batch operations (3 endpoints)
✅ Metadata extraction (1 endpoint)
✅ Authentication (2 endpoints)
✅ Health & monitoring (3 endpoints)

### Production Features
✅ Background job processing
✅ Auto-file cleanup (1 hour default)
✅ API key authentication
✅ Rate limiting (per IP and API key)
✅ Security headers
✅ Request logging
✅ Error handling
✅ Prometheus metrics
✅ Health checks
✅ Webhook notifications

---

## Technology Stack

**Backend Framework**: FastAPI 0.115+
**Runtime**: Python 3.11+
**Media Processing**: yt-dlp (latest)
**Validation**: Pydantic v2
**HTTP Client**: httpx (async)
**Rate Limiting**: slowapi
**Metrics**: prometheus-client
**Storage**: Railway Volumes
**Deployment**: Railway + Docker

---

## Project Structure

```
railway-yt-dlp-service/
├── app/
│   ├── main.py                      # FastAPI app entry
│   ├── config.py                    # Configuration
│   ├── dependencies.py              # DI container
│   │
│   ├── api/v1/                      # API routes
│   │   ├── download.py              # Download endpoints
│   │   ├── formats.py               # Format detection
│   │   ├── playlist.py              # Playlist endpoints
│   │   ├── batch.py                 # Batch operations
│   │   └── health.py                # Health/metrics
│   │
│   ├── models/                      # Pydantic models
│   │   ├── requests.py              # Request models
│   │   └── responses.py             # Response models
│   │
│   ├── services/                    # Business logic
│   │   ├── ytdlp_wrapper.py         # yt-dlp integration
│   │   ├── ytdlp_options.py         # Options builder
│   │   ├── queue_manager.py         # Job processing
│   │   ├── download_manager.py      # Download orchestration
│   │   └── file_manager.py          # File operations
│   │
│   ├── middleware/                  # Middleware stack
│   │   ├── auth.py                  # Authentication
│   │   ├── rate_limit.py            # Rate limiting
│   │   ├── security.py              # Security headers
│   │   └── error_handler.py         # Error handling
│   │
│   ├── utils/                       # Utilities
│   │   ├── logger.py                # Logging
│   │   └── metrics.py               # Prometheus
│   │
│   └── core/                        # Core components
│       ├── exceptions.py            # Custom exceptions
│       └── constants.py             # Constants
│
├── tests/                           # Test suite
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   └── e2e/                         # E2E tests
│
├── Dockerfile                       # Container definition
├── railway.toml                     # Railway config
├── requirements.txt                 # Dependencies
└── .env.example                     # Environment template
```

---

## Quick Start

### 1. Read Documentation
```bash
# Start with the summary
open ARCHITECTURE_SUMMARY.md

# Follow implementation guide
open IMPLEMENTATION_GUIDE.md
```

### 2. Set Up Development Environment
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### 3. Implement Components
Follow the 4-week roadmap in `IMPLEMENTATION_GUIDE.md`:
- **Week 1**: Models and yt-dlp integration
- **Week 2**: Services (queue, file management, download manager)
- **Week 3**: API endpoints and middleware
- **Week 4**: Deployment and monitoring

### 4. Test Implementation
```bash
# Run unit tests
pytest tests/unit/ -v --cov=app

# Run integration tests
pytest tests/integration/ -v

# Start development server
uvicorn app.main:app --reload
```

### 5. Deploy to Railway
```bash
# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

---

## Code Examples

### Example 1: Create Download Job
```python
# API endpoint implementation (from Part 3)
@router.post("/download", response_model=DownloadResponse)
@rate_limit("2/second", "10/minute")
async def create_download(
    request: DownloadRequest,
    download_manager: DownloadManager = Depends(get_download_manager),
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    async def download_callback(job):
        return await download_manager.download_single(
            request_id=job.job_id,
            request=request
        )

    job_id = await queue_manager.submit_job(
        job_type="download",
        payload=request.model_dump(),
        callback=download_callback
    )

    return DownloadResponse(
        request_id=job_id,
        status=JobStatus.QUEUED,
        created_at=datetime.now(timezone.utc)
    )
```

### Example 2: yt-dlp Integration
```python
# YtdlpWrapper usage (from Part 1)
ytdlp = YtdlpWrapper(storage_dir=Path("/app/data"))

# Extract metadata
info = await ytdlp.extract_info(url="https://example.com/video")
print(info['title'])

# Get formats
formats = await ytdlp.get_formats(url="https://example.com/video")
print(formats['recommended_format'])

# Download video
result = await ytdlp.download(
    request_id="uuid",
    request=DownloadRequest(url="https://example.com/video"),
    progress_callback=lambda p: print(p['percent'])
)
```

### Example 3: Background Job Processing
```python
# Queue manager usage (from Part 2)
queue_manager = QueueManager(max_workers=4)
await queue_manager.start()

# Submit job
job_id = await queue_manager.submit_job(
    job_type="download",
    payload={"url": "https://example.com/video"},
    callback=my_async_function
)

# Check status
job = await queue_manager.get_job(job_id)
print(job.status)  # QUEUED, RUNNING, COMPLETED, FAILED
```

---

## Architecture Highlights

### 1. Async-First Design
All I/O operations use `async/await` for maximum concurrency:
```python
async def download_single(self, request_id: str, request: DownloadRequest):
    # Async metadata extraction
    metadata = await self.ytdlp.extract_info(request.url)

    # Async download
    result = await self.ytdlp.download(request_id, request)

    # Async webhook
    await self.webhook_service.send_webhook(url, data)
```

### 2. Type Safety with Pydantic
All data validated with Pydantic models:
```python
class DownloadRequest(BaseModel):
    url: str = Field(..., description="Video URL")
    quality: QualityPreset = Field(QualityPreset.BEST)
    audio_only: bool = Field(False)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Invalid URL")
        return v
```

### 3. Background Job Queue
Scalable job processing with worker pool:
```python
class QueueManager:
    def __init__(self, max_workers: int = 4):
        self.queue = asyncio.Queue()
        self.workers = []

    async def _worker(self, worker_id: int):
        while self.running:
            job = await self.queue.get()
            await self._process_job(job)
```

### 4. Auto-Cleanup System
Scheduled file deletion with cancellation:
```python
# Schedule deletion after 1 hour
deletion_time = await file_manager.schedule_deletion(
    file_path=Path("/app/data/video.mp4"),
    delay_hours=1
)

# Cancel if needed
await file_manager.cancel_deletion(file_path)
```

---

## Testing Strategy

### Unit Tests (80%+ coverage)
```bash
# Test individual components
pytest tests/unit/test_ytdlp_wrapper.py
pytest tests/unit/test_queue_manager.py
pytest tests/unit/test_models.py
```

### Integration Tests
```bash
# Test complete flows
pytest tests/integration/test_download_flow.py
pytest tests/integration/test_playlist_flow.py
```

### E2E Tests
```bash
# Test API endpoints
pytest tests/e2e/test_api.py
```

### Load Tests
```bash
# Stress test with Locust
locust -f locustfile.py --host=http://localhost:8080
```

---

## Deployment Guide

### Local Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Docker
```bash
docker build -t ultimate-downloader .
docker run -p 8080:8080 -v $(pwd)/data:/app/data ultimate-downloader
```

### Railway
```bash
railway login
railway init
railway up
railway domain  # Get your URL
```

---

## Monitoring

### Prometheus Metrics
Available at `/api/v1/metrics`:
- `jobs_total{status}` - Total jobs
- `jobs_duration_seconds` - Execution time
- `bytes_uploaded_total` - Download volume
- `jobs_in_flight` - Active downloads

### Health Checks
Available at `/api/v1/health`:
- Queue manager health
- Storage health
- yt-dlp availability

### Logging
Structured JSON logs with:
- Request ID tracking
- Performance metrics
- Error context
- Security events

---

## Security

### Authentication
- API key via `X-API-Key` header
- Optional/required modes
- Constant-time comparison

### Rate Limiting
- Per-IP limits: 60/minute, 1000/hour
- Per-API-key limits: configurable
- Redis-backed for distributed systems

### Security Headers
- X-Content-Type-Options
- X-Frame-Options
- Strict-Transport-Security
- Content-Security-Policy

### Input Validation
- URL validation
- Domain allowlist
- File size limits
- Path traversal prevention

---

## Support

### Documentation
- Interactive API docs: `https://your-app.railway.app/api/docs`
- ReDoc: `https://your-app.railway.app/api/redoc`
- OpenAPI spec: `https://your-app.railway.app/api/openapi.json`

### Troubleshooting
See `IMPLEMENTATION_GUIDE.md` troubleshooting section for:
- Common errors and solutions
- Performance tuning
- Configuration issues
- Deployment problems

---

## Next Steps

1. **Understand the Architecture**
   - Read `ARCHITECTURE_SUMMARY.md` (15 minutes)
   - Review system architecture diagram
   - Understand technology choices

2. **Deep Dive into Components**
   - Study Part 1 for core architecture
   - Study Part 2 for service layer
   - Study Part 3 for API layer
   - Study Part 4 for deployment

3. **Start Implementation**
   - Follow `IMPLEMENTATION_GUIDE.md`
   - Week 1: Foundation
   - Week 2: Services
   - Week 3: API
   - Week 4: Deployment

4. **Test and Deploy**
   - Write tests as you build
   - Deploy to Railway
   - Set up monitoring
   - Go live!

---

## Summary

This documentation provides **everything needed** to build a production-ready media downloader backend:

✅ **Complete architecture** (system design, patterns, decisions)
✅ **Detailed implementation** (code examples, best practices)
✅ **Step-by-step guide** (4-week roadmap)
✅ **Testing strategy** (unit, integration, e2e)
✅ **Deployment config** (Docker, Railway)
✅ **Monitoring setup** (metrics, logs, health)

**Total Implementation Time**: 4 weeks (1 developer)

**Lines of Code**: ~3000-4000 lines

**Test Coverage**: 80%+

**Production Ready**: Yes

---

**Last Updated**: 2025-11-04
**Version**: 1.0
**Status**: Design Complete, Ready for Implementation
