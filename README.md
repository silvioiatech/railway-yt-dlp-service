# Railway yt-dlp Service

A comprehensive FastAPI-based service for downloading media from various platforms using yt-dlp, with Google Drive integration, security features, observability, and rate limiting.

## Features

### Core Functionality
- **Media Download**: Download videos/audio from 1000+ platforms using yt-dlp
- **Multiple Quality Options**: Best original, MP4 optimized, or strict MP4 re-encoding
- **Dual Storage**: Local storage with single-use tokens or Google Drive integration
- **Background Processing**: Asynchronous download jobs with status tracking
- **Range Support**: HTTP range requests for efficient media streaming

### Security & Rate Limiting
- **API Key Authentication**: Optional API key protection for enhanced security
- **Rate Limiting**: Configurable rate limits per endpoint to prevent abuse
- **Security Headers**: CORS, XSS protection, content type validation
- **Input Validation**: Comprehensive request validation and sanitization

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
Submit a download job.

**Request Body:**
```json
{
  "url": "https://example.com/video",
  "tag": "my-download-job",
  "expected_name": "video.mp4",
  "quality": "BEST_MP4",
  "dest": "LOCAL",
  "callback_url": "https://your-webhook.com/callback"
}
```

**Response:**
```json
{
  "accepted": true,
  "tag": "my-download-job",
  "expected_name": "video.mp4",
  "note": "processing"
}
```

#### GET /status?tag={job_tag}
Check download job status.

#### GET /result?tag={job_tag}
Get download job result with download links.

#### GET /once/{token}
Stream downloaded file (single-use, supports HTTP ranges).

#### GET /discover
Discover metadata from video sources without downloading.

Performs metadata discovery across one or more provided source URLs (channels, playlists, individual videos) using yt-dlp without downloading content.

**Query Parameters:**
- `sources` (required): Comma-separated URLs to discover
- `format` (optional): Output format - csv, json, or ndjson (default: csv)
- `limit` (optional): Limit per source, 1-1000 (default: 100)
- `min_views` (optional): Minimum view count filter
- `min_duration` (optional): Minimum duration in seconds
- `max_duration` (optional): Maximum duration in seconds
- `dateafter` (optional): Date filter - YYYYMMDD or now-<days>days format
- `match_filter` (optional): Raw yt-dlp match filter expression
- `fields` (optional): CSV field list (default: id,title,url,duration,view_count,like_count,uploader,upload_date)

**Rate Limit:** 20 requests per minute  
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
- `ONCE_TOKEN_TTL_SEC`: Single-use token TTL in seconds (default: 86400)
- `DELETE_AFTER_SERVE`: Delete files after streaming (default: true)

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
5. **File Cleanup**: Ensure `DELETE_AFTER_SERVE=true` for security
6. **Input Validation**: The service validates all inputs, but monitor logs

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