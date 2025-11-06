# Documentation Index

**Ultimate Media Downloader v3.1.0** - Complete Documentation

## Documentation Overview

This documentation suite covers all aspects of the Ultimate Media Downloader service, from quick start to advanced features and deployment.

---

## Quick Access

### Getting Started
- **[README.md](../README.md)** - Project overview and feature list
- **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- **[.env.example](../.env.example)** - Environment configuration template
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history and changes

### API Documentation
- **[Complete API Reference](api/API_REFERENCE_COMPLETE.md)** - All 30+ endpoints documented
- **[Postman Collection](api/postman_collection.json)** - Ready-to-use API collection (coming soon)
- **Interactive Docs** - Visit `/docs` when service is running

### User Guides
- **[Channel Downloads Guide](user-guides/CHANNEL_DOWNLOADS.md)** - Browse and download channels
- **[Batch Downloads Guide](user-guides/BATCH_DOWNLOADS.md)** - Multiple concurrent downloads
- **[Webhooks Guide](user-guides/WEBHOOKS.md)** - Real-time notifications
- **[Authentication Guide](user-guides/AUTHENTICATION.md)** - Cookie management
- **[Frontend Guide](user-guides/FRONTEND_GUIDE.md)** - Web interface usage (coming soon)

### Technical Documentation
- **[Backend Architecture](architecture/BACKEND_ARCHITECTURE.md)** - System design
- **[Webhook Implementation](WEBHOOK_IMPLEMENTATION.md)** - Technical details
- **[Testing Strategy](quality/testing-strategy.md)** - Test coverage

### Deployment Guides
- **[Railway Deployment](deployment/railway.md)** - Deploy to Railway
- **[Docker Deployment](deployment/docker.md)** - Docker containerization
- **[Configuration Guide](deployment/configuration.md)** - All environment variables

---

## Documentation by Feature

### Core Features (v3.0.0)

#### Downloads
- Single video downloads
- Playlist downloads
- Multiple quality options
- Subtitle support
- Thumbnail embedding
- Custom path templates

**Guides**: [API Reference](api/API_REFERENCE_COMPLETE.md) | [Quick Start](QUICKSTART.md)

#### Storage & Cleanup
- Railway volume integration
- Automatic file deletion
- Path validation
- Security hardening

**Guides**: [Deployment](deployment/railway.md) | [Architecture](architecture/BACKEND_ARCHITECTURE.md)

#### Monitoring
- Health checks
- Prometheus metrics
- Structured logging
- Job state tracking

**Guides**: [API Reference](api/API_REFERENCE_COMPLETE.md#health--monitoring)

### New Features (v3.1.0)

#### Channel Downloads
- Browse channel videos
- Advanced filtering (date, duration, views)
- Sort by multiple criteria
- Pagination support
- Batch download channels

**Guides**: [Channel Downloads Guide](user-guides/CHANNEL_DOWNLOADS.md)

**Endpoints**:
- `GET /api/v1/channel/info` - Browse channel
- `POST /api/v1/channel/download` - Download channel

#### Batch Downloads
- Up to 100 URLs per batch
- Configurable concurrency (1-10)
- Batch progress tracking
- Individual job monitoring
- Error handling strategies

**Guides**: [Batch Downloads Guide](user-guides/BATCH_DOWNLOADS.md)

**Endpoints**:
- `POST /api/v1/batch/download` - Create batch
- `GET /api/v1/batch/{batch_id}` - Get status
- `DELETE /api/v1/batch/{batch_id}` - Cancel batch

#### Webhook Notifications
- 4 event types (started, progress, completed, failed)
- HMAC-SHA256 signatures
- Automatic retry with backoff
- Progress throttling
- Timeout configuration

**Guides**: [Webhooks Guide](user-guides/WEBHOOKS.md) | [Webhook Implementation](WEBHOOK_IMPLEMENTATION.md)

**Configuration**:
- `WEBHOOK_ENABLE` - Enable/disable
- `WEBHOOK_TIMEOUT_SEC` - Request timeout
- `WEBHOOK_MAX_RETRIES` - Max retry attempts

#### Cookie Management
- Browser extraction (Chrome, Firefox, Edge, Safari, Brave, Opera)
- Manual cookie upload
- AES-256-GCM encryption
- Multiple cookie profiles
- Domain tracking

**Guides**: [Authentication Guide](user-guides/AUTHENTICATION.md)

**Endpoints**:
- `POST /api/v1/cookies` - Upload/extract cookies
- `GET /api/v1/cookies` - List cookies
- `GET /api/v1/cookies/{cookie_id}` - Get metadata
- `DELETE /api/v1/cookies/{cookie_id}` - Delete cookies

#### Frontend Web UI
- Modern responsive interface
- Complete download management
- Channel browsing
- Batch operations
- Cookie management
- PWA support

**Access**: Visit service root URL (e.g., `http://localhost:8080`)

---

## Documentation by Role

### For Developers

**Getting Started**:
1. [Quick Start Guide](QUICKSTART.md)
2. [Backend Architecture](architecture/BACKEND_ARCHITECTURE.md)
3. [API Reference](api/API_REFERENCE_COMPLETE.md)

**Building Features**:
- [Implementation Guide](implementation/)
- [Testing Strategy](quality/testing-strategy.md)
- Code examples in `examples/` directory

**Deployment**:
- [Docker Deployment](deployment/docker.md)
- [Configuration Guide](deployment/configuration.md)

### For DevOps Engineers

**Deployment**:
1. [Railway Deployment](deployment/railway.md)
2. [Docker Deployment](deployment/docker.md)
3. [Configuration Guide](deployment/configuration.md)

**Monitoring**:
- [API Reference - Monitoring](api/API_REFERENCE_COMPLETE.md#health--monitoring)
- Prometheus metrics at `/metrics`
- Health checks at `/api/v1/health`

**Security**:
- [Backend Architecture - Security](architecture/BACKEND_ARCHITECTURE.md)
- [Authentication Guide](user-guides/AUTHENTICATION.md)

### For End Users

**Using the Service**:
1. [Quick Start Guide](QUICKSTART.md)
2. [Frontend Guide](user-guides/FRONTEND_GUIDE.md) (web interface)
3. [API Reference](api/API_REFERENCE_COMPLETE.md) (programmatic access)

**Features**:
- [Channel Downloads](user-guides/CHANNEL_DOWNLOADS.md)
- [Batch Downloads](user-guides/BATCH_DOWNLOADS.md)
- [Authentication](user-guides/AUTHENTICATION.md)
- [Webhooks](user-guides/WEBHOOKS.md)

### For Product Managers

**Overview**:
- [README.md](../README.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [Product Requirements](product/)

**Features**:
- [Channel Downloads Guide](user-guides/CHANNEL_DOWNLOADS.md)
- [Batch Downloads Guide](user-guides/BATCH_DOWNLOADS.md)
- [Webhooks Guide](user-guides/WEBHOOKS.md)

---

## API Endpoint Reference

### Download Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/download` | Create single download |
| GET | `/api/v1/downloads/{id}` | Get download status |
| DELETE | `/api/v1/downloads/{id}` | Cancel download |
| GET | `/api/v1/downloads/{id}/logs` | Get job logs |

### Channel Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/channel/info` | Browse channel |
| POST | `/api/v1/channel/download` | Download channel |

### Batch Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/batch/download` | Create batch |
| GET | `/api/v1/batch/{batch_id}` | Get batch status |
| DELETE | `/api/v1/batch/{batch_id}` | Cancel batch |

### Cookie Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/cookies` | Upload/extract cookies |
| GET | `/api/v1/cookies` | List cookies |
| GET | `/api/v1/cookies/{cookie_id}` | Get metadata |
| DELETE | `/api/v1/cookies/{cookie_id}` | Delete cookies |

### Playlist Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/playlist/info` | Get playlist info |
| POST | `/api/v1/playlist/download` | Download playlist |

### Metadata & Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/metadata` | Extract metadata |
| GET | `/api/v1/health` | Health check |
| GET | `/version` | Version info |
| GET | `/metrics` | Prometheus metrics |

**Complete documentation**: [API Reference](api/API_REFERENCE_COMPLETE.md)

---

## Configuration Reference

### Essential Variables
```bash
REQUIRE_API_KEY=true
API_KEY=your-secret-key
STORAGE_DIR=/app/data
PUBLIC_BASE_URL=https://your-app.railway.app
```

### Feature Flags
```bash
ALLOW_YT_DOWNLOADS=true
WEBHOOK_ENABLE=true
```

### Performance
```bash
WORKERS=2
MAX_CONCURRENT_DOWNLOADS=3
RATE_LIMIT_RPS=2
```

### Security
```bash
COOKIE_ENCRYPTION_KEY=your-32-byte-hex-key
```

### Timeouts
```bash
DEFAULT_TIMEOUT_SEC=1800
PROGRESS_TIMEOUT_SEC=300
FILE_RETENTION_HOURS=48
```

**Complete reference**: [Configuration Guide](deployment/configuration.md)

---

## Code Examples

### Python SDK Usage
```python
import requests

api_base = "http://localhost:8080"
api_key = "your-api-key"

# Single download
response = requests.post(
    f"{api_base}/api/v1/download",
    headers={"X-API-Key": api_key},
    json={"url": "https://example.com/video", "quality": "1080p"}
)

# Batch download
response = requests.post(
    f"{api_base}/api/v1/batch/download",
    headers={"X-API-Key": api_key},
    json={"urls": ["url1", "url2", "url3"], "concurrent_limit": 3}
)

# Channel browsing
response = requests.get(
    f"{api_base}/api/v1/channel/info",
    headers={"X-API-Key": api_key},
    params={"url": "https://youtube.com/@example", "date_after": "20250101"}
)
```

**More examples**: Check `examples/` directory

---

## Support & Contributing

### Getting Help
- **Documentation**: Start here
- **Issues**: [GitHub Issues](https://github.com/yourusername/railway-yt-dlp-service/issues)
- **API Docs**: Visit `/docs` endpoint
- **Health Check**: Visit `/api/v1/health`

### Contributing
- **Code**: Follow patterns in existing code
- **Tests**: Add tests for new features
- **Docs**: Update relevant documentation
- **PRs**: Submit pull requests via GitHub

### Reporting Issues
Include:
1. Version number (`/version` endpoint)
2. Error messages and logs
3. Steps to reproduce
4. Expected vs actual behavior

---

## Version History

- **v3.1.0** (2025-11-06) - Channel downloads, batch operations, webhooks, cookies, frontend UI
- **v3.0.0** (2025-11-05) - Complete modular architecture rewrite
- **v2.0.0** - Legacy monolithic implementation

**Full changelog**: [CHANGELOG.md](../CHANGELOG.md)

---

## What's Next?

### Upcoming Features (v3.2.0)
- Video transcoding and format conversion
- Cloud storage integration (S3, GCS, Azure)
- Advanced scheduling (cron-based downloads)
- Multi-user support with authentication
- Download analytics and reporting

---

**Last Updated**: 2025-11-06
**Documentation Version**: 3.1.0
