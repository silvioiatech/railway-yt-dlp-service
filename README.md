# Railway YT-DLP Service# Railway yt-dlp Service



A fast, secure, and scalable YouTube downloader API service built with FastAPI and yt-dlp, optimized for Railway deployment with automatic file cleanup.A production-ready FastAPI service for downloading media from various platforms using yt-dlp, with Railway storage and automatic file cleanup.



## Features## Features



- **High Performance**: FastAPI-powered REST API with concurrent downloads### Core Functionality

- **Railway Storage**: Direct file storage on Railway mounted volumes- **Media Download**: Download videos/audio from 1000+ platforms using yt-dlp

- **Auto Cleanup**: Files automatically deleted after 1 hour to manage storage- **Railway Storage**: Direct file storage on Railway with automatic cleanup

- **Secure Downloads**: API key authentication and path validation- **Auto-Deletion**: Files automatically deleted after 1 hour

- **Multiple Formats**: Support for various video/audio formats via yt-dlp- **Secure File Serving**: Protected file access with path validation

- **File Serving**: Secure file serving with auto-generated download URLs- **Multiple Formats**: Support for various video/audio quality options

- **Health Monitoring**: Built-in health checks and request logging

- **Production Ready**: Optimized for Railway deployment### Security & Performance

- **API Key Authentication**: Secure access control

## Architecture- **Rate Limiting**: Configurable request rate limits

- **Input Validation**: Comprehensive request validation

This service downloads media files directly to Railway's mounted storage volumes and serves them via secure URLs. Files are automatically cleaned up after 1 hour to prevent storage overflow.- **Background Processing**: Asynchronous download jobs

- **Centralized Scheduler**: Efficient file deletion management

### Components- **Domain Allowlists**: Optional domain restrictions



- **FastAPI Application**: REST API server### Production Ready

- **yt-dlp Pipeline**: Media download processor- **Health Checks**: Comprehensive health monitoring

- **File Deletion Scheduler**: Centralized cleanup management- **Prometheus Metrics**: Built-in observability

- **Storage Manager**: Railway volume integration- **Structured Logging**: Detailed logging with configurable levels

- **Graceful Shutdown**: Clean process termination

## Quick Start- **Error Handling**: Robust error recovery



### Railway Deployment (Recommended)## Quick Start



1. **Fork/Clone** this repository### 1. Environment Setup

2. **Create Railway Project** and connect your repository

3. **Add Railway Volume**:Copy the environment template and configure:

   - Go to Railway dashboard → Your project → Storage

   - Create a new Volume and mount it to `/app/data````bash

4. **Set Environment Variables**:cp .env.example .env

   ``````

   API_KEY=your-secure-api-key-here

   STORAGE_DIR=/app/dataEdit `.env` with your settings:

   PUBLIC_BASE_URL=https://your-app.railway.app

   ``````bash

5. **Deploy**: Railway will automatically build and deploy# Required Configuration

API_KEY=your-secret-api-key-here

### Local DevelopmentALLOW_YT_DOWNLOADS=false



1. **Install Dependencies**:# Railway Storage Configuration

   ```bashSTORAGE_DIR=/app/data  # Mount Railway Volume here

   pip install -r requirements.txtPUBLIC_BASE_URL=https://your-app-name.up.railway.app

   ``````



2. **Set Environment Variables**:### 2. Railway Deployment

   ```bash

   cp .env.example .env1. **Create Railway Volume**:

   # Edit .env with your settings   - Go to Railway dashboard → Your project → Variables

   ```   - Create a new Volume and mount it to `/app/data`



3. **Run the Service**:2. **Set Environment Variables**:

   ```bash   - `API_KEY`: Generate a secure API key

   python app.py   - `STORAGE_DIR`: Set to `/app/data` (or your volume mount path)

   ```   - `PUBLIC_BASE_URL`: Set to your Railway app URL



The service starts on `http://localhost:8080`3. **Deploy**: Railway will automatically deploy from your Git repository



## API Reference### 3. Local Development



### Authentication```bash

# Install dependencies

All API endpoints require authentication via the `X-API-Key` header:pip install -r requirements.txt



```bash# Install yt-dlp

curl -H "X-API-Key: your-secret-api-key-here" ...pip install yt-dlp

```

# Run the service

### Endpointspython app.py

```

#### POST /download

The service will start on `http://localhost:8080`

Create a new download job.

- **Intent-Based Security**: Different security policies based on download intent

**Request:**

```json### 2. Set environment variables

{

  "url": "https://www.youtube.com/watch?v=example",### Observability & Monitoring

  "format": "best",

  "filename_template": "{title}-{id}.{ext}"```bash- **Structured Logging**: JSON-formatted logs with loguru

}

```cp .env.example .env- **Prometheus Metrics**: Built-in metrics endpoint for monitoring



**Response:**# Edit .env with your settings- **Health Checks**: Enhanced health check with dependency validation

```json

{```- **Request Tracing**: Automatic request/response logging with timing

  "request_id": "abc123",

  "status": "processing",

  "message": "Download started"

}### 3. Run with Docker Compose### Configuration

```

- **Environment Variables**: Full configuration via environment variables

#### GET /downloads/{request_id}

```bash- **Development Mode**: Easy setup for local development

Check download job status.

make dev- **Production Ready**: Optimized for production deployment

**Response (Processing):**

```json```

{

  "request_id": "abc123",## Quick Start

  "status": "processing",

  "message": "Download in progress"### 4. Test the service

}

```### Prerequisites



**Response (Complete):**```bash- Python 3.12+

```json

{# Health check- ffmpeg (for video processing)

  "request_id": "abc123",

  "status": "completed",curl http://localhost:8080/healthz- yt-dlp (installed via requirements.txt)

  "message": "Download completed",

  "file_url": "https://your-app.railway.app/files/path/to/video.mp4",

  "file_size": 15728640,

  "expires_at": "2024-01-01T13:00:00Z"# Create a download job### Installation

}

```curl -X POST http://localhost:8080/download \



#### GET /files/{path:path}  -H "X-API-Key: your-secret-api-key-here" \1. Clone the repository:



Serve downloaded files securely.  -H "Content-Type: application/json" \```bash



**Example:**  -d '{git clone <repository-url>

```bash

curl https://your-app.railway.app/files/videos/example-abc123.mp4 -o video.mp4    "url": "https://example.com/video",cd railway-yt-dlp-service

```

    "remote": "s3",```

#### GET /health

    "path": "videos/{safe_title}-{id}.{ext}",

Health check endpoint.

    "format": "bv*+ba/best"2. Install dependencies:

**Response:**

```json  }'```bash

{

  "status": "healthy",pip install -r requirements.txt

  "timestamp": "2024-01-01T12:00:00Z",

  "storage_available": true,# Check job status```

  "active_downloads": 2

}curl http://localhost:8080/downloads/{request_id}

```

```3. Set up environment (optional):

## Configuration

```bash

### Environment Variables

## API Referencecp .env.example .env

| Variable | Required | Default | Description |

|----------|----------|---------|-------------|# Edit .env with your configuration

| `API_KEY` | Yes | - | Secret API key for authentication |

| `STORAGE_DIR` | Yes | `/app/data` | Directory for storing downloaded files |### POST /download```

| `PUBLIC_BASE_URL` | Yes | - | Public URL of your Railway app |

| `MAX_FILE_SIZE` | No | `1GB` | Maximum allowed download size |

| `CLEANUP_INTERVAL` | No | `300` | Cleanup check interval in seconds |

| `FILE_LIFETIME` | No | `3600` | File lifetime in seconds (1 hour) |Create a new download job.4. Run the service:

| `MAX_CONCURRENT_DOWNLOADS` | No | `5` | Maximum concurrent downloads |

```bash

### Storage Configuration

**Headers:**python app.py

For Railway deployment, ensure you have:

- `X-API-Key`: Required API key```

1. **Volume Mount**: Railway volume mounted to `/app/data`

2. **Storage Permissions**: Write access to the mounted volume- `Content-Type: application/json`

3. **Cleanup Process**: The service automatically manages file cleanup

The service will start on `http://localhost:8000`

## Usage Examples

**Request Body:**

### Basic Video Download

```json### Docker Deployment

```bash

curl -X POST https://your-app.railway.app/download \{

  -H "X-API-Key: your-secret-api-key-here" \

  -H "Content-Type: application/json" \  "url": "https://example.com/video",```bash

  -d '{

    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  "dest": "BUCKET",docker build -t railway-yt-dlp-service .

    "format": "best",

    "filename_template": "{title}-{id}.{ext}"  "remote": "s3",docker run -p 8000:8000 -e PUBLIC_FILES_DIR=/app/public railway-yt-dlp-service

  }'

```  "path": "videos/{safe_title}-{id}.{ext}",```



### Audio Only Download  "format": "bv*+ba/best",



```bash  "webhook": "https://your-app.com/webhook",## API Documentation

curl -X POST https://your-app.railway.app/download \

  -H "X-API-Key: your-secret-api-key-here" \  "headers": {

  -H "Content-Type: application/json" \

  -d '{    "Content-Type": "video/mp4"Once running, visit:

    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",

    "format": "bestaudio",  },- **Interactive API Docs**: http://localhost:8000/docs

    "filename_template": "{title}-{id}.{ext}"

  }'  "cookies": "session=abc123",- **ReDoc Documentation**: http://localhost:8000/redoc

```

  "timeout_sec": 1800

### Check Status and Download

}### Core Endpoints

```bash

# Start download```

RESPONSE=$(curl -X POST https://your-app.railway.app/download \

  -H "X-API-Key: your-secret-api-key-here" \#### POST /download

  -H "Content-Type: application/json" \

  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}')**Response:**Submit an intent-based download job with enhanced validation.



# Extract request ID```json

REQUEST_ID=$(echo $RESPONSE | jq -r '.request_id')

{**Request Body:**

# Check status

curl https://your-app.railway.app/downloads/$REQUEST_ID \  "status": "QUEUED",```json

  -H "X-API-Key: your-secret-api-key-here"

  "request_id": "12345678-1234-5678-9abc-123456789abc",{

# Download file when ready

curl "https://your-app.railway.app/files/path/to/video.mp4" -o video.mp4  "logs_url": "https://api.example.com/downloads/12345678.../logs",  "intent": "download",

```

  "created_at": "2025-09-24T12:00:00Z"  "url": "https://example.com/video",

## Security Features

}  "tag": "my-download-job",

- **API Key Authentication**: Secure access control

- **Path Validation**: Prevents directory traversal attacks```  "expected_name": "video.mp4",

- **File Cleanup**: Automatic deletion prevents storage abuse

- **Request Validation**: Input sanitization and size limits  "quality": "BEST_MP4",

- **CORS Protection**: Configurable cross-origin policies

### GET /downloads/{request_id}  "dest": "LOCAL",

## Monitoring

  "callback_url": "https://your-webhook.com/callback",

The service includes built-in monitoring:

Get download job status.  "separate_audio_video": false,

- **Health Checks**: `/health` endpoint for uptime monitoring

- **Request Logging**: Structured logging for all requests  "audio_format": "m4a",

- **Storage Monitoring**: Automatic storage usage tracking

- **Error Tracking**: Comprehensive error logging**Response:**  "token_count": 1,



## Troubleshooting```json  "custom_ttl": 86400,



### Common Issues{  "timeout": 5400,



1. **Download Fails**: Check if the URL is accessible and supported by yt-dlp  "status": "DONE",  "retries": 3,

2. **File Not Found**: Files are automatically deleted after 1 hour

3. **Storage Full**: The service automatically cleans up old files  "request_id": "12345678-1234-5678-9abc-123456789abc",  "socket_timeout": 30

4. **Slow Downloads**: Consider adjusting `MAX_CONCURRENT_DOWNLOADS`

  "object_url": "https://s3.amazonaws.com/bucket/videos/video.mp4",}

### Debug Mode

  "bytes": 104857600,```

Set `DEBUG=true` for detailed logging:

  "duration_sec": 45.2,

```bash

DEBUG=true python app.py  "logs_url": "https://api.example.com/downloads/12345678.../logs",**Intent-Based Parameters:**

```

  "created_at": "2025-09-24T12:00:00Z",- `intent` (optional): Processing intent - "download", "preview", or "archive" (default: "download")

## License

  "completed_at": "2025-09-24T12:01:30Z"  - `download`: Standard processing with 24h default TTL

This project is licensed under the MIT License - see the LICENSE file for details.

}  - `preview`: Quick access with 1h max TTL, LOCAL dest only

## Contributing

```  - `archive`: Long-term storage with 7d default TTL, single token only

1. Fork the repository

2. Create a feature branch

3. Make your changes

4. Add tests if applicable## Path Templates**Enhanced Parameters:**

5. Submit a pull request

- `url` (required): Source URL with strict validation (http/https, max 2048 chars)

## Support

Customize object storage paths using these tokens:- `tag` (optional): Alphanumeric identifier with validation (max 100 chars)

For issues and questions:

- `expected_name` (optional): Output filename with sanitization (max 255 chars)

1. Check the [Issues](../../issues) page

2. Review the troubleshooting section- `{id}`: Video ID- `timeout` (optional): Download timeout, 60-7200 seconds (default: 5400)

3. Create a new issue with detailed information
- `{title}`: Full title- `retries` (optional): Retry attempts per strategy, 1-10 (default: 3)

- `{safe_title}`: Sanitized title (filesystem safe)- `socket_timeout` (optional): Socket timeout, 10-300 seconds (default: 30)

- `{ext}`: File extension (e.g., mp4)

- `{uploader}`: Uploader name**Multi-Artifact Parameters:**

- `{date}`: Upload date (YYYY-MM-DD)- `separate_audio_video` (optional): Download separate audio and video files (default: false)

- `{random}`: Random hex string- `audio_format` (optional): Audio format when separating: m4a, mp3, or best (default: m4a)

- `token_count` (optional): Number of tokens to create per artifact, 1-5 (default: 1)

**Examples:**- `custom_ttl` (optional): Custom TTL for tokens in seconds, 60s to 7 days (default: intent-based)

- `videos/{safe_title}-{id}.{ext}` → `videos/My_Video-abc123.mp4`

- `{date}/{uploader}/{id}.{ext}` → `2025-09-24/Creator/abc123.mp4`**Response:**

```json

## rclone Remote Examples{

  "accepted": true,

### Amazon S3  "tag": "my-download-job",

```  "expected_name": "video.mp4",

[s3]  "note": "processing with intent: download"

type = s3}

provider = AWS```

access_key_id = YOUR_ACCESS_KEY

secret_access_key = YOUR_SECRET_KEY#### GET /status?tag={job_tag}

region = us-east-1Check download job status.

```

#### GET /result?tag={job_tag}

### Google Cloud StorageGet download job result with enhanced metadata and tag management.

```

[gcs]**Query Parameters:**

type = google cloud storage- `tag` (required): Job tag identifier (validated, alphanumeric only)

project_number = 123456789- `include_metadata` (optional): Include detailed metadata (default: false)

service_account_file = /path/to/service-account.json- `format` (optional): Response format - "json" or "minimal" (default: "json")

```

**Enhanced Response (with include_metadata=true):**

### Azure Blob Storage```json

```{

[azure]  "tag": "my-download-job",

type = azureblob  "status": "ready",

account = mystorageaccount  "expected_name": "video.mp4",

key = YOUR_STORAGE_KEY  "once_url": "/once/abc123?sig=f3d1a2c4&exp=1640995200",

```  "once_urls": ["/once/abc123?sig=f3d1a2c4&exp=1640995200"],

  "expires_in_sec": 86400,

### Backblaze B2  "quality": "BEST_MP4",

```  "dest": "LOCAL",

[b2]  "intent": "download",

type = b2  "created_at": 1640908800.0,

account = YOUR_ACCOUNT_ID  "updated_at": 1640912400.0,

key = YOUR_APPLICATION_KEY  "processing_duration": 3600.0

```}

```

### MinIO (Self-hosted)

```**Minimal Response (format=minimal):**

[minio]```json

type = s3{

provider = Minio  "tag": "my-download-job",

access_key_id = minioadmin  "status": "ready",

secret_access_key = minioadmin  "once_url": "/once/abc123?sig=f3d1a2c4&exp=1640995200",

endpoint = http://localhost:9000  "expires_in_sec": 86400

```}

```

## Configuration

**Multi-Artifact Response (when separate_audio_video=true):**

### Required Environment Variables```json

{

- `API_KEY`: Secret key for API authentication  "tag": "my-download-job", 

- `ALLOW_YT_DOWNLOADS`: Enable/disable YouTube downloads (ToS compliance)  "status": "ready",

- `RCLONE_REMOTE_DEFAULT`: Default rclone remote name  "expected_name": "video.mp4",

  "artifacts": [

### Optional Environment Variables    {

      "type": "audio",

- `PUBLIC_BASE_URL`: Base URL for generating log links      "filename": "video_audio.m4a",

- `WORKERS`: Number of concurrent download workers (default: 2)      "urls": ["/once/audio1?sig=abc123&exp=1640995200"],

- `RATE_LIMIT_RPS`: Rate limit requests per second (default: 2)      "format": "m4a"

- `DEFAULT_TIMEOUT_SEC`: Default job timeout (default: 1800)    },

- `MAX_CONTENT_LENGTH`: Maximum file size (default: 10GB)    {

- `ALLOWED_DOMAINS`: Comma-separated allowlist of domains      "type": "video", 

- `LOG_LEVEL`: Logging level (default: INFO)      "filename": "video_video.mp4",

      "urls": ["/once/video1?sig=def456&exp=1640995200"],

## Observability      "format": "mp4"

    }

### Health Checks  ],

  "expires_in_sec": 86400,

- `GET /healthz`: Comprehensive health check  "quality": "BEST_MP4",

- `GET /readyz`: Readiness probe  "dest": "LOCAL",

- `GET /version`: Version information  "separate_audio_video": true

}

### Metrics```



Prometheus metrics available at `/metrics`:#### GET /once/{token}

Stream downloaded file (single-use, supports HTTP ranges).

- `jobs_total`: Total jobs processed (by status)

- `jobs_duration_seconds`: Job processing duration histogram#### POST /mint

- `bytes_uploaded_total`: Total bytes uploadedMint additional one-time tokens for an existing file.

- `jobs_in_flight`: Currently running jobs

**Request Body:**

### Logging```json

{

- Structured JSON logging to stdout and files  "file_id": "file_abc12345",

- Per-job log files in `/var/log/app/`  "count": 3,

- Request correlation with request IDs  "ttl_sec": 7200,

  "tag": "additional_tokens"

## Development}

```

```bash

# Setup development environment**Response:**

make setup```json

{

# Run tests  "success": true,

make test  "file_id": "file_abc12345",

  "tokens_created": 3,

# Run with coverage  "urls": [

make test-coverage    "/once/token1",

    "/once/token2", 

# Lint and format    "/once/token3"

make lint  ],

make format  "expires_in_sec": 7200

}

# Build Docker image```

make build

**Rate Limit:** 30 requests per minute  

# Clean up**Authentication:** API key required (if configured)

make clean

```#### GET /files

List available files that can have additional tokens minted.

## Production Deployment

**Response:**

### Docker```json

{

```bash  "files": [

docker build -t yt-dlp-streaming-service .    {

docker run -d \      "file_id": "file_abc12345",

  -p 8080:8080 \      "filename": "video.mp4",

  -v ~/.config/rclone:/home/appuser/.config/rclone:ro \      "size": 15728640,

  -v ./logs:/var/log/app \      "active_tokens": 2,

  --env-file .env \      "created_at": "2024-01-15T10:30:00"

  --name yt-dlp-service \    }

  yt-dlp-streaming-service  ],

```  "total_files": 1

}

### Kubernetes```



See `k8s/` directory for Kubernetes manifests.**Rate Limit:** 30 requests per minute  

**Authentication:** API key required (if configured)

### Security Considerations

#### GET /discover

1. **API Key**: Use a strong, randomly generated API keyEnhanced metadata discovery with strict validation and complexity limits.

2. **Domain Allowlist**: Restrict allowed source domains

3. **Rate Limiting**: Configure appropriate rate limitsPerforms metadata discovery across one or more provided source URLs (channels, playlists, individual videos) using yt-dlp without downloading content. Now includes enhanced validation and complexity-based rate limiting.

4. **Network**: Run in a private network when possible

5. **Updates**: Keep yt-dlp and rclone updated regularly**Query Parameters:**

- `sources` (required): Comma-separated URLs to discover (max 10 sources, max 4096 chars total)

## Troubleshooting- `format` (required): Output format - csv, json, or ndjson (strict validation)

- `limit` (optional): Limit per source, 1-1000 (default: 100)

### Common Issues- `min_views` (optional): Minimum view count filter (0 to 1B)

- `min_duration` (optional): Minimum duration in seconds (1-86400)

1. **rclone not found**: Ensure rclone is installed and in PATH- `max_duration` (optional): Maximum duration in seconds (1-86400, must be > min_duration)

2. **Permission denied**: Check file permissions and user configuration- `dateafter` (optional): Date filter - YYYYMMDD or now-<days>days format (max 32 chars)

3. **Network timeouts**: Adjust timeout settings for your network- `match_filter` (optional): Raw yt-dlp match filter expression (max 512 chars)

4. **Storage errors**: Verify rclone remote configuration- `fields` (optional): CSV field list (max 512 chars, default: id,title,url,duration,view_count,like_count,uploader,upload_date)



### Debug Mode**Enhanced Validation:**

- URLs must be http/https and max 2048 characters each

Set `LOG_LEVEL=DEBUG` for verbose logging.- Complexity scoring prevents resource exhaustion (max score: 50)

- Duration parameters validated for logical consistency

## License- Format strictly validated against allowed values



MIT License - see LICENSE file for details.**Rate Limit:** 20 requests per minute + complexity-based throttling  
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