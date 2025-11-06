# Startup Guide - Ultimate Media Downloader

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file or set environment variables:

```bash
# Required if REQUIRE_API_KEY=true (default)
API_KEY=your-secure-api-key-here

# Optional configurations
STORAGE_DIR=/tmp/railway-downloads
LOG_LEVEL=INFO
WORKERS=2
RATE_LIMIT_RPS=2
ALLOW_YT_DOWNLOADS=false
```

### 3. Run the Application

**Using Uvicorn directly:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

**With auto-reload for development:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

**Production with multiple workers:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4
```

## Application Structure

### Main Entry Point
- **app/main.py** - FastAPI application with lifespan management
  - Startup: Queue manager, scheduler, logging, directory validation
  - Shutdown: Graceful cleanup of all resources
  - Middleware: CORS, rate limiting, GZip compression
  - Error handlers for all exception types

### Rate Limiting
- **app/middleware/rate_limit.py** - Slowapi-based rate limiting
  - Per-API-key or per-IP limiting
  - Configurable limits via environment variables
  - Custom error responses with Retry-After headers

### API Routes
- **app/api/v1/router.py** - Main API router combining all endpoints
  - `/api/v1/health` - Health check
  - `/api/v1/download` - Download management
  - `/api/v1/metadata` - Metadata extraction
  - `/api/v1/playlist` - Playlist handling

### Core Services
- **app/services/queue_manager.py** - Background job queue with ThreadPoolExecutor
- **app/core/scheduler.py** - File deletion scheduler with cancellation
- **app/config.py** - Centralized configuration with Pydantic

## Endpoints

### API Documentation
- **GET /** - Service information or frontend (if static files exist)
- **GET /docs** - Swagger UI documentation (unless DISABLE_DOCS=true)
- **GET /redoc** - ReDoc documentation
- **GET /metrics** - Prometheus metrics

### System Endpoints
- **GET /api/v1/health** - Health check with component status
- **GET /api/v1/health/ready** - Readiness probe for orchestration
- **GET /version** - Service version information

### File Serving
- **GET /files/{path}** - Serve downloaded files with security checks
- **GET /static/{path}** - Serve static frontend files

## Configuration Options

### Core Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | "Ultimate Media Downloader" | Application name |
| `VERSION` | "3.0.0" | Version |
| `DEBUG` | false | Debug mode |
| `LOG_LEVEL` | "INFO" | Logging level |

### Server
| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | "0.0.0.0" | Server host |
| `PORT` | 8080 | Server port |
| `WORKERS` | 2 | Worker processes |

### Authentication
| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | "" | API authentication key (required if REQUIRE_API_KEY=true) |
| `REQUIRE_API_KEY` | true | Enforce API key authentication |

### Storage
| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_DIR` | "/tmp/railway-downloads" | Root directory for downloads |
| `FILE_RETENTION_HOURS` | 1.0 | Hours to retain files before deletion |
| `PUBLIC_BASE_URL` | "" | Public base URL for file serving |

### Downloads
| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENT_DOWNLOADS` | 10 | Maximum concurrent downloads |
| `DEFAULT_TIMEOUT_SEC` | 1800 | Default download timeout |
| `PROGRESS_TIMEOUT_SEC` | 300 | No-progress timeout |
| `MAX_CONTENT_LENGTH` | 10737418240 | Max file size (10GB) |

### Rate Limiting
| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_RPS` | 2 | Requests per second |
| `RATE_LIMIT_BURST` | 5 | Burst allowance |

### Features
| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOW_YT_DOWNLOADS` | false | Allow YouTube downloads |
| `ALLOWED_DOMAINS` | [] | Domain whitelist (empty = all) |
| `CORS_ORIGINS` | ["*"] | CORS allowed origins |

### Logging
| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_DIR` | "./logs" | Directory for log files |
| `LOG_FILE_MAX_BYTES` | 10485760 | Max log file size (10MB) |
| `LOG_FILE_BACKUP_COUNT` | 5 | Number of backup log files |

## Architecture Features

### Lifespan Management
The application uses FastAPI's lifespan context manager for proper startup/shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    - Validate settings
    - Setup logging with rotation
    - Initialize queue manager (ThreadPoolExecutor)
    - Start file deletion scheduler
    - Validate directories

    yield

    # Shutdown
    - Gracefully shutdown queue manager
    - Stop file deletion scheduler
    - Wait for in-flight jobs (30s timeout)
```

### Error Handling
Three-tier exception handling:
1. **MediaDownloaderException** - Custom app exceptions with proper status codes
2. **HTTPException** - FastAPI HTTP exceptions with consistent format
3. **Exception** - Catch-all for unexpected errors with logging

### Middleware Stack (applied in order)
1. **CORS** - Cross-origin resource sharing
2. **GZip** - Response compression (min 1000 bytes)
3. **SlowAPI** - Rate limiting with custom error handler

### Metrics
Prometheus metrics available at `/metrics`:
- `jobs_total{status}` - Counter: Total jobs by status
- `jobs_duration_seconds` - Histogram: Job duration
- `bytes_transferred_total` - Counter: Total bytes transferred
- `jobs_in_flight` - Gauge: Currently running jobs
- `queue_size` - Gauge: Current queue size

### Static File Serving
If `STATIC_DIR` exists and contains files:
- Frontend served at `/` (index.html)
- Static assets at `/static/*`
- Falls back to API info if no frontend

### Security Features
- Constant-time API key comparison (prevents timing attacks)
- Path traversal prevention for file serving
- Directory boundary validation
- Configurable CORS origins
- Rate limiting per API key or IP

## Development

### Run with Auto-Reload
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Environment Variables
Create `.env` file:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
REQUIRE_API_KEY=false  # Disable auth for development
ALLOW_YT_DOWNLOADS=true  # Enable YouTube if needed
```

### View Logs
```bash
tail -f logs/app.log
```

## Production Deployment

### Railway
The application is configured for Railway deployment:
```bash
# Railway will automatically use PORT environment variable
# Set your secrets in Railway dashboard:
- API_KEY
- PUBLIC_BASE_URL
- STORAGE_DIR (use Railway volume mount)
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Health Checks
- **Liveness**: `GET /api/v1/health` - Returns 200 if app is running
- **Readiness**: `GET /api/v1/health/ready` - Returns 200 if accepting requests

## Troubleshooting

### Import Errors
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Verify Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/railway-yt-dlp-service"
```

### Permission Errors
```bash
# Ensure storage and log directories are writable
chmod -R 755 /tmp/railway-downloads
chmod -R 755 ./logs
```

### Rate Limiting Issues
```bash
# Increase rate limits in .env
RATE_LIMIT_RPS=10
RATE_LIMIT_BURST=20
```

### Queue Full Errors
```bash
# Increase concurrent download limit
MAX_CONCURRENT_DOWNLOADS=20
WORKERS=4
```

## Testing the Application

### 1. Check Health
```bash
curl http://localhost:8080/api/v1/health
```

### 2. Download a File (with API key)
```bash
curl -X POST http://localhost:8080/api/v1/download \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "url": "https://example.com/video.mp4",
    "path": "videos/{safe_title}.{ext}"
  }'
```

### 3. Check Job Status
```bash
curl http://localhost:8080/api/v1/download/{request_id}
```

### 4. View Metrics
```bash
curl http://localhost:8080/metrics
```

## Migration from app.py

The new structure (`app/main.py`) is a drop-in replacement for the old `app.py`:

### Key Differences
1. **Modular structure** - Separated concerns into modules
2. **Type safety** - Full type hints and Pydantic validation
3. **Better logging** - Rotating file handlers, structured logging
4. **Enhanced error handling** - Custom exception hierarchy
5. **Dependency injection** - FastAPI dependencies for cleaner code
6. **Better testing** - Separated components for easier unit testing

### Migration Steps
1. Update imports: `from app.main import app`
2. Environment variables remain the same
3. API endpoints unchanged (backward compatible)
4. Consider updating `Procfile` or deployment config to use `app.main:app`

## Support

For issues or questions:
- Check logs in `./logs/app.log`
- Review API docs at `/docs`
- Check health endpoint for component status
- Review environment variable configuration
