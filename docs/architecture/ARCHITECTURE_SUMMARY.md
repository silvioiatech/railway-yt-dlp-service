# Ultimate Media Downloader - Architecture Summary

## Overview

This document provides a high-level summary of the complete backend architecture for the Ultimate Media Downloader service as specified in the PRD.

---

## Architecture Documents Index

| Document | Purpose | Key Content |
|----------|---------|-------------|
| **BACKEND_ARCHITECTURE.md** | Core architecture and foundation | Project structure, models, yt-dlp integration, main components |
| **BACKEND_ARCHITECTURE_PART2.md** | Service layer implementation | Response models, queue manager, download manager, file management |
| **BACKEND_ARCHITECTURE_PART3.md** | API layer implementation | Complete route handlers for all 18 endpoints |
| **BACKEND_ARCHITECTURE_PART4.md** | Cross-cutting concerns | Middleware, configuration, security, deployment |
| **IMPLEMENTATION_GUIDE.md** | Step-by-step implementation | 4-week roadmap, testing, deployment, monitoring |

---

## Technology Stack

### Core Technologies
- **Runtime**: Python 3.11+
- **Framework**: FastAPI 0.115+
- **Media Processing**: yt-dlp (latest)
- **Validation**: Pydantic v2
- **HTTP Client**: httpx (async)

### Infrastructure
- **Deployment**: Railway
- **Storage**: Railway Volumes
- **Containerization**: Docker
- **Monitoring**: Prometheus

### Key Libraries
- **slowapi**: Rate limiting
- **aiofiles**: Async file I/O
- **prometheus-client**: Metrics
- **cryptography**: Security

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                            │
│  (Web UI, Mobile App, Third-party Integrations)             │
└────────────────────────┬────────────────────────────────────┘
                         │
                    HTTPS/JSON API
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  FastAPI Gateway                            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Middleware │  │   Middleware │  │   Middleware │      │
│  │     CORS     │  │  Rate Limit  │  │     Auth     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               API Routes (v1)                        │  │
│  │  /download  /playlist  /batch  /channel  /metadata  │  │
│  └────────────────────┬─────────────────────────────────┘  │
└────────────────────────┼────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Service Layer                              │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Download   │  │     Queue    │  │     File     │      │
│  │   Manager    │  │   Manager    │  │   Manager    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
│  ┌─────────────────────────▼──────────────────────────┐     │
│  │           yt-dlp Wrapper Service                   │     │
│  │  - Metadata extraction                             │     │
│  │  - Format detection                                │     │
│  │  - Download execution                              │     │
│  │  - Progress tracking                               │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Storage Layer                              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Railway Volume Storage                     │  │
│  │                                                       │  │
│  │  /app/data/videos/          - Video downloads       │  │
│  │  /app/data/playlists/       - Playlist downloads    │  │
│  │  /app/data/cookies/         - Auth cookies          │  │
│  │  /app/data/temp/            - Temporary files       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints (18 Total)

### Download Operations (4)
1. `POST /api/v1/download` - Create download job
2. `GET /api/v1/download/{id}` - Get download status
3. `GET /api/v1/download/{id}/logs` - Get download logs
4. `DELETE /api/v1/download/{id}` - Cancel download

### Format Detection (1)
5. `GET /api/v1/formats` - Get available formats

### Playlist Operations (2)
6. `GET /api/v1/playlist/preview` - Preview playlist
7. `POST /api/v1/playlist/download` - Download playlist

### Channel Operations (2)
8. `GET /api/v1/channel/info` - Get channel info
9. `POST /api/v1/channel/download` - Download channel videos

### Batch Operations (3)
10. `POST /api/v1/batch/download` - Batch download
11. `GET /api/v1/batch/{id}` - Get batch status
12. `DELETE /api/v1/batch/{id}` - Cancel batch

### Metadata (1)
13. `GET /api/v1/metadata` - Extract metadata

### Authentication (2)
14. `POST /api/v1/auth/cookies` - Upload cookies
15. `DELETE /api/v1/auth/cookies/{id}` - Delete cookies

### Health & Monitoring (3)
16. `GET /api/v1/health` - Health check
17. `GET /api/v1/metrics` - Prometheus metrics
18. `GET /api/v1/stats` - Service statistics

---

## Core Features Implementation

### yt-dlp Integration (ALL Features)

✅ **Basic Downloads**
- Single video download
- Quality selection (4K, 1080p, 720p, 480p, 360p, audio-only)
- Custom format strings
- Auto-quality selection

✅ **Audio Extraction**
- Multiple formats (MP3, M4A, FLAC, WAV, OPUS, AAC)
- Bitrate selection (96k-320k)
- Thumbnail embedding
- Metadata preservation

✅ **Subtitle Support**
- Multiple languages
- Auto-generated subtitles
- Format conversion (SRT, VTT, ASS)
- Subtitle embedding

✅ **Thumbnail Management**
- Download thumbnails
- Embed in files
- Format conversion
- All resolutions

✅ **Playlist Support**
- Full playlist download
- Selective download (ranges, specific videos)
- Resume capability
- Error recovery

✅ **Channel Support**
- Channel video listing
- Date filtering
- Duration filtering
- View count filtering
- Sort options

✅ **Metadata Extraction**
- Complete video metadata
- No download required
- JSON export
- Channel information

✅ **Authentication**
- Cookie file upload
- Browser cookie extraction
- Secure storage
- Session management

✅ **Batch Operations**
- Multiple URL processing
- Concurrent downloads
- Progress tracking
- Error handling

---

## Request/Response Models

### Request Models (7 Main Types)
1. **DownloadRequest** - Single video download (30+ fields)
2. **PlaylistDownloadRequest** - Playlist operations
3. **ChannelDownloadRequest** - Channel downloads
4. **BatchDownloadRequest** - Batch operations
5. **CookiesUploadRequest** - Authentication
6. **Quality/Format Enums** - Structured options
7. **Validation Rules** - Input validation

### Response Models (12 Types)
1. **DownloadResponse** - Job status and results
2. **FormatsResponse** - Available formats
3. **PlaylistPreviewResponse** - Playlist browsing
4. **ChannelInfoResponse** - Channel details
5. **BatchDownloadResponse** - Batch job info
6. **MetadataResponse** - Extracted metadata
7. **LogsResponse** - Job logs
8. **HealthResponse** - Health check
9. **StatsResponse** - Statistics
10. **CancelResponse** - Cancellation
11. **CookiesResponse** - Cookie management
12. **Error Responses** - Standardized errors

---

## Service Layer Components

### 1. YtdlpWrapper
**Purpose**: Python API wrapper for yt-dlp
**Features**:
- Async execution
- Progress callbacks
- Error handling
- Format detection
- Metadata extraction

### 2. YtdlpOptionsBuilder
**Purpose**: Build yt-dlp options from requests
**Features**:
- Format string generation
- Post-processor configuration
- Subtitle options
- Thumbnail options
- Path templating

### 3. QueueManager
**Purpose**: Background job processing
**Features**:
- Async job queue
- Worker pool management
- Concurrency control
- Job lifecycle tracking
- Statistics

### 4. DownloadManager
**Purpose**: Download orchestration
**Features**:
- Single/playlist/batch downloads
- Progress tracking
- Webhook notifications
- Cookie management
- Error recovery

### 5. FileManager
**Purpose**: File operations and cleanup
**Features**:
- Auto-deletion scheduling
- Storage statistics
- Path security
- Empty directory cleanup
- Disk space monitoring

### 6. AuthManager
**Purpose**: Cookie and authentication
**Features**:
- Cookie storage
- Browser extraction
- Secure handling
- Expiry management

### 7. WebhookService
**Purpose**: Event notifications
**Features**:
- HTTP callbacks
- Retry logic
- Signature verification
- Timeout handling

---

## Middleware Stack (6 Layers)

1. **GZip Middleware** - Response compression
2. **SecurityHeadersMiddleware** - Security headers
3. **ErrorHandlerMiddleware** - Global error handling
4. **RequestLoggingMiddleware** - Request/response logging
5. **CORSMiddleware** - Cross-origin requests
6. **SlowAPIMiddleware** - Rate limiting

---

## Security Features

### Authentication
- API key authentication
- Constant-time comparison
- Optional/required modes
- Per-request validation

### Authorization
- Role-based access (future)
- Resource ownership (future)
- Action permissions (future)

### Rate Limiting
- Per-IP limits
- Per-API-key limits
- Configurable windows
- Redis-backed (optional)

### Input Validation
- URL validation
- Domain allowlist
- File size limits
- Path traversal prevention
- Command injection prevention

### Security Headers
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Strict-Transport-Security
- Content-Security-Policy
- Permissions-Policy

### Data Protection
- No personal data logging
- Secure file deletion
- HTTPS enforcement
- Encrypted secrets

---

## Monitoring & Observability

### Prometheus Metrics
- `jobs_total{status}` - Total jobs by status
- `jobs_duration_seconds` - Job execution time
- `bytes_uploaded_total` - Bytes downloaded
- `jobs_in_flight` - Active downloads
- `storage_bytes_used` - Storage usage

### Structured Logging
- Request/response logs
- Error logs with stack traces
- Performance logs
- Security events
- JSON format

### Health Checks
- Liveness probe (`/api/v1/health`)
- Readiness probe
- Component checks (storage, queue, yt-dlp)
- Dependency health

### Statistics
- Job counts by status
- Success/failure rates
- Average download time
- Queue depth
- Storage usage
- Active downloads

---

## File Management

### Auto-Cleanup System
- **Default retention**: 1 hour after download
- **Scheduled deletion**: Background task
- **Cancellable**: Users can cancel deletion
- **Smart cleanup**: Removes empty directories
- **Monitoring**: Storage quota alerts

### Path Templating
```
Supported variables:
- {id} - Video ID
- {title} - Video title
- {safe_title} - Sanitized title
- {ext} - File extension
- {uploader} - Channel name
- {date} - Upload date
- {random} - Random string
- {playlist} - Playlist name
- {playlist_index} - Position in playlist
```

### Storage Organization
```
/app/data/
  videos/              # Single downloads
  playlists/           # Playlist downloads
    {playlist_name}/
      001-video.mp4
      002-video.mp4
  channels/            # Channel downloads
    {channel_name}/
  cookies/             # Authentication
  temp/                # Temporary files
```

---

## Configuration

### Environment Variables (25+)
- Application settings (name, version, debug)
- Server settings (host, port, workers)
- Storage settings (directory, retention, size limits)
- Security settings (API key, domains, YouTube)
- Rate limiting (per minute/hour, Redis)
- CORS settings
- Logging settings
- Monitoring settings
- yt-dlp settings
- Webhook settings
- Database settings (optional)

### Runtime Configuration
- Pydantic Settings
- Type validation
- Environment file support
- Defaults for all values
- Railway integration

---

## Deployment Architecture

### Docker Container
```
Base: python:3.11-slim
Runtime deps: ffmpeg
User: non-root (appuser)
Working dir: /app
Exposed port: 8080
Health check: /api/v1/health
```

### Railway Deployment
```
Service: Web service
Build: Dockerfile
Workers: 4 (configurable)
Volume: /app/data (persistent)
Auto-restart: On failure
Health checks: Enabled
```

### Scaling Strategy
- **Horizontal**: Multiple Railway instances
- **Vertical**: Increase workers/memory
- **Storage**: Shared Railway volume
- **Queue**: In-memory or Redis-backed
- **Database**: Optional for persistence

---

## Performance Targets

| Metric | Target | Monitoring |
|--------|--------|------------|
| API Response Time | < 500ms (p95) | Prometheus |
| Download Success Rate | > 99% | Metrics |
| Concurrent Downloads | 10+ per instance | Queue stats |
| Storage Cleanup | Within 1 hour | Scheduler |
| Uptime | > 99.9% | Health checks |
| Queue Latency | < 5 seconds | Queue metrics |
| Error Rate | < 1% | Error logs |

---

## Testing Strategy

### Unit Tests (80%+ coverage)
- All models
- All services
- All utilities
- Edge cases
- Error conditions

### Integration Tests
- End-to-end download flows
- Playlist processing
- Batch operations
- File cleanup
- Webhook delivery

### E2E Tests
- API endpoint testing
- Authentication flows
- Rate limiting
- Error handling
- Performance testing

### Load Testing
- Concurrent requests
- Queue saturation
- Storage limits
- Memory usage
- Recovery testing

---

## Development Workflow

1. **Setup** (Day 1-2)
   - Clone repository
   - Create virtual environment
   - Install dependencies
   - Configure environment

2. **Core Development** (Week 1-2)
   - Implement models
   - Build services
   - Test components
   - Integration

3. **API Development** (Week 3)
   - Implement routes
   - Add middleware
   - Write tests
   - Documentation

4. **Deployment** (Week 4)
   - Docker setup
   - Railway deployment
   - Monitoring
   - Production testing

---

## Key Design Decisions

1. **Async-First**: All I/O operations use asyncio for better concurrency
2. **Type Safety**: Pydantic models ensure type safety throughout
3. **Stateless**: No state in application code (can scale horizontally)
4. **Queue-Based**: Background processing for long-running tasks
5. **Auto-Cleanup**: Scheduled deletion prevents storage bloat
6. **Security Layers**: Multiple security mechanisms (defense in depth)
7. **Observable**: Comprehensive logging and metrics from day one
8. **Modular**: Clean separation of concerns for maintainability

---

## Future Enhancements (Phase 2+)

### Planned Features
- [ ] User accounts and authentication
- [ ] Download history database
- [ ] Scheduled downloads
- [ ] Browser extension
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Collaborative playlists
- [ ] Social sharing
- [ ] Integration marketplace

### Infrastructure Improvements
- [ ] Redis for distributed rate limiting
- [ ] PostgreSQL for persistence
- [ ] CDN for file serving
- [ ] Load balancer for multiple instances
- [ ] Automated backups
- [ ] Blue-green deployments

---

## Success Criteria

### Technical Success
✅ All 18 API endpoints implemented
✅ All yt-dlp features supported
✅ 80%+ test coverage
✅ < 500ms API response time
✅ 99%+ download success rate
✅ Auto-cleanup working
✅ Metrics and monitoring in place
✅ Security best practices followed

### Operational Success
✅ Railway deployment successful
✅ Volume storage configured
✅ Health checks passing
✅ Logs accessible
✅ Metrics being collected
✅ Alerts configured

### Documentation Success
✅ API documentation complete (OpenAPI)
✅ Architecture documents comprehensive
✅ Implementation guide detailed
✅ Deployment guide clear
✅ Troubleshooting guide helpful

---

## Quick Reference

### Start Development
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

### Run Tests
```bash
pytest tests/ -v --cov=app
```

### Build Docker
```bash
docker build -t ultimate-downloader .
docker run -p 8080:8080 ultimate-downloader
```

### Deploy to Railway
```bash
railway login
railway up
railway domain
```

### Check Health
```bash
curl https://your-app.railway.app/api/v1/health
```

### View Metrics
```bash
curl https://your-app.railway.app/api/v1/metrics
```

### Test Download
```bash
curl -X POST https://your-app.railway.app/api/v1/download \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"url": "https://example.com/video"}'
```

---

## Support & Resources

### Documentation
- `/api/docs` - Interactive Swagger UI
- `/api/redoc` - ReDoc documentation
- `/api/openapi.json` - OpenAPI specification

### Code Organization
- `app/` - Application code
- `tests/` - Test suite
- `logs/` - Log files
- `static/` - Frontend assets

### Configuration Files
- `.env` - Environment variables
- `Dockerfile` - Container definition
- `railway.toml` - Railway configuration
- `requirements.txt` - Python dependencies

---

## Conclusion

This architecture provides a **production-ready, scalable, and secure** backend for the Ultimate Media Downloader service. It implements **all features** specified in the PRD with:

- ✅ **Complete yt-dlp integration** (all features)
- ✅ **18 RESTful API endpoints** (comprehensive coverage)
- ✅ **Background job processing** (scalable architecture)
- ✅ **Auto-cleanup system** (storage management)
- ✅ **Security best practices** (multi-layered protection)
- ✅ **Comprehensive monitoring** (metrics, logs, health)
- ✅ **Type-safe implementation** (Pydantic validation)
- ✅ **Railway deployment ready** (production configuration)

Follow the **IMPLEMENTATION_GUIDE.md** for step-by-step instructions to build this system in **4 weeks**.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Architecture Status**: Design Complete, Ready for Implementation
