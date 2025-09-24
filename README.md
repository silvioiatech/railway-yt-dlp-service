# Railway yt-dlp Service

A production-ready FastAPI service for downloading media from various platforms using yt-dlp, with Railway storage integration and intelligent file management.

## Features

### Core Functionality
- **Media Download**: Download videos/audio from 1000+ platforms using yt-dlp
- **Railway Storage**: Direct file storage on Railway with automatic cleanup
- **Auto-Deletion**: Files automatically deleted after 1 hour (configurable)
- **Metadata Discovery**: Extract information from channels, playlists, and videos
- **Multiple Formats**: Support for various video/audio quality options
- **Path Templates**: Customizable file paths with dynamic tokens

### Security & Performance
- **API Key Authentication**: Secure access control
- **Rate Limiting**: Configurable request rate limits
- **Input Validation**: Comprehensive request validation
- **Background Processing**: Asynchronous download jobs
- **Centralized Scheduler**: Efficient file deletion management
- **Domain Allowlists**: Optional domain restrictions

### Production Ready
- **Health Checks**: Comprehensive health monitoring
- **Prometheus Metrics**: Built-in observability
- **Structured Logging**: Detailed logging with configurable levels
- **Graceful Shutdown**: Clean process termination
- **Error Handling**: Robust error recovery

## Quick Start

### 1. Railway Deployment (Recommended)

1. **Fork/Clone** this repository
2. **Create Railway Project** and connect your repository
3. **Add Railway Volume**:
   - Go to Railway dashboard → Your project → Storage
   - Create a new Volume and mount it to `/app/data`
4. **Set Environment Variables**:
   - `API_KEY`: Generate a secure API key
   - `STORAGE_DIR`: Set to `/app/data` (or your volume mount path)
   - `PUBLIC_BASE_URL`: Set to your Railway app URL
5. **Deploy**: Railway will automatically build and deploy

### 2. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run the service
python app.py
```

The service will start on `http://localhost:8080`

## API Reference

### Authentication

All API endpoints require authentication via the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-api-key-here" ...
```

### Endpoints

#### POST /download

Create a new download job.

**Request:**
```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "format": "best",
  "path": "videos/{safe_title}-{id}.{ext}",
  "webhook": "https://your-app.com/webhook",
  "timeout_sec": 1800
}
```

**Response:**
```json
{
  "status": "QUEUED",
  "request_id": "12345678-1234-5678-9abc-123456789abc",
  "logs_url": "https://your-app.railway.app/downloads/12345678.../logs",
  "created_at": "2025-09-24T12:00:00Z"
}
```

#### GET /downloads/{request_id}

Get download job status.

**Response:**
```json
{
  "status": "DONE",
  "request_id": "12345678-1234-5678-9abc-123456789abc",
  "file_url": "https://your-app.railway.app/files/videos/video-abc123.mp4",
  "bytes": 104857600,
  "duration_sec": 45.2,
  "logs_url": "https://your-app.railway.app/downloads/12345678.../logs",
  "created_at": "2025-09-24T12:00:00Z",
  "completed_at": "2025-09-24T12:01:30Z",
  "deletion_time": "2025-09-24T13:01:30Z"
}
```

#### GET /downloads/{request_id}/logs

Retrieve detailed logs for a download job.

**Response:**
```json
{
  "request_id": "12345678-1234-5678-9abc-123456789abc",
  "logs": [
    "[2025-09-24T12:00:00Z] INFO: Starting download: https://www.example.com/video",
    "[2025-09-24T12:01:30Z] INFO: Download completed successfully. Bytes: 104857600"
  ],
  "status": "DONE",
  "log_count": 2
}
```

#### GET /files/{path:path}

Serve downloaded files securely.

**Example:**
```bash
curl https://your-app.railway.app/files/videos/example-abc123.mp4 -o video.mp4
```

#### GET /discover

Enhanced metadata discovery without downloading content.

**Query Parameters:**
- `sources` (required): Comma-separated URLs to discover (max 10 sources)
- `format` (required): Output format - csv, json, or ndjson
- `limit` (optional): Limit per source, 1-1000 (default: 100)
- `min_views` (optional): Minimum view count filter
- `min_duration` (optional): Minimum duration in seconds (1-86400)
- `max_duration` (optional): Maximum duration in seconds (1-86400)
- `dateafter` (optional): Date filter - YYYYMMDD or now-<days>days format
- `match_filter` (optional): Raw yt-dlp match filter expression
- `fields` (optional): CSV field list (default: id,title,url,duration,view_count,like_count,uploader,upload_date)

**Sample Request:**
```
GET /discover?sources=https://youtube.com/playlist?list=EXAMPLE&format=json&limit=5&min_duration=60
```

**Sample Response (JSON):**
```json
[
  {
    "id": "abc123",
    "title": "Sample Video", 
    "url": "https://youtube.com/watch?v=abc123",
    "duration": 120,
    "view_count": 1500,
    "uploader": "Creator",
    "upload_date": "20231201"
  }
]
```

#### GET /healthz

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "timestamp": "2025-09-24T12:00:00Z",
  "checks": {
    "executor": "healthy",
    "storage": "healthy",
    "yt_dlp": "healthy"
  }
}
```

#### GET /readyz

Readiness probe for orchestration platforms.

#### GET /version

Version information.

#### GET /metrics

Prometheus metrics endpoint.

## Path Templates

Customize object storage paths using these tokens:

- `{id}`: Video ID
- `{title}`: Full title
- `{safe_title}`: Sanitized title (filesystem safe)
- `{ext}`: File extension (e.g., mp4)
- `{uploader}`: Uploader name
- `{date}`: Upload date (YYYY-MM-DD)
- `{random}`: Random hex string

**Examples:**
- `videos/{safe_title}-{id}.{ext}` → `videos/My_Video-abc123.mp4`
- `{date}/{uploader}/{id}.{ext}` → `2025-09-24/Creator/abc123.mp4`

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | Yes | - | Secret API key for authentication |
| `ALLOW_YT_DOWNLOADS` | No | `false` | Enable/disable YouTube downloads (ToS compliance) |
| `STORAGE_DIR` | Yes | `/app/data` | Directory for storing downloaded files |
| `PUBLIC_BASE_URL` | Yes | - | Public URL of your Railway app |
| `WORKERS` | No | `2` | Number of concurrent download workers |
| `RATE_LIMIT_RPS` | No | `2` | Rate limit requests per second |
| `RATE_LIMIT_BURST` | No | `5` | Rate limit burst size |
| `DEFAULT_TIMEOUT_SEC` | No | `1800` | Default download timeout in seconds |
| `MAX_CONTENT_LENGTH` | No | `10737418240` | Maximum file size (10GB) |
| `PROGRESS_TIMEOUT_SEC` | No | `300` | Progress timeout (abort if no progress) |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ALLOWED_DOMAINS` | No | - | Comma-separated allowlist of domains |
| `PORT` | No | `8080` | Server port |
| `LOG_DIR` | No | `./logs` | Directory for log files |

## Usage Examples

### Basic Video Download

```bash
curl -X POST https://your-app.railway.app/download \
  -H "X-API-Key: your-secret-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "best",
    "path": "{safe_title}-{id}.{ext}"
  }'
```

### Audio Only Download

```bash
curl -X POST https://your-app.railway.app/download \
  -H "X-API-Key: your-secret-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "bestaudio",
    "path": "audio/{safe_title}-{id}.{ext}"
  }'
```

### Check Status and Download

```bash
# Start download
RESPONSE=$(curl -X POST https://your-app.railway.app/download \
  -H "X-API-Key: your-secret-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}')

# Extract request ID
REQUEST_ID=$(echo $RESPONSE | jq -r '.request_id')

# Check status
curl https://your-app.railway.app/downloads/$REQUEST_ID \
  -H "X-API-Key: your-secret-api-key-here"

# Download file when ready
curl "https://your-app.railway.app/files/path/to/video.mp4" -o video.mp4
```

### Discover Playlist Content

```bash
curl "https://your-app.railway.app/discover?sources=https://youtube.com/playlist?list=EXAMPLE&format=json&limit=10" \
  -H "X-API-Key: your-secret-api-key-here"
```

## Security Features

- **API Key Authentication**: Secure access control
- **Path Validation**: Prevents directory traversal attacks
- **File Cleanup**: Automatic deletion prevents storage abuse
- **Request Validation**: Input sanitization and size limits
- **CORS Protection**: Configurable cross-origin policies
- **Domain Allowlist**: Optional restriction to trusted domains

## Monitoring

The service includes built-in monitoring:

- **Health Checks**: `/healthz` endpoint for uptime monitoring
- **Readiness Probe**: `/readyz` for orchestration platforms
- **Prometheus Metrics**: `/metrics` for time-series monitoring
- **Request Logging**: Structured logging for all requests
- **Storage Monitoring**: Automatic storage usage tracking
- **Error Tracking**: Comprehensive error logging

## Troubleshooting

### Common Issues

1. **Download Fails**: Check if the URL is accessible and supported by yt-dlp
2. **File Not Found**: Files are automatically deleted after 1 hour
3. **Storage Full**: Ensure Railway volume has sufficient space
4. **Slow Downloads**: Consider adjusting `WORKERS` and `DEFAULT_TIMEOUT_SEC`
5. **Permission Denied**: Check file permissions and Railway volume mount
6. **Rate Limiting**: Adjust `RATE_LIMIT_RPS` and `RATE_LIMIT_BURST`

### Debug Mode

Set `LOG_LEVEL=DEBUG` for detailed logging:

```bash
LOG_LEVEL=DEBUG python app.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:

1. Check the [Issues](../../issues) page
2. Review the troubleshooting section
3. Create a new issue with detailed information
