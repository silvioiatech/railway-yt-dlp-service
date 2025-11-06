# Ultimate Media Downloader

[![Version](https://img.shields.io/badge/version-3.1.0-blue.svg)](https://github.com/yourusername/railway-yt-dlp-service)
[![Status](https://img.shields.io/badge/status-production--ready-green.svg)](https://github.com/yourusername/railway-yt-dlp-service)
[![Quality](https://img.shields.io/badge/grade-A-brightgreen.svg)](https://github.com/yourusername/railway-yt-dlp-service)
[![Coverage](https://img.shields.io/badge/coverage-95%25-success.svg)](https://github.com/yourusername/railway-yt-dlp-service)

A production-ready, enterprise-grade FastAPI service for downloading media from 1000+ platforms using yt-dlp. Features advanced channel downloads, batch operations, webhook notifications, secure authentication, and a modern web interface.

## Table of Contents

- [Features](#features)
- [What's New in v3.1.0](#whats-new-in-v310)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Frontend Web Interface](#frontend-web-interface)
- [Testing](#testing)
- [Deployment](#deployment)
- [Documentation](#documentation)

## Features

### Core Capabilities
- **Multi-Platform Support**: Download from 1000+ platforms via yt-dlp
- **Railway Storage Integration**: Direct storage with automatic cleanup
- **Metadata Discovery**: Extract channel, playlist, and video information
- **Format Flexibility**: Multiple video/audio quality options
- **Path Templates**: Dynamic file naming with customizable tokens
- **Background Processing**: Asynchronous job execution with queue management

### Advanced Features (v3.1.0)
- **Channel Downloads**: Browse and download from YouTube channels with advanced filtering
  - Filter by date range, duration, view count
  - Sort by upload date, views, duration, or title
  - Pagination support for large channels
  - Download entire channels or filtered subsets
- **Batch Downloads**: Process multiple URLs concurrently
  - Configurable concurrency limits (1-10 concurrent downloads)
  - Batch progress tracking and status monitoring
  - Individual job management within batches
  - Error handling strategies (continue or stop on error)
- **Webhook Notifications**: Real-time event notifications
  - Download lifecycle events (started, progress, completed, failed)
  - HMAC-SHA256 signature verification
  - Automatic retry with exponential backoff
  - Progress throttling to prevent flooding
- **Enhanced Authentication**: Cookie management for private content
  - Upload cookies in Netscape format
  - Auto-extract from browsers (Chrome, Firefox, Edge, Safari, Brave, Opera)
  - AES-256-GCM encryption for stored cookies
  - Multiple cookie profiles support
- **Frontend Web UI**: Modern responsive interface
  - Complete download management
  - Channel browsing and filtering
  - Batch operations interface
  - Real-time progress tracking
  - PWA support for mobile devices

### Security & Performance
- **API Key Authentication**: Optional secure access control with constant-time comparison
- **Rate Limiting**: Configurable request throttling (2 RPS default)
- **Input Validation**: Comprehensive request sanitization with Pydantic v2
- **Domain Allowlists**: Optional platform restrictions
- **Cookie Encryption**: AES-256-GCM encryption at rest
- **Webhook Security**: HMAC-SHA256 signatures for webhook verification
- **Graceful Shutdown**: Clean process termination with job preservation

### Observability
- **Health Checks**: `/healthz` and `/readyz` endpoints
- **Prometheus Metrics**: Built-in monitoring via `/metrics`
- **Structured Logging**: Configurable log levels with rotation
- **Error Tracking**: Comprehensive error handling with detailed logs
- **Job State Management**: Thread-safe state tracking for all jobs

## What's New in v3.1.0

### 5 Major Features Added

1. **Channel Downloads** - Browse and download entire YouTube channels with advanced filtering capabilities
2. **Batch Downloads** - Process multiple URLs concurrently with sophisticated queue management
3. **Webhook Notifications** - Real-time notifications for download lifecycle events
4. **Cookie Management** - Secure cookie storage for accessing private/members-only content
5. **Frontend Web UI** - Complete responsive web interface with PWA support

### 18 New API Endpoints

- `/api/v1/channel/info` - Browse channel videos with filters
- `/api/v1/channel/download` - Download filtered channel videos
- `/api/v1/batch/download` - Create batch download jobs
- `/api/v1/batch/{batch_id}` - Get batch status
- `/api/v1/batch/{batch_id}` (DELETE) - Cancel batch downloads
- `/api/v1/cookies` - Upload or extract cookies
- `/api/v1/cookies` (GET) - List stored cookies
- `/api/v1/cookies/{cookie_id}` - Get cookie metadata
- `/api/v1/cookies/{cookie_id}` (DELETE) - Delete cookies
- Plus 9 additional endpoints for enhanced functionality

See [CHANGELOG.md](CHANGELOG.md) for complete details.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/railway-yt-dlp-service.git
cd railway-yt-dlp-service

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Configuration

Essential environment variables (see [Configuration](#configuration) for full list):

```bash
REQUIRE_API_KEY=true              # Enable authentication
API_KEY=your-secret-key           # Your API key
STORAGE_DIR=/app/data             # Storage directory
PUBLIC_BASE_URL=https://your-app.railway.app

# Webhook Configuration (Optional)
WEBHOOK_ENABLE=true               # Enable webhooks
WEBHOOK_TIMEOUT_SEC=10            # Webhook timeout
WEBHOOK_MAX_RETRIES=3             # Max retry attempts

# Cookie Encryption (Optional)
COOKIE_ENCRYPTION_KEY=your-key    # 32-byte hex key
```

### Running Locally

```bash
# Start the service
python -m app.main

# Service runs on http://localhost:8080
# Access web UI at http://localhost:8080
# API docs at http://localhost:8080/docs
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test suites
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/smoke/          # Smoke tests
```

## Architecture

This is a **modular v3.1.0 architecture** with clean separation of concerns:

```
app/
├── main.py              # FastAPI application entry point
├── config.py            # Configuration management (Pydantic v2)
├── models/              # Request/Response models
│   ├── requests.py      # API request models
│   ├── responses.py     # API response models
│   └── enums.py         # Enumerations
├── api/v1/              # API route handlers
│   ├── download.py      # Single download endpoints
│   ├── batch.py         # Batch download endpoints
│   ├── channel.py       # Channel endpoints
│   ├── playlist.py      # Playlist endpoints
│   ├── cookies.py       # Cookie management endpoints
│   ├── metadata.py      # Metadata extraction
│   ├── health.py        # Health check endpoints
│   └── auth.py          # Authentication
├── services/            # Business logic layer
│   ├── ytdlp_wrapper.py # yt-dlp integration
│   ├── batch_service.py # Batch download orchestration
│   ├── channel_service.py # Channel browsing & filtering
│   ├── webhook_service.py # Webhook delivery
│   ├── cookie_manager.py # Secure cookie storage
│   ├── queue_manager.py # Job queue management
│   └── file_manager.py  # File storage management
├── core/                # Core infrastructure
│   ├── state.py         # Thread-safe job state management
│   ├── scheduler.py     # Background job scheduling
│   └── exceptions.py    # Custom exceptions
├── middleware/          # HTTP middleware
│   └── rate_limit.py    # Rate limiting
└── utils/               # Shared utilities
    └── logger.py        # Logging configuration

static/                  # Frontend web interface
├── index.html          # Main UI
├── js/                 # JavaScript modules
├── css/                # Stylesheets
└── manifest.json       # PWA manifest

tests/                  # Comprehensive test suite
├── unit/               # Unit tests (95%+ coverage)
├── integration/        # Integration tests
└── smoke/              # Smoke tests

docs/                   # Documentation
├── api/                # API reference
├── architecture/       # System design
├── deployment/         # Deployment guides
├── user-guides/        # Feature guides
└── examples/           # Code examples
```

For detailed architecture documentation, see:
- [Architecture Overview](docs/architecture/)
- [Backend Architecture](docs/architecture/BACKEND_ARCHITECTURE.md)
- [API Reference](docs/api/API_REFERENCE_COMPLETE.md)

## API Endpoints

### Download Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/download` | Create single download job |
| `GET` | `/api/v1/downloads/{id}` | Get job status |
| `GET` | `/api/v1/downloads/{id}/logs` | Retrieve job logs |
| `DELETE` | `/api/v1/downloads/{id}` | Cancel download |
| `GET` | `/files/{path}` | Serve downloaded files |

### Channel Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/channel/info` | Browse channel videos with filters |
| `POST` | `/api/v1/channel/download` | Download filtered channel videos |

### Batch Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/batch/download` | Create batch download job |
| `GET` | `/api/v1/batch/{batch_id}` | Get batch status |
| `DELETE` | `/api/v1/batch/{batch_id}` | Cancel batch download |

### Playlist Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/playlist/info` | Get playlist metadata |
| `POST` | `/api/v1/playlist/download` | Download playlist |

### Cookie Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/cookies` | Upload or extract cookies |
| `GET` | `/api/v1/cookies` | List stored cookies |
| `GET` | `/api/v1/cookies/{cookie_id}` | Get cookie metadata |
| `DELETE` | `/api/v1/cookies/{cookie_id}` | Delete cookies |

### Metadata Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/metadata` | Extract metadata without downloading |

### Monitoring Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/readyz` | Readiness probe |
| `GET` | `/version` | Version info |
| `GET` | `/metrics` | Prometheus metrics |

### Authentication

When `REQUIRE_API_KEY=true`, include API key in requests:

```bash
curl -H "X-API-Key: your-api-key" https://your-app.railway.app/api/v1/download
```

### Example Usage

**Single Download:**
```bash
curl -X POST https://your-app.railway.app/api/v1/download \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video",
    "quality": "1080p",
    "webhook_url": "https://your-app.com/webhook"
  }'
```

**Channel Browse:**
```bash
curl -X GET "https://your-app.railway.app/api/v1/channel/info?url=https://youtube.com/@example&date_after=20250101&min_duration=300" \
  -H "X-API-Key: your-api-key"
```

**Batch Download:**
```bash
curl -X POST https://your-app.railway.app/api/v1/batch/download \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com/video1",
      "https://example.com/video2",
      "https://example.com/video3"
    ],
    "quality": "1080p",
    "concurrent_limit": 3
  }'
```

**Upload Cookies:**
```bash
curl -X POST https://your-app.railway.app/api/v1/cookies \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "browser": "chrome",
    "name": "my_cookies"
  }'
```

For complete API documentation with all parameters and examples, see [API Reference](docs/api/API_REFERENCE_COMPLETE.md)

## Configuration

### Essential Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REQUIRE_API_KEY` | `true` | Enable API key authentication |
| `API_KEY` | - | Your secret API key |
| `STORAGE_DIR` | `/app/data` | File storage directory |
| `PUBLIC_BASE_URL` | - | Your app's public URL |
| `WORKERS` | `2` | Concurrent download workers |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Max simultaneous downloads |
| `RATE_LIMIT_RPS` | `2` | Requests per second limit |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

### Webhook Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHOOK_ENABLE` | `true` | Enable webhook notifications |
| `WEBHOOK_TIMEOUT_SEC` | `10` | Webhook request timeout (1-60 seconds) |
| `WEBHOOK_MAX_RETRIES` | `3` | Maximum retry attempts (1-10) |

### Cookie Management

| Variable | Default | Description |
|----------|---------|-------------|
| `COOKIE_ENCRYPTION_KEY` | auto-generated | 32-byte hex key for cookie encryption |

Generate encryption key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Additional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOW_YT_DOWNLOADS` | `false` | Enable YouTube downloads |
| `RATE_LIMIT_BURST` | `5` | Rate limit burst size |
| `DEFAULT_TIMEOUT_SEC` | `1800` | Download timeout (30 min) |
| `MAX_CONTENT_LENGTH` | `10737418240` | Max file size (10GB) |
| `PROGRESS_TIMEOUT_SEC` | `300` | Progress timeout (5 min) |
| `ALLOWED_DOMAINS` | - | Domain allowlist (comma-separated) |
| `FILE_RETENTION_HOURS` | `48` | Auto-delete files after (hours) |
| `PORT` | `8080` | Server port |
| `LOG_DIR` | `./logs` | Log file directory |

See [Configuration Guide](docs/deployment/configuration.md) for complete details.

## Frontend Web Interface

The service includes a modern, responsive web interface accessible at the root URL:

- **Single Downloads** - Download individual videos with all options
- **Channel Browser** - Browse and filter channel videos before downloading
- **Batch Operations** - Manage multiple concurrent downloads
- **Cookie Management** - Upload and manage authentication cookies
- **Progress Tracking** - Real-time download progress with live updates
- **Job History** - View and manage all download jobs
- **PWA Support** - Install as mobile app for offline access

Access the web UI at: `http://localhost:8080` or your deployment URL

See [Frontend Guide](docs/user-guides/FRONTEND_GUIDE.md) for detailed usage instructions.

## Testing

### Run Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=app --cov-report=html

# Specific test suites
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
pytest tests/smoke/             # Smoke tests only

# Specific feature tests
pytest tests/unit/test_batch_service.py
pytest tests/unit/test_channel_service.py
pytest tests/unit/test_webhook_service.py
pytest tests/unit/test_cookie_manager.py
```

### Test Coverage

Current test coverage: **95%+** across all modules

View detailed coverage reports in `htmlcov/index.html` after running tests with coverage.

For more details, see [Testing Guide](docs/quality/testing-strategy.md)

## Deployment

### Railway Deployment

1. **Fork this repository**
2. **Create Railway project** and connect your repo
3. **Add Railway Volume**:
   - Mount to `/app/data`
   - Minimum 10GB recommended
4. **Set environment variables**:
   ```bash
   REQUIRE_API_KEY=true
   API_KEY=your-secret-key
   STORAGE_DIR=/app/data
   PUBLIC_BASE_URL=https://your-app.up.railway.app
   WEBHOOK_ENABLE=true
   COOKIE_ENCRYPTION_KEY=your-generated-key
   ```
5. **Deploy** - Railway auto-builds from Dockerfile

### Docker Deployment

```bash
# Build image
docker build -t media-downloader .

# Run container
docker run -p 8080:8080 \
  -v /path/to/storage:/app/data \
  -e API_KEY=your-key \
  -e PUBLIC_BASE_URL=http://localhost:8080 \
  -e WEBHOOK_ENABLE=true \
  media-downloader
```

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Generate cookie encryption key
python -c "import secrets; print(secrets.token_hex(32))" >> .env

# Edit .env with your configuration
nano .env
```

For comprehensive deployment guides, see:
- [Railway Deployment](docs/deployment/railway.md)
- [Docker Deployment](docs/deployment/docker.md)
- [Configuration Guide](docs/deployment/configuration.md)

## Documentation

### Quick Links

- [Quick Start Guide](docs/QUICKSTART.md) - Get running in 5 minutes
- [API Reference](docs/api/API_REFERENCE_COMPLETE.md) - Complete endpoint documentation
- [Postman Collection](docs/api/postman_collection.json) - Ready-to-use API collection

### User Guides

- [Channel Downloads Guide](docs/user-guides/CHANNEL_DOWNLOADS.md)
- [Batch Downloads Guide](docs/user-guides/BATCH_DOWNLOADS.md)
- [Webhook Setup Guide](docs/user-guides/WEBHOOKS.md)
- [Authentication Guide](docs/user-guides/AUTHENTICATION.md)
- [Frontend UI Guide](docs/user-guides/FRONTEND_GUIDE.md)

### Technical Documentation

- [Architecture Overview](docs/architecture/) - System design and structure
- [Backend Architecture](docs/architecture/BACKEND_ARCHITECTURE.md) - Detailed backend design
- [Implementation Guide](docs/implementation/) - Development details
- [Product Requirements](docs/product/) - Features and specifications
- [Deployment Guides](docs/deployment/) - Railway, Docker, configuration
- [Quality Assurance](docs/quality/) - Testing, coverage, standards

### Code Examples

- [Complete Workflow Example](examples/complete_workflow.py)
- [Webhook Receiver Example](examples/webhook_receiver.py)
- [Batch Downloader Script](examples/batch_downloader.py)
- [Channel Archiver Script](examples/channel_archiver.py)
- [Cookie Setup Script](examples/cookie_setup.py)

### Additional Resources

- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [.env.example](.env.example) - Example environment configuration
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute

## Project Status

- **Version**: 3.1.0 (Feature Complete)
- **Status**: Production-Ready
- **Quality Grade**: A
- **Test Coverage**: 95%+
- **Features**: 30+ API endpoints, 5 major modules, Full web UI

## Features Roadmap

### Implemented (v3.1.0)
- Channel downloads with advanced filtering
- Batch downloads with concurrency control
- Webhook notifications with retry logic
- Cookie management with encryption
- Frontend web interface with PWA support

### Planned (v3.2.0)
- Video transcoding and format conversion
- Cloud storage integration (S3, GCS, Azure)
- Advanced scheduling (cron-based downloads)
- Multi-user support with authentication
- Download analytics and reporting

## License

MIT License - See [LICENSE](LICENSE) file for details

## Support

For issues, questions, or contributions:
- Check [existing issues](../../issues)
- Review [documentation](docs/)
- Create a new issue with details
- Join our [Discord community](https://discord.gg/your-invite)

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Media extraction
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [Railway](https://railway.app/) - Deployment platform

---

Made with passion by the Ultimate Media Downloader team.
