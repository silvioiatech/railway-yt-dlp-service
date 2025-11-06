# Quick Start Guide

Get the Ultimate Media Downloader up and running in 5 minutes!

## Prerequisites

- Python 3.9 or higher
- pip package manager
- 1GB free disk space minimum
- (Optional) Railway account for deployment

## 1. Installation (2 minutes)

```bash
# Clone the repository
git clone https://github.com/yourusername/railway-yt-dlp-service.git
cd railway-yt-dlp-service

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m app.main --help
```

## 2. Configuration (1 minute)

```bash
# Copy environment template
cp .env.example .env

# Generate secure API key
python -c "import secrets; print(f'API_KEY={secrets.token_urlsafe(32)}')" >> .env

# (Optional) Generate cookie encryption key
python -c "import secrets; print(f'COOKIE_ENCRYPTION_KEY={secrets.token_hex(32)}')" >> .env
```

Edit `.env` and set:

```bash
REQUIRE_API_KEY=true
API_KEY=<your-generated-key>
STORAGE_DIR=./downloads
PUBLIC_BASE_URL=http://localhost:8080
ALLOW_YT_DOWNLOADS=true  # Set to true if you want YouTube downloads
```

## 3. Start the Service (30 seconds)

```bash
# Start the service
python -m app.main

# You should see:
# INFO - Starting Ultimate Media Downloader v3.1.0
# INFO - Queue manager started: 2 workers, max 3 concurrent downloads
# INFO - Ultimate Media Downloader startup complete - listening on 0.0.0.0:8080
```

## 4. Test the API (1 minute)

### Option A: Use the Web Interface

Open your browser to:
```
http://localhost:8080
```

You'll see a modern web interface where you can:
- Download single videos
- Browse and download channels
- Manage batch downloads
- Upload and manage cookies

### Option B: Use the API Directly

```bash
# Set your API key
export API_KEY="your-key-from-env-file"

# Check service health
curl http://localhost:8080/api/v1/health

# Start a download
curl -X POST http://localhost:8080/api/v1/download \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video",
    "quality": "720p"
  }'

# Check status (replace with your request_id)
curl http://localhost:8080/api/v1/downloads/req_abc123 \
  -H "X-API-Key: $API_KEY"
```

## 5. Your First Download (1 minute)

### Single Video Download

```python
import requests

API_BASE = "http://localhost:8080"
API_KEY = "your-api-key"

# Start download
response = requests.post(
    f"{API_BASE}/api/v1/download",
    headers={"X-API-Key": API_KEY},
    json={
        "url": "https://example.com/video",
        "quality": "1080p",
        "download_subtitles": True
    }
)

request_id = response.json()["request_id"]
print(f"Download started: {request_id}")

# Check status
status = requests.get(
    f"{API_BASE}/api/v1/downloads/{request_id}",
    headers={"X-API-Key": API_KEY}
).json()

print(f"Status: {status['status']}")
print(f"Progress: {status.get('progress', {}).get('percent', 0)}%")
```

## Common Use Cases

### Use Case 1: Download a Video with Subtitles

```bash
curl -X POST http://localhost:8080/api/v1/download \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video",
    "quality": "1080p",
    "download_subtitles": true,
    "subtitle_languages": ["en", "es"],
    "embed_subtitles": true
  }'
```

### Use Case 2: Download Audio Only

```bash
curl -X POST http://localhost:8080/api/v1/download \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video",
    "audio_only": true,
    "audio_format": "mp3",
    "audio_quality": "320"
  }'
```

### Use Case 3: Browse a Channel

```bash
curl -X GET "http://localhost:8080/api/v1/channel/info?url=https://youtube.com/@example&date_after=20250101&sort_by=view_count" \
  -H "X-API-Key: $API_KEY"
```

### Use Case 4: Batch Download

```bash
curl -X POST http://localhost:8080/api/v1/batch/download \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com/video1",
      "https://example.com/video2",
      "https://example.com/video3"
    ],
    "quality": "720p",
    "concurrent_limit": 3
  }'
```

### Use Case 5: Download with Cookies (Private Content)

```bash
# First, upload cookies
COOKIE_ID=$(curl -X POST http://localhost:8080/api/v1/cookies \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "browser": "chrome",
    "name": "my_cookies"
  }' | jq -r '.cookie_id')

# Then download with cookies
curl -X POST http://localhost:8080/api/v1/download \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://example.com/private-video\",
    \"cookies_id\": \"$COOKIE_ID\"
  }"
```

## Troubleshooting

### Service won't start

**Problem**: Port 8080 already in use

**Solution**: Change port in `.env`:
```bash
PORT=8081
```

### Downloads failing

**Problem**: YouTube downloads failing

**Solution**: Enable YouTube in `.env`:
```bash
ALLOW_YT_DOWNLOADS=true
```

**Problem**: Permission errors with storage directory

**Solution**: Check directory permissions:
```bash
mkdir -p ./downloads
chmod 755 ./downloads
```

### API returns 401 Unauthorized

**Problem**: Invalid or missing API key

**Solution**: Check your API key in `.env` matches the one in your requests

### Cookie extraction fails

**Problem**: Browser cookies can't be extracted

**Solution**: Make sure the browser is installed and you're not running as root. Try uploading cookies manually instead:
```bash
# Export cookies to Netscape format using a browser extension
# Then upload them:
curl -X POST http://localhost:8080/api/v1/cookies \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": "<paste-netscape-cookies-here>",
    "name": "manual_cookies"
  }'
```

## Next Steps

### Explore Features

1. **Web Interface**: Visit `http://localhost:8080` for the full UI
2. **API Documentation**: Visit `http://localhost:8080/docs` for interactive API docs
3. **Channel Downloads**: See [Channel Downloads Guide](user-guides/CHANNEL_DOWNLOADS.md)
4. **Batch Operations**: See [Batch Downloads Guide](user-guides/BATCH_DOWNLOADS.md)
5. **Webhooks**: See [Webhooks Guide](user-guides/WEBHOOKS.md)

### Deploy to Production

- **Railway**: See [Railway Deployment Guide](deployment/railway.md)
- **Docker**: See [Docker Deployment Guide](deployment/docker.md)
- **Configuration**: See [Configuration Guide](deployment/configuration.md)

### Advanced Topics

- **Architecture**: [Backend Architecture](architecture/BACKEND_ARCHITECTURE.md)
- **API Reference**: [Complete API Documentation](api/API_REFERENCE_COMPLETE.md)
- **Code Examples**: Check the `examples/` directory

## Quick Reference

### Environment Variables

```bash
# Essential
REQUIRE_API_KEY=true
API_KEY=your-secret-key
STORAGE_DIR=./downloads
PUBLIC_BASE_URL=http://localhost:8080

# Performance
WORKERS=2
MAX_CONCURRENT_DOWNLOADS=3
RATE_LIMIT_RPS=2

# Features
WEBHOOK_ENABLE=true
COOKIE_ENCRYPTION_KEY=your-32-byte-hex-key
ALLOW_YT_DOWNLOADS=true

# Timeouts
DEFAULT_TIMEOUT_SEC=1800
PROGRESS_TIMEOUT_SEC=300
FILE_RETENTION_HOURS=48
```

### API Endpoints Quick Reference

```bash
# Downloads
POST   /api/v1/download
GET    /api/v1/downloads/{id}
DELETE /api/v1/downloads/{id}

# Channels
GET    /api/v1/channel/info
POST   /api/v1/channel/download

# Batch
POST   /api/v1/batch/download
GET    /api/v1/batch/{batch_id}
DELETE /api/v1/batch/{batch_id}

# Cookies
POST   /api/v1/cookies
GET    /api/v1/cookies
GET    /api/v1/cookies/{cookie_id}
DELETE /api/v1/cookies/{cookie_id}

# Monitoring
GET    /api/v1/health
GET    /api/v1/readyz
GET    /version
GET    /metrics
```

### Quality Presets

- `best` - Best available quality
- `1080p` - 1920x1080 Full HD
- `720p` - 1280x720 HD
- `480p` - 854x480 SD
- `360p` - 640x360 Low
- `audio_only` - Audio only, no video

### Audio Formats

- `mp3` - MP3 (most compatible)
- `m4a` - M4A/AAC (high quality)
- `opus` - Opus (best compression)
- `flac` - FLAC (lossless)
- `wav` - WAV (uncompressed)

### Video Formats

- `mp4` - MP4 (most compatible)
- `mkv` - Matroska (feature-rich)
- `webm` - WebM (web-optimized)
- `avi` - AVI (legacy)

## Help & Support

- **Documentation**: [Full documentation](README.md)
- **API Reference**: [Complete API docs](api/API_REFERENCE_COMPLETE.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/railway-yt-dlp-service/issues)
- **Examples**: Check the `examples/` directory for code samples

---

**Congratulations!** You now have a fully functional media downloader service running. Explore the features and enjoy!
