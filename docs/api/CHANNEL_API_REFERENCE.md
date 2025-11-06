# Channel API Reference

Quick reference for the Channel Downloads API endpoints.

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [GET /api/v1/channel/info](#get-apiv1channelinfo)
  - [POST /api/v1/channel/download](#post-apiv1channeldownload)
- [Models](#models)
- [Error Codes](#error-codes)
- [Examples](#examples)

## Overview

The Channel API allows you to browse and download videos from YouTube channels and other platforms with advanced filtering capabilities.

**Base URL**: `http://your-domain/api/v1`

**Features**:
- Browse channel videos without downloading
- Filter by date range, duration, and view count
- Sort by various criteria
- Pagination support
- Batch download filtered videos
- Full quality and format control

## Authentication

All endpoints require API key authentication via header:

```
X-API-Key: your-api-key-here
```

## Endpoints

### GET /api/v1/channel/info

Get channel information with filtering and pagination.

**URL**: `/api/v1/channel/info`

**Method**: `GET`

**Auth Required**: YES

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | YES | - | Channel URL |
| `date_after` | string | NO | - | Filter videos after date (YYYYMMDD) |
| `date_before` | string | NO | - | Filter videos before date (YYYYMMDD) |
| `min_duration` | integer | NO | - | Minimum video duration (seconds) |
| `max_duration` | integer | NO | - | Maximum video duration (seconds) |
| `min_views` | integer | NO | - | Minimum view count |
| `max_views` | integer | NO | - | Maximum view count |
| `sort_by` | string | NO | `upload_date` | Sort field: `upload_date`, `view_count`, `duration`, `title` |
| `page` | integer | NO | `1` | Page number (>= 1) |
| `page_size` | integer | NO | `20` | Items per page (1-100) |

#### Success Response (200 OK)

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
    "min_duration": 300,
    "sort_by": "view_count"
  },
  "extractor": "youtube"
}
```

#### Error Responses

- **400 Bad Request**: Invalid parameters
- **401 Unauthorized**: Invalid or missing API key
- **422 Unprocessable Entity**: Failed to extract channel info
- **500 Internal Server Error**: Server error

#### cURL Example

```bash
curl -X GET \
  "http://localhost:8080/api/v1/channel/info?url=https://youtube.com/@example&date_after=20250101&min_duration=300&sort_by=view_count&page=1" \
  -H "X-API-Key: your-api-key"
```

---

### POST /api/v1/channel/download

Download filtered channel videos as a batch job.

**URL**: `/api/v1/channel/download`

**Method**: `POST`

**Auth Required**: YES

**Content-Type**: `application/json`

#### Request Body

```json
{
  "url": "https://youtube.com/@example",
  "date_after": "20250101",
  "date_before": "20251231",
  "min_duration": 300,
  "max_duration": 3600,
  "min_views": 10000,
  "max_views": null,
  "sort_by": "view_count",
  "max_downloads": 50,
  "quality": "1080p",
  "custom_format": null,
  "video_format": "mp4",
  "audio_only": false,
  "audio_format": "mp3",
  "audio_quality": "192",
  "download_subtitles": true,
  "subtitle_languages": ["en", "es"],
  "subtitle_format": "srt",
  "embed_subtitles": false,
  "auto_subtitles": false,
  "write_thumbnail": false,
  "embed_thumbnail": false,
  "embed_metadata": true,
  "write_info_json": false,
  "skip_downloaded": true,
  "ignore_errors": true,
  "path_template": "channels/{uploader}/{upload_date}-{title}.{ext}",
  "cookies_id": null,
  "timeout_sec": 3600,
  "webhook_url": null
}
```

#### Request Body Parameters

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | YES | - | Channel URL |
| `date_after` | string | NO | - | Filter videos after date (YYYYMMDD) |
| `date_before` | string | NO | - | Filter videos before date (YYYYMMDD) |
| `min_duration` | integer | NO | - | Minimum duration (seconds) |
| `max_duration` | integer | NO | - | Maximum duration (seconds) |
| `min_views` | integer | NO | - | Minimum view count |
| `max_views` | integer | NO | - | Maximum view count |
| `sort_by` | string | NO | `upload_date` | Sort field |
| `max_downloads` | integer | NO | - | Maximum videos to download (1-1000) |
| `quality` | string | NO | `best` | Quality preset |
| `video_format` | string | NO | `mp4` | Video format |
| `audio_only` | boolean | NO | `false` | Extract audio only |
| `download_subtitles` | boolean | NO | `false` | Download subtitles |
| `path_template` | string | NO | - | Output path template |

See [ChannelDownloadRequest model](#channeldownloadrequest) for all fields.

#### Success Response (201 Created)

```json
{
  "batch_id": "batch_abc123",
  "status": "queued",
  "total_jobs": 50,
  "completed_jobs": 0,
  "failed_jobs": 0,
  "running_jobs": 0,
  "queued_jobs": 50,
  "jobs": [],
  "created_at": "2025-11-06T10:00:00Z",
  "started_at": null,
  "completed_at": null,
  "duration_sec": null,
  "error": null
}
```

#### Error Responses

- **400 Bad Request**: No videos match filters, invalid parameters
- **401 Unauthorized**: Invalid or missing API key
- **422 Unprocessable Entity**: Failed to extract channel info
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

#### cURL Example

```bash
curl -X POST \
  "http://localhost:8080/api/v1/channel/download" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/@example",
    "sort_by": "view_count",
    "max_downloads": 50,
    "quality": "1080p",
    "download_subtitles": true
  }'
```

## Models

### ChannelInfoResponse

Complete channel information with filtered videos.

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Channel URL |
| `channel_id` | string | Unique channel ID |
| `channel_name` | string | Channel display name |
| `description` | string | Channel description |
| `subscriber_count` | integer | Subscriber count |
| `video_count` | integer | Total videos in channel |
| `filtered_video_count` | integer | Videos matching filters |
| `videos` | array | List of video objects |
| `page` | integer | Current page number |
| `page_size` | integer | Items per page |
| `total_pages` | integer | Total pages available |
| `has_next` | boolean | More pages available |
| `has_previous` | boolean | Previous pages available |
| `filters_applied` | object | Active filters |
| `extractor` | string | yt-dlp extractor name |

### ChannelDownloadRequest

Request to download channel videos.

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `url` | string | YES | - | Valid HTTP(S) URL |
| `date_after` | string | NO | - | YYYYMMDD format |
| `date_before` | string | NO | - | YYYYMMDD format |
| `min_duration` | integer | NO | - | >= 0 |
| `max_duration` | integer | NO | - | >= min_duration |
| `min_views` | integer | NO | - | >= 0 |
| `max_views` | integer | NO | - | >= min_views |
| `sort_by` | string | NO | `upload_date` | upload_date, view_count, duration, title |
| `max_downloads` | integer | NO | - | 1-1000 |
| `quality` | string | NO | `best` | best, 4k, 1080p, 720p, 480p, 360p, audio |
| `audio_only` | boolean | NO | `false` | - |
| `download_subtitles` | boolean | NO | `false` | - |
| `subtitle_languages` | array | NO | `["en"]` | 2-3 letter codes |
| `embed_metadata` | boolean | NO | `true` | - |

### BatchDownloadResponse

Response for batch download operations.

| Field | Type | Description |
|-------|------|-------------|
| `batch_id` | string | Unique batch identifier |
| `status` | string | Batch status (queued, running, completed, failed) |
| `total_jobs` | integer | Total number of jobs |
| `completed_jobs` | integer | Completed jobs |
| `failed_jobs` | integer | Failed jobs |
| `running_jobs` | integer | Currently running jobs |
| `queued_jobs` | integer | Queued jobs |
| `jobs` | array | Individual job details |
| `created_at` | datetime | Batch creation time |
| `started_at` | datetime | Batch start time |
| `completed_at` | datetime | Batch completion time |

## Error Codes

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | Success | Request completed successfully |
| 201 | Created | Resource created (batch job) |
| 400 | Bad Request | Invalid parameters, validation errors |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Channel extraction failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Queue is full |

### Error Response Format

```json
{
  "error": "ValidationError",
  "message": "Invalid parameter: date_after",
  "details": {
    "field": "date_after",
    "constraint": "Date must be in YYYYMMDD format"
  },
  "timestamp": "2025-11-06T10:00:00Z",
  "status_code": 400
}
```

## Examples

### Example 1: Browse Recent Videos

Get videos from the last 30 days, sorted by views:

```bash
curl -X GET \
  "http://localhost:8080/api/v1/channel/info?url=https://youtube.com/@example&date_after=20251007&sort_by=view_count" \
  -H "X-API-Key: your-api-key"
```

### Example 2: Download Top 10 Long-Form Videos

Download the 10 most-viewed videos over 10 minutes:

```bash
curl -X POST \
  "http://localhost:8080/api/v1/channel/download" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/@example",
    "min_duration": 600,
    "sort_by": "view_count",
    "max_downloads": 10,
    "quality": "1080p"
  }'
```

### Example 3: Download Videos from Specific Month

Download all videos from January 2025:

```bash
curl -X POST \
  "http://localhost:8080/api/v1/channel/download" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/@example",
    "date_after": "20250101",
    "date_before": "20250131",
    "sort_by": "upload_date",
    "quality": "best"
  }'
```

### Example 4: Python Client

```python
import httpx
import asyncio

async def download_channel():
    async with httpx.AsyncClient() as client:
        # Browse channel
        response = await client.get(
            "http://localhost:8080/api/v1/channel/info",
            params={
                "url": "https://youtube.com/@example",
                "sort_by": "view_count",
                "page_size": 10
            },
            headers={"X-API-Key": "your-api-key"}
        )
        info = response.json()
        print(f"Found {info['filtered_video_count']} videos")

        # Download top videos
        response = await client.post(
            "http://localhost:8080/api/v1/channel/download",
            json={
                "url": "https://youtube.com/@example",
                "sort_by": "view_count",
                "max_downloads": 10,
                "quality": "1080p"
            },
            headers={
                "X-API-Key": "your-api-key",
                "Content-Type": "application/json"
            }
        )
        batch = response.json()
        print(f"Batch job created: {batch['batch_id']}")

asyncio.run(download_channel())
```

## Rate Limits

Default rate limits (configurable):
- Channel info: 100 requests/minute
- Channel download: 10 requests/minute
- Batch size limit: 1000 videos per request

## Support

For issues or questions:
- GitHub: [repository URL]
- Documentation: [docs URL]
- API Status: GET /api/v1/health

---

**API Version**: 3.0.0
**Last Updated**: 2025-11-06
**Status**: Stable
