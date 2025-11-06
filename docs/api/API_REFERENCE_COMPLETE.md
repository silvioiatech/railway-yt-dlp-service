# Complete API Reference

**Ultimate Media Downloader v3.1.0**

Complete documentation for all API endpoints with request/response examples, error codes, and authentication requirements.

## Table of Contents

1. [Authentication](#authentication)
2. [Rate Limiting](#rate-limiting)
3. [Error Responses](#error-responses)
4. [Download Endpoints](#download-endpoints)
5. [Channel Endpoints](#channel-endpoints)
6. [Batch Endpoints](#batch-endpoints)
7. [Playlist Endpoints](#playlist-endpoints)
8. [Cookie Management](#cookie-management)
9. [Metadata Endpoints](#metadata-endpoints)
10. [Health & Monitoring](#health--monitoring)
11. [Webhook Integration](#webhook-integration)

---

## Authentication

All endpoints require authentication when `REQUIRE_API_KEY=true` (default).

### API Key Header

```http
X-API-Key: your-secret-api-key
```

### Example

```bash
curl -H "X-API-Key: your-api-key" https://api.example.com/api/v1/health
```

### Authentication Errors

```json
{
  "error": "Invalid or missing API key",
  "status_code": 401,
  "timestamp": "2025-11-06T10:00:00Z"
}
```

---

## Rate Limiting

Default rate limits (configurable via environment variables):

- **Rate**: 2 requests per second
- **Burst**: 5 requests
- **Window**: Rolling window per IP address

### Rate Limit Headers

```http
X-RateLimit-Limit: 2
X-RateLimit-Remaining: 1
X-RateLimit-Reset: 1699267200
```

### Rate Limit Exceeded Response

```json
{
  "error": "Rate limit exceeded",
  "status_code": 429,
  "retry_after": 1,
  "timestamp": "2025-11-06T10:00:00Z"
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message describing the problem",
  "error_code": "ERROR_CODE",
  "status_code": 400,
  "timestamp": "2025-11-06T10:00:00Z",
  "details": {}
}
```

### Common HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Request accepted for processing |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Invalid or missing API key |
| 404 | Not Found | Resource not found |
| 413 | Payload Too Large | Request body too large |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

---

## Download Endpoints

### POST /api/v1/download

Create a single download job.

**Authentication**: Required

**Request Body**:

```json
{
  "url": "https://example.com/video",
  "quality": "1080p",
  "video_format": "mp4",
  "audio_only": false,
  "audio_format": "mp3",
  "audio_quality": "192",
  "download_subtitles": false,
  "subtitle_languages": ["en"],
  "subtitle_format": "srt",
  "embed_subtitles": false,
  "auto_subtitles": false,
  "write_thumbnail": false,
  "embed_thumbnail": false,
  "embed_metadata": true,
  "write_info_json": false,
  "path_template": "videos/{safe_title}-{id}.{ext}",
  "cookies_id": null,
  "timeout_sec": 1800,
  "webhook_url": "https://your-app.com/webhook"
}
```

**Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| url | string | Yes | Video URL to download |
| quality | string | No | Quality preset: best, 1080p, 720p, 480p, 360p, audio_only |
| custom_format | string | No | Custom yt-dlp format string (overrides quality) |
| video_format | string | No | Container format: mp4, mkv, webm, avi |
| audio_only | boolean | No | Extract audio only (default: false) |
| audio_format | string | No | Audio format: mp3, m4a, wav, flac, opus |
| audio_quality | string | No | Audio bitrate: 96, 128, 192, 256, 320 |
| download_subtitles | boolean | No | Download subtitles (default: false) |
| subtitle_languages | array | No | Language codes (e.g., ["en", "es"]) |
| subtitle_format | string | No | Subtitle format: srt, vtt, ass |
| embed_subtitles | boolean | No | Embed subtitles in video |
| auto_subtitles | boolean | No | Download auto-generated subs |
| write_thumbnail | boolean | No | Save thumbnail file |
| embed_thumbnail | boolean | No | Embed thumbnail in media file |
| embed_metadata | boolean | No | Embed metadata (default: true) |
| write_info_json | boolean | No | Save metadata as JSON |
| path_template | string | No | Output path template |
| cookies_id | string | No | Stored cookie ID for authentication |
| timeout_sec | integer | No | Timeout in seconds (60-7200) |
| webhook_url | string | No | Webhook notification URL |

**Response** (202 Accepted):

```json
{
  "request_id": "req_abc123def456",
  "status": "queued",
  "url": "https://example.com/video",
  "created_at": "2025-11-06T10:00:00Z",
  "message": "Download job created successfully"
}
```

**cURL Example**:

```bash
curl -X POST https://api.example.com/api/v1/download \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video",
    "quality": "1080p",
    "download_subtitles": true,
    "webhook_url": "https://your-app.com/webhook"
  }'
```

**Python Example**:

```python
import requests

response = requests.post(
    "https://api.example.com/api/v1/download",
    headers={"X-API-Key": "your-api-key"},
    json={
        "url": "https://example.com/video",
        "quality": "1080p",
        "download_subtitles": True,
        "webhook_url": "https://your-app.com/webhook"
    }
)

data = response.json()
request_id = data["request_id"]
```

---

### GET /api/v1/downloads/{request_id}

Get the status of a download job.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| request_id | string | Unique job identifier |

**Response** (200 OK):

```json
{
  "request_id": "req_abc123def456",
  "url": "https://example.com/video",
  "status": "completed",
  "progress": {
    "percent": 100.0,
    "downloaded_bytes": 104857600,
    "total_bytes": 104857600,
    "speed": 1048576,
    "eta": 0
  },
  "file_info": {
    "filename": "video-abc123.mp4",
    "filepath": "videos/video-abc123.mp4",
    "size_bytes": 104857600,
    "download_url": "https://api.example.com/files/videos/video-abc123.mp4"
  },
  "metadata": {
    "title": "Example Video",
    "uploader": "Example Channel",
    "duration": 600,
    "view_count": 10000,
    "upload_date": "20251106"
  },
  "created_at": "2025-11-06T10:00:00Z",
  "started_at": "2025-11-06T10:00:05Z",
  "completed_at": "2025-11-06T10:02:30Z",
  "error": null
}
```

**Status Values**:

- `queued` - Job is waiting in queue
- `running` - Download is in progress
- `completed` - Download completed successfully
- `failed` - Download failed with error
- `cancelled` - Job was cancelled

**cURL Example**:

```bash
curl -X GET https://api.example.com/api/v1/downloads/req_abc123def456 \
  -H "X-API-Key: your-api-key"
```

**Python Example**:

```python
response = requests.get(
    f"https://api.example.com/api/v1/downloads/{request_id}",
    headers={"X-API-Key": "your-api-key"}
)

status = response.json()
print(f"Status: {status['status']}")
print(f"Progress: {status['progress']['percent']}%")
```

---

### GET /api/v1/downloads/{request_id}/logs

Retrieve logs for a specific download job.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| request_id | string | Unique job identifier |

**Response** (200 OK):

```json
{
  "request_id": "req_abc123def456",
  "logs": [
    {
      "timestamp": "2025-11-06T10:00:00Z",
      "level": "INFO",
      "message": "Job created"
    },
    {
      "timestamp": "2025-11-06T10:00:05Z",
      "level": "INFO",
      "message": "Starting download"
    },
    {
      "timestamp": "2025-11-06T10:02:30Z",
      "level": "INFO",
      "message": "Download completed successfully"
    }
  ],
  "total_logs": 3
}
```

**cURL Example**:

```bash
curl -X GET https://api.example.com/api/v1/downloads/req_abc123def456/logs \
  -H "X-API-Key: your-api-key"
```

---

### DELETE /api/v1/downloads/{request_id}

Cancel a download job.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| request_id | string | Unique job identifier |

**Response** (200 OK):

```json
{
  "request_id": "req_abc123def456",
  "status": "cancelled",
  "message": "Job cancelled successfully",
  "timestamp": "2025-11-06T10:00:00Z"
}
```

**cURL Example**:

```bash
curl -X DELETE https://api.example.com/api/v1/downloads/req_abc123def456 \
  -H "X-API-Key: your-api-key"
```

---

## Channel Endpoints

### GET /api/v1/channel/info

Browse channel videos with filtering and pagination.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | Channel URL |
| date_after | string | No | Filter videos after date (YYYYMMDD) |
| date_before | string | No | Filter videos before date (YYYYMMDD) |
| min_duration | integer | No | Minimum duration in seconds |
| max_duration | integer | No | Maximum duration in seconds |
| min_views | integer | No | Minimum view count |
| max_views | integer | No | Maximum view count |
| sort_by | string | No | Sort field: upload_date, view_count, duration, title |
| page | integer | No | Page number (default: 1) |
| page_size | integer | No | Items per page (1-100, default: 20) |

**Response** (200 OK):

```json
{
  "url": "https://youtube.com/@example",
  "channel_id": "UC123456",
  "channel_name": "Example Channel",
  "description": "Channel description",
  "subscriber_count": 1000000,
  "video_count": 500,
  "filtered_video_count": 50,
  "videos": [
    {
      "id": "video1",
      "title": "Example Video",
      "url": "https://youtube.com/watch?v=video1",
      "duration": 600,
      "view_count": 50000,
      "uploader": "Example Channel",
      "upload_date": "20251105",
      "thumbnail": "https://example.com/thumb.jpg",
      "description": "Video description",
      "playlist_index": 1
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "has_next": true,
  "has_previous": false,
  "filters_applied": {
    "date_after": "20250101",
    "min_duration": 300
  },
  "extractor": "youtube"
}
```

**cURL Example**:

```bash
curl -X GET "https://api.example.com/api/v1/channel/info?url=https://youtube.com/@example&date_after=20250101&min_duration=300&sort_by=view_count&page=1&page_size=20" \
  -H "X-API-Key: your-api-key"
```

**Python Example**:

```python
response = requests.get(
    "https://api.example.com/api/v1/channel/info",
    headers={"X-API-Key": "your-api-key"},
    params={
        "url": "https://youtube.com/@example",
        "date_after": "20250101",
        "min_duration": 300,
        "sort_by": "view_count",
        "page": 1,
        "page_size": 20
    }
)

channel = response.json()
print(f"Found {channel['filtered_video_count']} videos")
for video in channel['videos']:
    print(f"- {video['title']} ({video['view_count']} views)")
```

---

### POST /api/v1/channel/download

Download filtered channel videos as a batch job.

**Authentication**: Required

**Request Body**:

```json
{
  "url": "https://youtube.com/@example",
  "date_after": "20250101",
  "date_before": null,
  "min_duration": 300,
  "max_duration": null,
  "min_views": 1000,
  "max_views": null,
  "sort_by": "view_count",
  "max_downloads": 50,
  "quality": "1080p",
  "video_format": "mp4",
  "download_subtitles": true,
  "path_template": "channels/{uploader}/{upload_date}-{title}.{ext}",
  "cookies_id": null,
  "timeout_sec": 3600,
  "webhook_url": "https://your-app.com/webhook"
}
```

**Response** (201 Created):

```json
{
  "batch_id": "batch_abc123",
  "status": "queued",
  "total_jobs": 50,
  "completed_jobs": 0,
  "failed_jobs": 0,
  "running_jobs": 0,
  "queued_jobs": 50,
  "jobs": [
    {
      "job_id": "job_batch_abc123_0",
      "url": "https://youtube.com/watch?v=video1",
      "status": "queued",
      "title": "Example Video",
      "progress": null,
      "file_info": null,
      "error": null,
      "created_at": "2025-11-06T10:00:00Z",
      "completed_at": null
    }
  ],
  "created_at": "2025-11-06T10:00:00Z",
  "started_at": null,
  "completed_at": null,
  "duration_sec": null,
  "error": null
}
```

**cURL Example**:

```bash
curl -X POST https://api.example.com/api/v1/channel/download \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/@example",
    "date_after": "20250101",
    "min_duration": 300,
    "max_downloads": 50,
    "quality": "1080p"
  }'
```

---

## Batch Endpoints

### POST /api/v1/batch/download

Create a batch download job for multiple URLs.

**Authentication**: Required

**Request Body**:

```json
{
  "urls": [
    "https://example.com/video1",
    "https://example.com/video2",
    "https://example.com/video3"
  ],
  "quality": "1080p",
  "video_format": "mp4",
  "concurrent_limit": 3,
  "stop_on_error": false,
  "ignore_errors": true,
  "path_template": "batch/{batch_id}/{safe_title}-{id}.{ext}",
  "cookies_id": null,
  "timeout_sec": 1800,
  "webhook_url": "https://your-app.com/webhook"
}
```

**Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| urls | array | Yes | List of URLs (1-100) |
| quality | string | No | Quality preset |
| video_format | string | No | Container format |
| concurrent_limit | integer | No | Max concurrent downloads (1-10, default: 3) |
| stop_on_error | boolean | No | Stop batch on first error (default: false) |
| ignore_errors | boolean | No | Continue on individual errors (default: true) |
| path_template | string | No | Output path template |
| cookies_id | string | No | Stored cookie ID |
| timeout_sec | integer | No | Timeout per job |
| webhook_url | string | No | Webhook notification URL |

**Response** (202 Accepted):

```json
{
  "batch_id": "batch_xyz789",
  "status": "queued",
  "total_jobs": 3,
  "completed_jobs": 0,
  "failed_jobs": 0,
  "running_jobs": 0,
  "queued_jobs": 3,
  "jobs": [
    {
      "job_id": "job_batch_xyz789_0",
      "url": "https://example.com/video1",
      "status": "queued",
      "title": null,
      "progress": null,
      "file_info": null,
      "error": null,
      "created_at": "2025-11-06T10:00:00Z",
      "completed_at": null
    }
  ],
  "created_at": "2025-11-06T10:00:00Z",
  "started_at": null,
  "completed_at": null,
  "duration_sec": null,
  "error": null
}
```

**cURL Example**:

```bash
curl -X POST https://api.example.com/api/v1/batch/download \
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

**Python Example**:

```python
urls = [
    "https://example.com/video1",
    "https://example.com/video2",
    "https://example.com/video3"
]

response = requests.post(
    "https://api.example.com/api/v1/batch/download",
    headers={"X-API-Key": "your-api-key"},
    json={
        "urls": urls,
        "quality": "1080p",
        "concurrent_limit": 3,
        "webhook_url": "https://your-app.com/webhook"
    }
)

batch = response.json()
batch_id = batch["batch_id"]
```

---

### GET /api/v1/batch/{batch_id}

Get the status of a batch download.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| batch_id | string | Unique batch identifier |

**Response** (200 OK):

```json
{
  "batch_id": "batch_xyz789",
  "status": "running",
  "total_jobs": 3,
  "completed_jobs": 1,
  "failed_jobs": 0,
  "running_jobs": 2,
  "queued_jobs": 0,
  "jobs": [
    {
      "job_id": "job_batch_xyz789_0",
      "url": "https://example.com/video1",
      "status": "completed",
      "title": "Video 1",
      "progress": {
        "percent": 100.0
      },
      "file_info": {
        "filename": "video1.mp4",
        "size_bytes": 52428800
      },
      "error": null,
      "created_at": "2025-11-06T10:00:00Z",
      "completed_at": "2025-11-06T10:02:00Z"
    },
    {
      "job_id": "job_batch_xyz789_1",
      "url": "https://example.com/video2",
      "status": "running",
      "title": "Video 2",
      "progress": {
        "percent": 45.5
      },
      "file_info": null,
      "error": null,
      "created_at": "2025-11-06T10:00:00Z",
      "completed_at": null
    }
  ],
  "created_at": "2025-11-06T10:00:00Z",
  "started_at": "2025-11-06T10:00:05Z",
  "completed_at": null,
  "duration_sec": 120,
  "error": null
}
```

**cURL Example**:

```bash
curl -X GET https://api.example.com/api/v1/batch/batch_xyz789 \
  -H "X-API-Key: your-api-key"
```

---

### DELETE /api/v1/batch/{batch_id}

Cancel a batch download.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| batch_id | string | Unique batch identifier |

**Response** (200 OK):

```json
{
  "request_id": "batch_xyz789",
  "status": "cancelled",
  "cancelled_jobs": 2,
  "message": "Batch cancelled successfully, 2 jobs cancelled",
  "timestamp": "2025-11-06T10:00:00Z"
}
```

**cURL Example**:

```bash
curl -X DELETE https://api.example.com/api/v1/batch/batch_xyz789 \
  -H "X-API-Key: your-api-key"
```

---

## Playlist Endpoints

### GET /api/v1/playlist/info

Get playlist metadata.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | Playlist URL |

**Response** (200 OK):

```json
{
  "url": "https://youtube.com/playlist?list=PLxxx",
  "playlist_id": "PLxxx",
  "playlist_title": "Example Playlist",
  "uploader": "Channel Name",
  "video_count": 25,
  "videos": [
    {
      "id": "video1",
      "title": "Video 1",
      "url": "https://youtube.com/watch?v=video1",
      "duration": 600,
      "view_count": 10000,
      "playlist_index": 1
    }
  ]
}
```

**cURL Example**:

```bash
curl -X GET "https://api.example.com/api/v1/playlist/info?url=https://youtube.com/playlist?list=PLxxx" \
  -H "X-API-Key: your-api-key"
```

---

### POST /api/v1/playlist/download

Download playlist videos.

**Authentication**: Required

**Request Body**:

```json
{
  "url": "https://youtube.com/playlist?list=PLxxx",
  "items": "1-10",
  "start": null,
  "end": null,
  "quality": "1080p",
  "skip_downloaded": true,
  "ignore_errors": true,
  "reverse_playlist": false,
  "path_template": "playlists/{playlist}/{playlist_index:03d}-{title}.{ext}",
  "cookies_id": null,
  "timeout_sec": 3600,
  "webhook_url": "https://your-app.com/webhook"
}
```

**Parameters**:

| Field | Type | Description |
|-------|------|-------------|
| items | string | Item selection (e.g., "1-10,15,20-25") |
| start | integer | Start index |
| end | integer | End index |
| skip_downloaded | boolean | Skip already downloaded |
| ignore_errors | boolean | Continue on errors |
| reverse_playlist | boolean | Download in reverse order |

**Response** (201 Created):

```json
{
  "request_id": "req_playlist123",
  "status": "queued",
  "url": "https://youtube.com/playlist?list=PLxxx",
  "created_at": "2025-11-06T10:00:00Z",
  "message": "Playlist download job created successfully"
}
```

**cURL Example**:

```bash
curl -X POST https://api.example.com/api/v1/playlist/download \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/playlist?list=PLxxx",
    "items": "1-10",
    "quality": "1080p"
  }'
```

---

## Cookie Management

### POST /api/v1/cookies

Upload or extract cookies for authentication.

**Authentication**: Required

**Request Body (Upload Mode)**:

```json
{
  "cookies": "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t1234567890\tSESSION_TOKEN\tabc123",
  "name": "youtube_cookies"
}
```

**Request Body (Browser Extraction Mode)**:

```json
{
  "browser": "chrome",
  "name": "chrome_youtube",
  "profile": "Default"
}
```

**Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| cookies | string | Conditional | Cookies in Netscape format (required if no browser) |
| name | string | No | Cookie set name (default: "default") |
| browser | string | Conditional | Browser name (required if no cookies) |
| profile | string | No | Browser profile name |

**Supported Browsers**: chrome, firefox, edge, safari, brave, opera, chromium

**Response** (201 Created):

```json
{
  "cookie_id": "cookie_abc123",
  "name": "youtube_cookies",
  "created_at": "2025-11-06T10:00:00Z",
  "browser": "chrome",
  "domains": [".youtube.com", ".google.com"],
  "status": "active"
}
```

**cURL Example (Upload)**:

```bash
curl -X POST https://api.example.com/api/v1/cookies \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t1234567890\tSESSION\tabc",
    "name": "my_cookies"
  }'
```

**cURL Example (Browser Extraction)**:

```bash
curl -X POST https://api.example.com/api/v1/cookies \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "browser": "chrome",
    "name": "chrome_cookies"
  }'
```

**Python Example**:

```python
# Upload cookies
with open('cookies.txt', 'r') as f:
    cookies_content = f.read()

response = requests.post(
    "https://api.example.com/api/v1/cookies",
    headers={"X-API-Key": "your-api-key"},
    json={
        "cookies": cookies_content,
        "name": "my_cookies"
    }
)

cookie_id = response.json()["cookie_id"]

# Use cookies in download
download_response = requests.post(
    "https://api.example.com/api/v1/download",
    headers={"X-API-Key": "your-api-key"},
    json={
        "url": "https://youtube.com/watch?v=private_video",
        "cookies_id": cookie_id
    }
)
```

---

### GET /api/v1/cookies

List all stored cookies.

**Authentication**: Required

**Response** (200 OK):

```json
{
  "cookies": [
    {
      "cookie_id": "cookie_abc123",
      "name": "youtube_cookies",
      "created_at": "2025-11-06T10:00:00Z",
      "browser": "chrome",
      "domains": [".youtube.com"],
      "status": "active"
    },
    {
      "cookie_id": "cookie_def456",
      "name": "patreon_cookies",
      "created_at": "2025-11-05T15:30:00Z",
      "browser": null,
      "domains": [".patreon.com"],
      "status": "active"
    }
  ],
  "total": 2
}
```

**cURL Example**:

```bash
curl -X GET https://api.example.com/api/v1/cookies \
  -H "X-API-Key: your-api-key"
```

---

### GET /api/v1/cookies/{cookie_id}

Get cookie metadata.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| cookie_id | string | Unique cookie identifier |

**Response** (200 OK):

```json
{
  "cookie_id": "cookie_abc123",
  "name": "youtube_cookies",
  "created_at": "2025-11-06T10:00:00Z",
  "browser": "chrome",
  "domains": [".youtube.com", ".google.com"],
  "status": "active"
}
```

**cURL Example**:

```bash
curl -X GET https://api.example.com/api/v1/cookies/cookie_abc123 \
  -H "X-API-Key: your-api-key"
```

---

### DELETE /api/v1/cookies/{cookie_id}

Delete stored cookies.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| cookie_id | string | Unique cookie identifier |

**Response** (200 OK):

```json
{
  "id": "cookie_abc123",
  "resource_type": "cookies",
  "status": "deleted",
  "message": "Cookies successfully deleted",
  "timestamp": "2025-11-06T10:00:00Z"
}
```

**cURL Example**:

```bash
curl -X DELETE https://api.example.com/api/v1/cookies/cookie_abc123 \
  -H "X-API-Key: your-api-key"
```

---

## Metadata Endpoints

### GET /api/v1/metadata

Extract metadata without downloading.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | Video/Playlist URL |

**Response** (200 OK):

```json
{
  "url": "https://example.com/video",
  "title": "Example Video",
  "uploader": "Channel Name",
  "duration": 600,
  "view_count": 100000,
  "like_count": 5000,
  "upload_date": "20251106",
  "thumbnail": "https://example.com/thumb.jpg",
  "description": "Video description",
  "formats": [
    {
      "format_id": "137",
      "ext": "mp4",
      "quality": "1080p",
      "filesize": 104857600
    }
  ],
  "subtitles": ["en", "es", "fr"],
  "extractor": "youtube"
}
```

**cURL Example**:

```bash
curl -X GET "https://api.example.com/api/v1/metadata?url=https://example.com/video" \
  -H "X-API-Key: your-api-key"
```

---

## Health & Monitoring

### GET /api/v1/health

Service health check.

**Authentication**: Not required

**Response** (200 OK):

```json
{
  "status": "healthy",
  "timestamp": "2025-11-06T10:00:00Z",
  "version": "3.1.0",
  "uptime_seconds": 86400
}
```

**cURL Example**:

```bash
curl -X GET https://api.example.com/api/v1/health
```

---

### GET /api/v1/readyz

Readiness probe for load balancers.

**Authentication**: Not required

**Response** (200 OK):

```json
{
  "status": "ready",
  "checks": {
    "storage": "ok",
    "queue": "ok"
  }
}
```

**cURL Example**:

```bash
curl -X GET https://api.example.com/api/v1/readyz
```

---

### GET /version

Get service version information.

**Authentication**: Not required

**Response** (200 OK):

```json
{
  "version": "3.1.0",
  "app_name": "Ultimate Media Downloader",
  "build_date": "2025-11-06",
  "features": [
    "yt-dlp",
    "railway-storage",
    "auto-deletion",
    "channel-downloads",
    "batch-downloads",
    "webhooks",
    "cookie-management"
  ]
}
```

**cURL Example**:

```bash
curl -X GET https://api.example.com/version
```

---

### GET /metrics

Prometheus metrics endpoint.

**Authentication**: Not required

**Response** (200 OK):

```
# HELP jobs_total Total jobs processed
# TYPE jobs_total counter
jobs_total{status="completed"} 150
jobs_total{status="failed"} 5

# HELP jobs_duration_seconds Job duration in seconds
# TYPE jobs_duration_seconds histogram
jobs_duration_seconds_bucket{le="60.0"} 50
jobs_duration_seconds_bucket{le="300.0"} 120
jobs_duration_seconds_sum 45000
jobs_duration_seconds_count 155

# HELP bytes_transferred_total Total bytes transferred
# TYPE bytes_transferred_total counter
bytes_transferred_total 5368709120

# HELP jobs_in_flight Jobs currently running
# TYPE jobs_in_flight gauge
jobs_in_flight 3

# HELP queue_size Current queue size
# TYPE queue_size gauge
queue_size 5
```

**cURL Example**:

```bash
curl -X GET https://api.example.com/metrics
```

---

## Webhook Integration

### Webhook Events

The service sends webhook notifications for download lifecycle events when `webhook_url` is provided.

**Event Types**:

- `download.started` - Download has started
- `download.progress` - Progress update (throttled to 1 per second)
- `download.completed` - Download completed successfully
- `download.failed` - Download failed with error

### Webhook Payload

```json
{
  "event": "download.completed",
  "timestamp": "2025-11-06T10:02:30Z",
  "request_id": "req_abc123def456",
  "data": {
    "request_id": "req_abc123def456",
    "url": "https://example.com/video",
    "status": "completed",
    "file_info": {
      "filename": "video-abc123.mp4",
      "filepath": "videos/video-abc123.mp4",
      "size_bytes": 104857600,
      "download_url": "https://api.example.com/files/videos/video-abc123.mp4"
    },
    "metadata": {
      "title": "Example Video",
      "duration": 600
    }
  }
}
```

### Webhook Headers

```http
Content-Type: application/json
User-Agent: Ultimate-Media-Downloader-Webhook/3.1.0
X-Webhook-Signature: sha256=abc123def456...
```

### Signature Verification

Webhooks include an HMAC-SHA256 signature in the `X-Webhook-Signature` header.

**Python Example**:

```python
import hmac
import hashlib

def verify_webhook(payload_body, signature, secret_key):
    """Verify webhook signature."""
    expected_sig = signature.replace('sha256=', '')

    calculated_sig = hmac.new(
        secret_key.encode('utf-8'),
        payload_body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_sig, calculated_sig)

# In your webhook endpoint
@app.post("/webhook")
async def webhook_handler(request: Request):
    payload = await request.body()
    signature = request.headers.get('X-Webhook-Signature')

    if not verify_webhook(payload.decode(), signature, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(payload)
    event_type = data['event']

    # Process webhook event
    if event_type == 'download.completed':
        print(f"Download completed: {data['data']['file_info']['filename']}")
```

### Retry Logic

- **Max Retries**: 3 attempts (configurable via `WEBHOOK_MAX_RETRIES`)
- **Backoff**: Exponential (1s, 2s, 4s)
- **Timeout**: 10 seconds per request (configurable via `WEBHOOK_TIMEOUT_SEC`)
- **4xx Errors**: No retry (permanent failure)
- **5xx Errors**: Retry with backoff

---

## Complete Workflow Example

```python
import requests
import time

API_BASE = "https://api.example.com"
API_KEY = "your-api-key"
HEADERS = {"X-API-Key": API_KEY}

# 1. Upload cookies for private content
cookies_response = requests.post(
    f"{API_BASE}/api/v1/cookies",
    headers=HEADERS,
    json={"browser": "chrome", "name": "my_cookies"}
)
cookie_id = cookies_response.json()["cookie_id"]

# 2. Browse channel with filters
channel_response = requests.get(
    f"{API_BASE}/api/v1/channel/info",
    headers=HEADERS,
    params={
        "url": "https://youtube.com/@example",
        "date_after": "20250101",
        "min_duration": 300,
        "max_downloads": 10,
        "sort_by": "view_count"
    }
)
channel = channel_response.json()
print(f"Found {channel['filtered_video_count']} videos")

# 3. Download filtered channel videos
download_response = requests.post(
    f"{API_BASE}/api/v1/channel/download",
    headers=HEADERS,
    json={
        "url": "https://youtube.com/@example",
        "date_after": "20250101",
        "min_duration": 300,
        "max_downloads": 10,
        "quality": "1080p",
        "cookies_id": cookie_id,
        "webhook_url": "https://your-app.com/webhook"
    }
)
batch_id = download_response.json()["batch_id"]

# 4. Monitor batch progress
while True:
    status_response = requests.get(
        f"{API_BASE}/api/v1/batch/{batch_id}",
        headers=HEADERS
    )
    status = status_response.json()

    print(f"Progress: {status['completed_jobs']}/{status['total_jobs']}")

    if status['status'] in ['completed', 'failed']:
        break

    time.sleep(5)

print(f"Batch completed: {status['completed_jobs']} successful, {status['failed_jobs']} failed")
```

---

## Need Help?

- **Documentation**: [https://github.com/your-repo/docs](https://github.com/your-repo/docs)
- **Issues**: [https://github.com/your-repo/issues](https://github.com/your-repo/issues)
- **API Status**: Check `/api/v1/health` endpoint
- **OpenAPI Docs**: Visit `/docs` for interactive API documentation

---

**Last Updated**: 2025-11-06
**API Version**: 3.1.0
