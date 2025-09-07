# Railway yt-dlp Service

A comprehensive FastAPI-based service for downloading media from various platforms using yt-dlp, with intent-based processing, enhanced security, Google Drive integration, and comprehensive observability.

## Features

### Core Functionality
- **Intent-Based Downloads**: Smart processing with download, preview, and archive intents
- **Media Download**: Download videos/audio from 1000+ platforms using yt-dlp
- **Enhanced Validation**: Strict URL validation, parameter constraints, and error handling
- **Multiple Quality Options**: Best original, MP4 optimized, or strict MP4 re-encoding
- **Dual Storage**: Local storage with multi-token one-time URLs or Google Drive integration
- **Background Processing**: Asynchronous download jobs with comprehensive status tracking
- **Range Support**: HTTP range requests for efficient media streaming
- **Multi-Token URLs**: Generate multiple one-time download tokens for the same file
- **Smart TTL**: Intent-aware token expiration with configurable cleanup policies
- **Audio+Video Artifacts**: Option to download separate audio and video files
- **Metadata Discovery**: Enhanced /discover endpoint with stricter validation and complexity limits

### Security & Rate Limiting
- **API Key Authentication**: Optional API key protection for enhanced security
- **Signed Download Links**: HMAC-SHA256 signed URLs with expiry validation for secure downloads
- **Enhanced Rate Limiting**: Complexity-based rate limiting with configurable thresholds
- **Security Headers**: CORS, XSS protection, content type validation
- **Input Validation**: Comprehensive request validation with Pydantic models
- **Configuration Validation**: Startup validation for environment configuration
- **Intent-Based Security**: Different security policies based on download intent

### Observability & Monitoring
- **Structured Logging**: JSON-formatted logs with loguru
- **Prometheus Metrics**: Built-in metrics endpoint for monitoring
- **Health Checks**: Enhanced health check with dependency validation
- **Request Tracing**: Automatic request/response logging with timing

### Configuration
- **Environment Variables**: Full configuration via environment variables
- **Development Mode**: Easy setup for local development
- **Production Ready**: Optimized for production deployment

## Quick Start

### Prerequisites
- Python 3.12+
- ffmpeg (for video processing)
- yt-dlp (installed via requirements.txt)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd railway-yt-dlp-service
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment (optional):
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the service:
```bash
python app.py
```

The service will start on `http://localhost:8000`

### Docker Deployment

```bash
docker build -t railway-yt-dlp-service .
docker run -p 8000:8000 -e PUBLIC_FILES_DIR=/app/public railway-yt-dlp-service
```

## API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

### Core Endpoints

#### POST /download
Submit an intent-based download job with enhanced validation.

**Request Body:**
```json
{
  "intent": "download",
  "url": "https://example.com/video",
  "tag": "my-download-job",
  "expected_name": "video.mp4",
  "quality": "BEST_MP4",
  "dest": "LOCAL",
  "callback_url": "https://your-webhook.com/callback",
  "separate_audio_video": false,
  "audio_format": "m4a",
  "token_count": 1,
  "custom_ttl": 86400,
  "timeout": 5400,
  "retries": 3,
  "socket_timeout": 30
}
```

**Intent-Based Parameters:**
- `intent` (optional): Processing intent - "download", "preview", or "archive" (default: "download")
  - `download`: Standard processing with 24h default TTL
  - `preview`: Quick access with 1h max TTL, LOCAL dest only
  - `archive`: Long-term storage with 7d default TTL, single token only

**Enhanced Parameters:**
- `url` (required): Source URL with strict validation (http/https, max 2048 chars)
- `tag` (optional): Alphanumeric identifier with validation (max 100 chars)
- `expected_name` (optional): Output filename with sanitization (max 255 chars)
- `timeout` (optional): Download timeout, 60-7200 seconds (default: 5400)
- `retries` (optional): Retry attempts per strategy, 1-10 (default: 3)
- `socket_timeout` (optional): Socket timeout, 10-300 seconds (default: 30)

**Multi-Artifact Parameters:**
- `separate_audio_video` (optional): Download separate audio and video files (default: false)
- `audio_format` (optional): Audio format when separating: m4a, mp3, or best (default: m4a)
- `token_count` (optional): Number of tokens to create per artifact, 1-5 (default: 1)
- `custom_ttl` (optional): Custom TTL for tokens in seconds, 60s to 7 days (default: intent-based)

**Response:**
```json
{
  "accepted": true,
  "tag": "my-download-job",
  "expected_name": "video.mp4",
  "note": "processing with intent: download"
}
```

#### GET /status?tag={job_tag}
Check download job status.

#### GET /result?tag={job_tag}
Get download job result with enhanced metadata and tag management.

**Query Parameters:**
- `tag` (required): Job tag identifier (validated, alphanumeric only)
- `include_metadata` (optional): Include detailed metadata (default: false)
- `format` (optional): Response format - "json" or "minimal" (default: "json")

**Enhanced Response (with include_metadata=true):**
```json
{
  "tag": "my-download-job",
  "status": "ready",
  "expected_name": "video.mp4",
  "once_url": "/once/abc123?sig=f3d1a2c4&exp=1640995200",
  "once_urls": ["/once/abc123?sig=f3d1a2c4&exp=1640995200"],
  "expires_in_sec": 86400,
  "quality": "BEST_MP4",
  "dest": "LOCAL",
  "intent": "download",
  "created_at": 1640908800.0,
  "updated_at": 1640912400.0,
  "processing_duration": 3600.0
}
```

**Minimal Response (format=minimal):**
```json
{
  "tag": "my-download-job",
  "status": "ready",
  "once_url": "/once/abc123?sig=f3d1a2c4&exp=1640995200",
  "expires_in_sec": 86400
}
```

**Multi-Artifact Response (when separate_audio_video=true):**
```json
{
  "tag": "my-download-job", 
  "status": "ready",
  "expected_name": "video.mp4",
  "artifacts": [
    {
      "type": "audio",
      "filename": "video_audio.m4a",
      "urls": ["/once/audio1?sig=abc123&exp=1640995200"],
      "format": "m4a"
    },
    {
      "type": "video", 
      "filename": "video_video.mp4",
      "urls": ["/once/video1?sig=def456&exp=1640995200"],
      "format": "mp4"
    }
  ],
  "expires_in_sec": 86400,
  "quality": "BEST_MP4",
  "dest": "LOCAL",
  "separate_audio_video": true
}
```

#### GET /once/{token}
Stream downloaded file (single-use, supports HTTP ranges).

#### POST /mint
Mint additional one-time tokens for an existing file.

**Request Body:**
```json
{
  "file_id": "file_abc12345",
  "count": 3,
  "ttl_sec": 7200,
  "tag": "additional_tokens"
}
```

**Response:**
```json
{
  "success": true,
  "file_id": "file_abc12345",
  "tokens_created": 3,
  "urls": [
    "/once/token1",
    "/once/token2", 
    "/once/token3"
  ],
  "expires_in_sec": 7200
}
```

**Rate Limit:** 30 requests per minute  
**Authentication:** API key required (if configured)

#### GET /files
List available files that can have additional tokens minted.

**Response:**
```json
{
  "files": [
    {
      "file_id": "file_abc12345",
      "filename": "video.mp4",
      "size": 15728640,
      "active_tokens": 2,
      "created_at": "2024-01-15T10:30:00"
    }
  ],
  "total_files": 1
}
```

**Rate Limit:** 30 requests per minute  
**Authentication:** API key required (if configured)

#### GET /discover
Enhanced metadata discovery with strict validation and complexity limits.

Performs metadata discovery across one or more provided source URLs (channels, playlists, individual videos) using yt-dlp without downloading content. Now includes enhanced validation and complexity-based rate limiting.

**Query Parameters:**
- `sources` (required): Comma-separated URLs to discover (max 10 sources, max 4096 chars total)
- `format` (required): Output format - csv, json, or ndjson (strict validation)
- `limit` (optional): Limit per source, 1-1000 (default: 100)
- `min_views` (optional): Minimum view count filter (0 to 1B)
- `min_duration` (optional): Minimum duration in seconds (1-86400)
- `max_duration` (optional): Maximum duration in seconds (1-86400, must be > min_duration)
- `dateafter` (optional): Date filter - YYYYMMDD or now-<days>days format (max 32 chars)
- `match_filter` (optional): Raw yt-dlp match filter expression (max 512 chars)
- `fields` (optional): CSV field list (max 512 chars, default: id,title,url,duration,view_count,like_count,uploader,upload_date)

**Enhanced Validation:**
- URLs must be http/https and max 2048 characters each
- Complexity scoring prevents resource exhaustion (max score: 50)
- Duration parameters validated for logical consistency
- Format strictly validated against allowed values

**Rate Limit:** 20 requests per minute + complexity-based throttling  
**Authentication:** API key required (if configured)

**Sample Request:**
```
GET /discover?sources=https://youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMq6VmpLgvIgx8B_D2&format=json&limit=5&min_duration=60
```

**Sample Response (CSV):**
```csv
id,title,url,duration,view_count,uploader,upload_date
abc123,Sample Video,https://youtube.com/watch?v=abc123,120,1500,Creator,20231201
def456,Another Video,https://youtube.com/watch?v=def456,240,2300,Creator,20231205
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

### Monitoring Endpoints

#### GET /healthz
Health check endpoint.

#### GET /metrics
Prometheus metrics (for monitoring tools).

## Configuration

### Environment Variables

#### Basic Configuration
- `PORT`: Server port (default: 8000)
- `PUBLIC_FILES_DIR`: Directory for storing downloaded files (default: /data/public)
- `PUBLIC_BASE_URL`: Base URL for generating download links
- `DEFAULT_DEST`: Default storage destination: LOCAL or DRIVE (default: LOCAL)

#### Security & Rate Limiting
- `API_KEY`: Optional API key for authentication
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins (default: *)
- `RATE_LIMIT_REQUESTS`: Rate limit format (default: 30/minute)
- `SIGNED_LINKS_ENABLED`: Enable signed download links (default: false)
- `LINK_SIGNING_KEY`: 64-character hex key for signing links (required if SIGNED_LINKS_ENABLED=true)

#### Google Drive Integration
- `DRIVE_ENABLED`: Enable Google Drive: oauth or service
- `DRIVE_AUTH`: Authentication method: oauth or service (default: oauth)
- `DRIVE_FOLDER_ID`: Default Google Drive folder ID
- `DRIVE_PUBLIC`: Make uploaded files public (default: false)

**OAuth Method:**
- `GOOGLE_CLIENT_ID`: OAuth client ID
- `GOOGLE_CLIENT_SECRET`: OAuth client secret  
- `GOOGLE_REFRESH_TOKEN`: OAuth refresh token

**Service Account Method:**
- `DRIVE_SERVICE_ACCOUNT_JSON`: Service account JSON (as string)
- `DRIVE_SERVICE_ACCOUNT_JSON_B64`: Service account JSON (base64 encoded)

#### Download Configuration
- `DOWNLOAD_TIMEOUT_SEC`: Download timeout in seconds (default: 5400)
- `ONCE_TOKEN_TTL_SEC`: Default single-use token TTL in seconds (default: 86400)
- `DELETE_AFTER_SERVE`: Delete files after streaming (default: true)

**Note:** Individual tokens can override the default TTL using the `custom_ttl` parameter in download requests or when minting tokens.

#### Logging
- `LOG_LEVEL`: Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)

### Quality Options

- **BEST_ORIGINAL**: Download best quality, preserve original format, merge to MP4
- **BEST_MP4**: Download best MP4 video + audio, remux if needed
- **STRICT_MP4_REENC**: Re-encode everything to MP4 (most compatible)

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-httpx pytest-cov

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
black app.py tests/

# Sort imports
isort app.py tests/

# Lint code
flake8 app.py tests/
```

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

## Production Deployment

### Railway
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

### Environment Setup for Production

```bash
# Required for production
export API_KEY="your-secret-api-key"
export PUBLIC_BASE_URL="https://your-domain.com"
export PUBLIC_FILES_DIR="/app/data/public"

# Optional: Google Drive
export DRIVE_ENABLED="service"
export DRIVE_SERVICE_ACCOUNT_JSON_B64="base64-encoded-service-account-json"
export DRIVE_FOLDER_ID="your-drive-folder-id"

# Security
export CORS_ORIGINS="https://yourdomain.com,https://anotherdomain.com"
export RATE_LIMIT_REQUESTS="10/minute"
```

### Monitoring

The service provides several monitoring endpoints:

1. **Health Check**: `/healthz` - Returns service health status
2. **Metrics**: `/metrics` - Prometheus-compatible metrics
3. **Logs**: Structured JSON logs with request tracing

Set up monitoring tools like:
- Prometheus + Grafana for metrics
- ELK stack or similar for log aggregation
- Uptime monitoring for health checks

## Troubleshooting

### Common Issues

1. **Permission Denied for /data/public**
   - Set `PUBLIC_FILES_DIR` to a writable directory
   - Ensure proper file permissions

2. **yt-dlp Download Failures**
   - Check if the URL is supported
   - Verify internet connectivity
   - Try different quality settings

3. **Google Drive Upload Fails**
   - Verify credentials and permissions
   - Check folder ID exists and is accessible
   - Ensure Drive API is enabled

4. **Rate Limit Errors**
   - Adjust `RATE_LIMIT_REQUESTS` setting
   - Implement client-side retry logic
   - Consider API key authentication

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python app.py
```

## Security Considerations

1. **Use API Keys in Production**: Set `API_KEY` environment variable
2. **HTTPS Only**: Always use HTTPS in production
3. **CORS Configuration**: Restrict `CORS_ORIGINS` to trusted domains
4. **Rate Limiting**: Configure appropriate rate limits
5. **Signed Links**: Enable `SIGNED_LINKS_ENABLED=true` for enhanced download security
6. **Link Signing Key**: Use a strong 64-character hex key for `LINK_SIGNING_KEY`
7. **File Cleanup**: Ensure `DELETE_AFTER_SERVE=true` for security
8. **Input Validation**: The service validates all inputs, but monitor logs
9. **Intent-Based Access**: Use appropriate intents (preview, download, archive) for different use cases

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Ensure code quality checks pass
6. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error details
3. Open an issue on GitHub with:
   - Error message
   - Environment details
   - Steps to reproduce