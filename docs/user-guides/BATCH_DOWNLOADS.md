# Batch Downloads Guide

Complete guide to downloading multiple URLs concurrently with batch operations.

## Overview

Batch downloads allow you to:

- Download multiple URLs (up to 100) in a single request
- Control concurrency (1-10 simultaneous downloads)
- Monitor progress across all downloads
- Handle errors gracefully (continue or stop on error)
- Get webhook notifications for batch completion

## Quick Start

### Basic Batch Download

```bash
curl -X POST http://localhost:8080/api/v1/batch/download \
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

**Response**:
```json
{
  "batch_id": "batch_abc123",
  "status": "queued",
  "total_jobs": 3,
  "completed_jobs": 0,
  "failed_jobs": 0,
  "running_jobs": 0,
  "queued_jobs": 3
}
```

### Monitor Batch Status

```bash
curl -X GET http://localhost:8080/api/v1/batch/batch_abc123 \
  -H "X-API-Key: your-api-key"
```

### Cancel Batch

```bash
curl -X DELETE http://localhost:8080/api/v1/batch/batch_abc123 \
  -H "X-API-Key: your-api-key"
```

## Configuration Options

### Concurrency Control

```json
{
  "urls": [...],
  "concurrent_limit": 5  // 1-10, default 3
}
```

- `concurrent_limit: 1` - Sequential (one at a time)
- `concurrent_limit: 3` - Moderate (default)
- `concurrent_limit: 10` - Aggressive (max)

### Error Handling

```json
{
  "urls": [...],
  "stop_on_error": false,  // Continue on errors (default)
  "ignore_errors": true     // Don't fail batch if individual jobs fail
}
```

- `stop_on_error: true` - Stop entire batch on first error
- `stop_on_error: false` - Continue downloading remaining URLs
- `ignore_errors: true` - Individual failures don't fail batch

### Path Organization

```json
{
  "urls": [...],
  "path_template": "batch/{batch_id}/{safe_title}-{id}.{ext}"
}
```

Available variables:
- `{batch_id}` - Unique batch identifier
- `{safe_title}` - Sanitized video title
- `{id}` - Video ID
- `{ext}` - File extension
- `{uploader}` - Channel/uploader name
- `{upload_date}` - Upload date (YYYYMMDD)

## Python Examples

### Simple Batch Downloader

```python
import requests
import time

def batch_download(urls: list, api_base: str, api_key: str):
    """Download multiple URLs as a batch."""
    response = requests.post(
        f"{api_base}/api/v1/batch/download",
        headers={"X-API-Key": api_key},
        json={
            "urls": urls,
            "quality": "1080p",
            "concurrent_limit": 3
        }
    )
    batch_id = response.json()["batch_id"]

    # Monitor progress
    while True:
        status = requests.get(
            f"{api_base}/api/v1/batch/{batch_id}",
            headers={"X-API-Key": api_key}
        ).json()

        print(f"Progress: {status['completed_jobs']}/{status['total_jobs']}")

        if status['status'] in ['completed', 'failed']:
            break

        time.sleep(5)

    return status

# Usage
urls = [
    "https://example.com/video1",
    "https://example.com/video2",
    "https://example.com/video3"
]

result = batch_download(urls, "http://localhost:8080", "your-api-key")
print(f"Complete: {result['completed_jobs']} succeeded, {result['failed_jobs']} failed")
```

### Advanced Batch Manager

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests
import time

@dataclass
class BatchConfig:
    quality: str = "1080p"
    concurrent_limit: int = 3
    stop_on_error: bool = False
    ignore_errors: bool = True
    video_format: str = "mp4"
    download_subtitles: bool = False
    webhook_url: Optional[str] = None

class BatchManager:
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base
        self.headers = {"X-API-Key": api_key}

    def create_batch(
        self,
        urls: List[str],
        config: BatchConfig = None
    ) -> str:
        """Create a batch download job."""
        config = config or BatchConfig()

        payload = {
            "urls": urls,
            "quality": config.quality,
            "concurrent_limit": config.concurrent_limit,
            "stop_on_error": config.stop_on_error,
            "ignore_errors": config.ignore_errors,
            "video_format": config.video_format,
            "download_subtitles": config.download_subtitles
        }

        if config.webhook_url:
            payload["webhook_url"] = config.webhook_url

        response = requests.post(
            f"{self.api_base}/api/v1/batch/download",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()["batch_id"]

    def get_status(self, batch_id: str) -> Dict:
        """Get batch status."""
        response = requests.get(
            f"{self.api_base}/api/v1/batch/{batch_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def cancel(self, batch_id: str) -> Dict:
        """Cancel a batch."""
        response = requests.delete(
            f"{self.api_base}/api/v1/batch/{batch_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def wait_for_completion(
        self,
        batch_id: str,
        callback = None,
        poll_interval: int = 5
    ) -> Dict:
        """Wait for batch to complete."""
        while True:
            status = self.get_status(batch_id)

            if callback:
                callback(status)

            if status["status"] in ["completed", "failed"]:
                return status

            time.sleep(poll_interval)

# Usage
manager = BatchManager("http://localhost:8080", "your-api-key")

# Create batch with custom config
config = BatchConfig(
    quality="720p",
    concurrent_limit=5,
    download_subtitles=True,
    webhook_url="https://your-app.com/webhook"
)

batch_id = manager.create_batch(urls, config)

# Monitor with callback
def progress_callback(status):
    print(f"Status: {status['completed_jobs']}/{status['total_jobs']}")

final_status = manager.wait_for_completion(batch_id, progress_callback)
```

## Use Cases

### 1. Download Playlist URLs

```python
# Extract URLs from playlist
playlist_urls = [
    "https://example.com/watch?v=abc123",
    "https://example.com/watch?v=def456",
    "https://example.com/watch?v=ghi789"
]

# Download as batch
batch_id = manager.create_batch(
    playlist_urls,
    BatchConfig(concurrent_limit=5)
)
```

### 2. Download from CSV

```python
import csv

# Read URLs from CSV
urls = []
with open('downloads.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        urls.append(row['url'])

# Process in batches of 50
for i in range(0, len(urls), 50):
    batch = urls[i:i+50]
    batch_id = manager.create_batch(batch)
    print(f"Created batch {i//50 + 1}: {batch_id}")
```

### 3. Retry Failed Downloads

```python
# Get batch status
status = manager.get_status(batch_id)

# Extract failed URLs
failed_urls = [
    job['url'] for job in status['jobs']
    if job['status'] == 'failed'
]

if failed_urls:
    print(f"Retrying {len(failed_urls)} failed downloads")
    retry_batch_id = manager.create_batch(failed_urls)
```

## Batch Status Response

```json
{
  "batch_id": "batch_abc123",
  "status": "running",
  "total_jobs": 10,
  "completed_jobs": 6,
  "failed_jobs": 1,
  "running_jobs": 2,
  "queued_jobs": 1,
  "jobs": [
    {
      "job_id": "job_batch_abc123_0",
      "url": "https://example.com/video1",
      "status": "completed",
      "title": "Video 1",
      "progress": {"percent": 100.0},
      "file_info": {
        "filename": "video1.mp4",
        "filepath": "batch/batch_abc123/video1.mp4",
        "size_bytes": 52428800,
        "download_url": "http://localhost:8080/files/batch/batch_abc123/video1.mp4"
      },
      "error": null,
      "created_at": "2025-11-06T10:00:00Z",
      "completed_at": "2025-11-06T10:02:30Z"
    }
  ],
  "created_at": "2025-11-06T10:00:00Z",
  "started_at": "2025-11-06T10:00:05Z",
  "completed_at": null,
  "duration_sec": 150,
  "error": null
}
```

## Best Practices

### 1. Choose Appropriate Concurrency

```python
# Small files (audio, short videos): higher concurrency
config = BatchConfig(concurrent_limit=10)

# Large files (4K video): lower concurrency
config = BatchConfig(concurrent_limit=2)

# Mixed sizes: moderate
config = BatchConfig(concurrent_limit=5)
```

### 2. Use Webhooks for Large Batches

```python
# For batches > 10 URLs, use webhooks
config = BatchConfig(
    webhook_url="https://your-app.com/webhook"
)

batch_id = manager.create_batch(urls, config)
# No need to poll - you'll get webhook when done
```

### 3. Split Large Batches

```python
# Split >100 URLs into multiple batches
def split_batch(urls: List[str], batch_size: int = 50):
    for i in range(0, len(urls), batch_size):
        yield urls[i:i+batch_size]

for batch in split_batch(all_urls, 50):
    batch_id = manager.create_batch(batch)
    print(f"Created batch: {batch_id}")
```

### 4. Handle Errors Gracefully

```python
config = BatchConfig(
    stop_on_error=False,  # Continue on errors
    ignore_errors=True     # Don't fail batch
)

# After completion, check individual jobs
status = manager.get_status(batch_id)
for job in status['jobs']:
    if job['status'] == 'failed':
        print(f"Failed: {job['url']} - {job['error']}")
```

## Limitations

- Maximum 100 URLs per batch
- Maximum 10 concurrent downloads
- Individual job timeouts still apply (default 1800s)
- Memory usage scales with concurrent downloads
- Rate limiting applies to batch creation

## Common Issues

### Issue: Batch fails immediately

**Cause**: Invalid URLs or duplicate URLs

**Solution**: Validate URLs before creating batch

```python
# Remove duplicates
urls = list(set(urls))

# Validate format
validated = [url for url in urls if url.startswith('http')]
```

### Issue: Some jobs never complete

**Cause**: Individual job timeout or stalled downloads

**Solution**: Check individual job status and cancel if needed

```python
# Check for stuck jobs
for job in status['jobs']:
    if job['status'] == 'running':
        # Check if running too long
        # Cancel and retry if needed
```

### Issue: Memory usage too high

**Cause**: Too many concurrent downloads

**Solution**: Reduce concurrent_limit

```python
config = BatchConfig(concurrent_limit=2)
```

## Related Guides

- [Channel Downloads Guide](CHANNEL_DOWNLOADS.md)
- [Webhooks Guide](WEBHOOKS.md)
- [API Reference](../api/API_REFERENCE_COMPLETE.md)

---

**Last Updated**: 2025-11-06
