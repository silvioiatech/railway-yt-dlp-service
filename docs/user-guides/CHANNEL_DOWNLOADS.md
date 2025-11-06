# Channel Downloads Guide

Complete guide to browsing and downloading YouTube channels with advanced filtering.

## Overview

The channel download feature allows you to:

- Browse channel videos with detailed metadata
- Filter videos by date, duration, and views
- Sort videos by various criteria
- Download entire channels or filtered subsets
- Monitor download progress across all videos

## Use Cases

- **Content Archival**: Backup entire channels before they get deleted
- **Selective Downloads**: Download only recent videos or popular content
- **Research**: Collect videos matching specific criteria
- **Playlists**: Create custom collections from channel content

## Browse Channel Videos

### Basic Channel Info

```bash
curl -X GET "http://localhost:8080/api/v1/channel/info?url=https://youtube.com/@example" \
  -H "X-API-Key: your-api-key"
```

**Response**:
```json
{
  "url": "https://youtube.com/@example",
  "channel_id": "UC123456",
  "channel_name": "Example Channel",
  "description": "Channel description",
  "subscriber_count": 1000000,
  "video_count": 500,
  "filtered_video_count": 500,
  "videos": [...],
  "page": 1,
  "page_size": 20,
  "total_pages": 25
}
```

### Filter by Date Range

Download only videos from 2025:

```bash
curl -X GET "http://localhost:8080/api/v1/channel/info?\
url=https://youtube.com/@example&\
date_after=20250101&\
date_before=20251231" \
  -H "X-API-Key: your-api-key"
```

### Filter by Duration

Get only videos between 10-30 minutes:

```bash
curl -X GET "http://localhost:8080/api/v1/channel/info?\
url=https://youtube.com/@example&\
min_duration=600&\
max_duration=1800" \
  -H "X-API-Key: your-api-key"
```

### Filter by View Count

Get videos with over 100K views:

```bash
curl -X GET "http://localhost:8080/api/v1/channel/info?\
url=https://youtube.com/@example&\
min_views=100000" \
  -H "X-API-Key: your-api-key"
```

### Combined Filters

Get popular recent long-form videos:

```bash
curl -X GET "http://localhost:8080/api/v1/channel/info?\
url=https://youtube.com/@example&\
date_after=20250101&\
min_duration=1800&\
min_views=50000&\
sort_by=view_count" \
  -H "X-API-Key: your-api-key"
```

### Pagination

Browse large channels page by page:

```bash
# Get page 2 with 50 videos per page
curl -X GET "http://localhost:8080/api/v1/channel/info?\
url=https://youtube.com/@example&\
page=2&\
page_size=50" \
  -H "X-API-Key: your-api-key"
```

## Download Channel Videos

### Download Entire Channel

```bash
curl -X POST http://localhost:8080/api/v1/channel/download \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/@example",
    "quality": "1080p"
  }'
```

### Download Filtered Videos

Download only recent popular videos:

```bash
curl -X POST http://localhost:8080/api/v1/channel/download \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/@example",
    "date_after": "20250101",
    "min_views": 10000,
    "sort_by": "view_count",
    "max_downloads": 50,
    "quality": "1080p"
  }'
```

### With Custom Path Template

Organize downloads by upload date:

```bash
curl -X POST http://localhost:8080/api/v1/channel/download \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/@example",
    "quality": "720p",
    "path_template": "channels/{uploader}/{upload_date}-{title}.{ext}"
  }'
```

## Python Examples

### Complete Channel Browser

```python
import requests
from typing import List, Dict

class ChannelBrowser:
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base
        self.headers = {"X-API-Key": api_key}

    def browse_channel(
        self,
        url: str,
        date_after: str = None,
        min_duration: int = None,
        min_views: int = None,
        sort_by: str = "upload_date",
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """Browse channel with filters."""
        params = {
            "url": url,
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by
        }

        if date_after:
            params["date_after"] = date_after
        if min_duration:
            params["min_duration"] = min_duration
        if min_views:
            params["min_views"] = min_views

        response = requests.get(
            f"{self.api_base}/api/v1/channel/info",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()

    def get_all_videos(
        self,
        url: str,
        **filters
    ) -> List[Dict]:
        """Get all videos from channel with pagination."""
        videos = []
        page = 1

        while True:
            data = self.browse_channel(url, page=page, **filters)
            videos.extend(data["videos"])

            if not data["has_next"]:
                break

            page += 1

        return videos

# Usage
browser = ChannelBrowser("http://localhost:8080", "your-api-key")

# Get all videos from 2025
videos = browser.get_all_videos(
    "https://youtube.com/@example",
    date_after="20250101",
    sort_by="view_count"
)

print(f"Found {len(videos)} videos")
for video in videos[:10]:
    print(f"- {video['title']} ({video['view_count']} views)")
```

### Channel Archiver

```python
import requests
import time
from datetime import datetime

class ChannelArchiver:
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base
        self.headers = {"X-API-Key": api_key}

    def download_channel(
        self,
        url: str,
        filters: Dict = None,
        quality: str = "1080p",
        webhook_url: str = None
    ) -> str:
        """Start channel download job."""
        payload = {
            "url": url,
            "quality": quality,
            **(filters or {})
        }

        if webhook_url:
            payload["webhook_url"] = webhook_url

        response = requests.post(
            f"{self.api_base}/api/v1/channel/download",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()["batch_id"]

    def monitor_batch(self, batch_id: str):
        """Monitor batch download progress."""
        while True:
            response = requests.get(
                f"{self.api_base}/api/v1/batch/{batch_id}",
                headers=self.headers
            )
            response.raise_for_status()
            status = response.json()

            completed = status["completed_jobs"]
            failed = status["failed_jobs"]
            total = status["total_jobs"]

            print(f"Progress: {completed}/{total} completed, {failed} failed")

            if status["status"] in ["completed", "failed"]:
                return status

            time.sleep(5)

# Usage
archiver = ChannelArchiver("http://localhost:8080", "your-api-key")

# Download all videos from 2025 with over 10K views
batch_id = archiver.download_channel(
    "https://youtube.com/@example",
    filters={
        "date_after": "20250101",
        "min_views": 10000,
        "max_downloads": 100
    },
    quality="1080p"
)

print(f"Started batch: {batch_id}")

# Monitor progress
final_status = archiver.monitor_batch(batch_id)
print(f"Download complete: {final_status['completed_jobs']} successful")
```

## Advanced Filtering

### Date Range Filtering

```python
# Videos from specific month
date_after = "20250301"  # March 1, 2025
date_before = "20250331"  # March 31, 2025

# Videos from last quarter of 2024
date_after = "20241001"
date_before = "20241231"
```

### Duration Filtering

```python
# Short videos (<5 minutes)
max_duration = 300

# Medium videos (5-20 minutes)
min_duration = 300
max_duration = 1200

# Long-form content (>30 minutes)
min_duration = 1800
```

### View Count Filtering

```python
# Viral videos (>1M views)
min_views = 1000000

# Moderately popular (10K-100K views)
min_views = 10000
max_views = 100000

# Hidden gems (<1K views)
max_views = 1000
```

### Sorting Options

```python
# Most recent first
sort_by = "upload_date"  # Default, newest first

# Most popular first
sort_by = "view_count"  # Highest views first

# Longest first
sort_by = "duration"  # Longest videos first

# Alphabetical
sort_by = "title"  # A-Z
```

## Response Format

### Channel Info Response

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
      "like_count": 2500,
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

### Channel Download Response

```json
{
  "batch_id": "batch_abc123",
  "status": "queued",
  "total_jobs": 50,
  "completed_jobs": 0,
  "failed_jobs": 0,
  "running_jobs": 0,
  "queued_jobs": 50,
  "jobs": [...],
  "created_at": "2025-11-06T10:00:00Z"
}
```

## Best Practices

### 1. Browse Before Downloading

Always browse the channel first to see what you'll download:

```python
# 1. Browse to see what matches
info = browser.browse_channel(
    "https://youtube.com/@example",
    date_after="20250101",
    min_views=10000
)

print(f"Will download {info['filtered_video_count']} videos")

# 2. If acceptable, proceed with download
if info['filtered_video_count'] <= 100:
    batch_id = archiver.download_channel(
        "https://youtube.com/@example",
        filters={"date_after": "20250101", "min_views": 10000}
    )
```

### 2. Use max_downloads Limit

Prevent accidentally downloading too many videos:

```python
# Limit to 50 most popular videos
payload = {
    "url": "https://youtube.com/@example",
    "sort_by": "view_count",
    "max_downloads": 50,
    "quality": "1080p"
}
```

### 3. Organize with Path Templates

Use meaningful directory structures:

```python
# By date
"channels/{uploader}/{upload_date}-{title}.{ext}"

# By year and month
"channels/{uploader}/{upload_date[:6]}/{title}.{ext}"

# By view count range
"channels/{uploader}/popular/{title}.{ext}"  # for min_views filter
```

### 4. Use Webhooks for Long Jobs

Get notified when channel downloads complete:

```python
batch_id = archiver.download_channel(
    "https://youtube.com/@example",
    quality="1080p",
    webhook_url="https://your-app.com/webhook"
)
```

## Common Issues

### Issue: Too many videos

**Problem**: Channel has thousands of videos

**Solution**: Use filters to reduce count
```python
# Only videos from 2025
"date_after": "20250101"

# Only popular videos
"min_views": 50000

# Limit total downloads
"max_downloads": 100
```

### Issue: Slow browsing

**Problem**: Channel info request is slow

**Solution**: This is normal for large channels. yt-dlp must fetch all videos before filtering.

### Issue: Private videos failing

**Problem**: Some videos require authentication

**Solution**: Upload cookies before downloading
```bash
# Upload cookies
curl -X POST http://localhost:8080/api/v1/cookies \
  -H "X-API-Key: your-api-key" \
  -d '{"browser": "chrome", "name": "my_cookies"}'

# Use cookies in download
curl -X POST http://localhost:8080/api/v1/channel/download \
  -H "X-API-Key: your-api-key" \
  -d '{
    "url": "https://youtube.com/@example",
    "cookies_id": "cookie_abc123"
  }'
```

## Limitations

- Maximum 1000 videos per channel download (use `max_downloads`)
- Pagination limited to 100 items per page
- Date filtering uses upload_date field (may not be exact)
- View count filtering may not be accurate for very recent videos
- Some platforms may not support all filter types

## Related Guides

- [Batch Downloads Guide](BATCH_DOWNLOADS.md) - Managing multiple downloads
- [Webhooks Guide](WEBHOOKS.md) - Real-time notifications
- [Authentication Guide](AUTHENTICATION.md) - Cookie management

---

**Last Updated**: 2025-11-06
