# Batch Downloads Quick Start Guide

**Version:** 1.0
**Last Updated:** 2025-11-06

## Overview

The Batch Downloads feature allows you to download multiple videos concurrently with a single API call. This guide provides quick examples to get you started.

## Basic Usage

### 1. Create a Batch Download

**Endpoint:** `POST /api/v1/batch/download`

**Minimal Example:**
```bash
curl -X POST "http://localhost:8080/api/v1/batch/download" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "https://www.youtube.com/watch?v=9bZkp7q19f0"
    ]
  }'
```

**Response:**
```json
{
  "batch_id": "batch_abc123xyz",
  "status": "queued",
  "total_jobs": 2,
  "completed_jobs": 0,
  "failed_jobs": 0,
  "running_jobs": 0,
  "queued_jobs": 2,
  "jobs": [
    {
      "job_id": "batch_abc123xyz_job_000",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "status": "queued",
      "created_at": "2025-11-06T10:00:00Z"
    }
  ],
  "created_at": "2025-11-06T10:00:00Z"
}
```

Save the `batch_id` for checking status later.

### 2. Check Batch Status

**Endpoint:** `GET /api/v1/batch/{batch_id}`

```bash
curl -X GET "http://localhost:8080/api/v1/batch/batch_abc123xyz" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "batch_id": "batch_abc123xyz",
  "status": "running",
  "total_jobs": 2,
  "completed_jobs": 1,
  "failed_jobs": 0,
  "running_jobs": 1,
  "queued_jobs": 0,
  "jobs": [
    {
      "job_id": "batch_abc123xyz_job_000",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "status": "completed",
      "title": "Rick Astley - Never Gonna Give You Up",
      "file_info": {
        "filename": "rick-astley-never-gonna-give-you-up.mp4",
        "file_url": "http://localhost:8080/files/batch_abc123xyz/rick-astley-never-gonna-give-you-up.mp4",
        "size_bytes": 52428800
      },
      "completed_at": "2025-11-06T10:05:00Z"
    },
    {
      "job_id": "batch_abc123xyz_job_001",
      "status": "running",
      "progress": {
        "percent": 45.2,
        "downloaded_bytes": 23756800,
        "speed": 1048576.0,
        "eta": 27
      }
    }
  ]
}
```

### 3. Cancel a Batch

**Endpoint:** `DELETE /api/v1/batch/{batch_id}`

```bash
curl -X DELETE "http://localhost:8080/api/v1/batch/batch_abc123xyz" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "request_id": "batch_abc123xyz",
  "status": "cancelled",
  "cancelled_jobs": 1,
  "message": "Batch cancelled successfully, 1 jobs cancelled",
  "timestamp": "2025-11-06T10:10:00Z"
}
```

## Advanced Options

### Concurrent Download Limit

Control how many downloads run simultaneously (1-10):

```json
{
  "urls": ["url1", "url2", "url3", "url4", "url5"],
  "concurrent_limit": 2
}
```

With `concurrent_limit=2`:
- URLs 1-2 start immediately
- URLs 3-5 wait in queue
- When URL 1 completes, URL 3 starts

### Stop on First Error

Stop the entire batch if any download fails:

```json
{
  "urls": ["url1", "url2", "url3"],
  "stop_on_error": true
}
```

Default is `false` (continue despite errors).

### Quality and Format Options

```json
{
  "urls": ["url1", "url2"],
  "quality": "1080p",
  "video_format": "mp4",
  "audio_only": false
}
```

**Quality presets:**
- `best` (default)
- `4k`, `1080p`, `720p`, `480p`, `360p`
- `audio` (audio only)

### Audio-Only Downloads

```json
{
  "urls": ["url1", "url2"],
  "audio_only": true,
  "audio_format": "mp3",
  "audio_quality": "192"
}
```

**Audio formats:** `mp3`, `m4a`, `flac`, `wav`, `opus`, `aac`
**Quality (kbps):** `96`, `128`, `192`, `256`, `320`

### Subtitles

```json
{
  "urls": ["url1", "url2"],
  "download_subtitles": true,
  "subtitle_languages": ["en", "es", "fr"],
  "subtitle_format": "srt",
  "embed_subtitles": true
}
```

### Custom Path Template

Organize downloads with custom paths:

```json
{
  "urls": ["url1", "url2"],
  "path_template": "batch/{batch_id}/{safe_title}-{id}.{ext}"
}
```

**Available variables:**
- `{batch_id}`: Batch identifier
- `{safe_title}`: Sanitized video title
- `{title}`: Original video title
- `{id}`: Video ID
- `{ext}`: File extension
- `{uploader}`: Channel/uploader name
- `{upload_date}`: Upload date (YYYYMMDD)

### Thumbnails and Metadata

```json
{
  "urls": ["url1", "url2"],
  "write_thumbnail": true,
  "embed_thumbnail": true,
  "embed_metadata": true,
  "write_info_json": true
}
```

## Complete Example

Full-featured batch download:

```bash
curl -X POST "http://localhost:8080/api/v1/batch/download" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "https://www.youtube.com/watch?v=9bZkp7q19f0",
      "https://www.youtube.com/watch?v=kJQP7kiw5Fk"
    ],
    "quality": "1080p",
    "video_format": "mp4",
    "audio_only": false,
    "download_subtitles": true,
    "subtitle_languages": ["en"],
    "embed_subtitles": true,
    "write_thumbnail": true,
    "embed_thumbnail": true,
    "embed_metadata": true,
    "concurrent_limit": 2,
    "stop_on_error": false,
    "path_template": "batch/{batch_id}/{safe_title}.{ext}",
    "timeout_sec": 1800
  }'
```

## Python Client Example

```python
import requests
import time

API_URL = "http://localhost:8080/api/v1"
API_KEY = "your-api-key"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Create batch
response = requests.post(
    f"{API_URL}/batch/download",
    headers=headers,
    json={
        "urls": [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=9bZkp7q19f0"
        ],
        "quality": "1080p",
        "concurrent_limit": 2
    }
)

batch = response.json()
batch_id = batch["batch_id"]
print(f"Batch created: {batch_id}")

# Poll for completion
while True:
    response = requests.get(
        f"{API_URL}/batch/{batch_id}",
        headers=headers
    )

    batch = response.json()
    status = batch["status"]
    completed = batch["completed_jobs"]
    total = batch["total_jobs"]

    print(f"Status: {status} ({completed}/{total} completed)")

    if status in ["completed", "failed", "cancelled"]:
        break

    time.sleep(5)

# Print results
for job in batch["jobs"]:
    if job["status"] == "completed":
        print(f"✓ {job['title']}")
        print(f"  File: {job['file_info']['file_url']}")
    elif job["status"] == "failed":
        print(f"✗ {job['url']}")
        print(f"  Error: {job['error']}")
```

## JavaScript/TypeScript Example

```typescript
const API_URL = "http://localhost:8080/api/v1";
const API_KEY = "your-api-key";

const headers = {
  "X-API-Key": API_KEY,
  "Content-Type": "application/json"
};

// Create batch
const createBatch = async (urls: string[]) => {
  const response = await fetch(`${API_URL}/batch/download`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      urls,
      quality: "1080p",
      concurrent_limit: 2
    })
  });

  return response.json();
};

// Check batch status
const getBatchStatus = async (batchId: string) => {
  const response = await fetch(`${API_URL}/batch/${batchId}`, {
    method: "GET",
    headers
  });

  return response.json();
};

// Wait for completion
const waitForCompletion = async (batchId: string) => {
  while (true) {
    const batch = await getBatchStatus(batchId);

    console.log(`Status: ${batch.status} (${batch.completed_jobs}/${batch.total_jobs})`);

    if (["completed", "failed", "cancelled"].includes(batch.status)) {
      return batch;
    }

    await new Promise(resolve => setTimeout(resolve, 5000));
  }
};

// Usage
const urls = [
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "https://www.youtube.com/watch?v=9bZkp7q19f0"
];

const batch = await createBatch(urls);
console.log(`Batch created: ${batch.batch_id}`);

const result = await waitForCompletion(batch.batch_id);
console.log("Batch completed:", result);
```

## Error Handling

### Common Errors

**Batch too large:**
```json
{
  "error": "RequestEntityTooLarge",
  "message": "Batch size exceeds maximum of 100 URLs",
  "status_code": 413
}
```

**Invalid URLs:**
```json
{
  "error": "ValidationError",
  "message": "Invalid URL format at index 2",
  "status_code": 422
}
```

**Queue full:**
```json
{
  "error": "ServiceUnavailable",
  "message": "Queue at capacity: 50 active jobs",
  "status_code": 503
}
```

### Handling Partial Failures

With `stop_on_error=false` (default), some jobs may fail while others succeed:

```json
{
  "batch_id": "batch_abc123",
  "status": "completed",
  "completed_jobs": 8,
  "failed_jobs": 2,
  "jobs": [
    {
      "job_id": "batch_abc123_job_005",
      "status": "failed",
      "error": "Video unavailable"
    }
  ]
}
```

Check individual job status and errors in the response.

## Best Practices

### 1. Use Appropriate Concurrent Limits

- **2-3 downloads:** Good for most cases
- **1 download:** For rate-limited sources
- **5-10 downloads:** For high-bandwidth scenarios

### 2. Monitor Progress

Poll batch status every 5-10 seconds:

```python
while batch["status"] not in ["completed", "failed", "cancelled"]:
    time.sleep(5)
    batch = get_batch_status(batch_id)
```

### 3. Handle Errors Gracefully

```python
if batch["failed_jobs"] > 0:
    for job in batch["jobs"]:
        if job["status"] == "failed":
            print(f"Failed: {job['url']}")
            print(f"Error: {job['error']}")
            # Retry logic here
```

### 4. Clean Up Old Batches

Batch state is retained in memory. After processing, you may want to track batch IDs and clean up periodically.

### 5. Optimize Path Templates

Use organized paths for easier file management:

```json
{
  "path_template": "batch/{batch_id}/{upload_date}-{safe_title}.{ext}"
}
```

## Limits and Constraints

| Parameter | Limit | Description |
|-----------|-------|-------------|
| Max URLs per batch | 100 | Hard limit enforced |
| Min URLs per batch | 1 | At least one URL required |
| Concurrent limit | 1-10 | Per-batch concurrency |
| Timeout per job | 60-7200 sec | Individual job timeout |
| Batch retention | 24 hours | In-memory state retention |

## Troubleshooting

### Batch Stuck in "queued"

**Cause:** Queue manager not started
**Solution:** Check application logs, restart if necessary

### Batch Stuck in "running"

**Cause:** Jobs deadlocked or crashed
**Solution:** Cancel batch and retry

### High Memory Usage

**Cause:** Too many active batches
**Solution:**
- Reduce concurrent batches
- Implement batch cleanup
- Consider database migration

### Slow Processing

**Cause:** Network or source limitations
**Solution:**
- Reduce concurrent_limit
- Check source rate limits
- Verify network bandwidth

## Need Help?

- Documentation: `/docs/implementation/BATCH_DOWNLOADS_IMPLEMENTATION.md`
- API Reference: `http://localhost:8080/docs` (Swagger UI)
- GitHub Issues: [Create an issue](https://github.com/your-repo/issues)

## Related Endpoints

- Single download: `POST /api/v1/download`
- Check job status: `GET /api/v1/download/{job_id}`
- Cancel job: `DELETE /api/v1/download/{job_id}`
- Metadata extraction: `GET /api/v1/metadata`
