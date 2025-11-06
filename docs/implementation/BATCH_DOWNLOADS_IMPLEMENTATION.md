# Batch Downloads Implementation

**Date:** 2025-11-06
**Version:** 1.0
**Status:** Complete

## Overview

This document describes the implementation of the Batch Downloads feature for the Ultimate Media Downloader (v3.0.0). The feature allows users to submit multiple URLs for concurrent download with configurable concurrency limits, error handling strategies, and real-time progress tracking.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│              Batch Download Architecture                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  API Layer: /api/v1/batch/*                            │
│    - POST /batch/download    (Create batch)            │
│    - GET /batch/{batch_id}   (Get status)              │
│    - DELETE /batch/{batch_id} (Cancel batch)           │
│                          │                              │
│                          ▼                              │
│  Service Layer: BatchService                           │
│    - create_batch()      (Create & queue jobs)         │
│    - get_batch_status()  (Aggregate status)            │
│    - cancel_batch()      (Cancel all jobs)             │
│    - _process_batch()    (Concurrent processing)       │
│                          │                              │
│                          ▼                              │
│  Queue Manager: QueueManager                           │
│    - submit_job()        (Submit to thread pool)       │
│    - cancel_job()        (Cancel individual job)       │
│                          │                              │
│                          ▼                              │
│  State Manager: JobStateManager                        │
│    - create_job()        (Create job state)            │
│    - get_job()           (Retrieve job status)         │
│    - update_job()        (Update progress)             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Request/Response Models

**File:** `app/models/requests.py`

The `BatchDownloadRequest` model was already defined with the following fields:

```python
class BatchDownloadRequest(BaseModel):
    urls: List[str]                    # 1-100 URLs
    quality: Optional[QualityPreset]    # Video quality
    video_format: Optional[VideoFormat] # Container format
    audio_only: bool                    # Extract audio only
    audio_format: Optional[AudioFormat] # Audio format
    audio_quality: Optional[str]        # Audio bitrate

    # Subtitle options
    download_subtitles: bool
    subtitle_languages: Optional[List[str]]
    subtitle_format: Optional[SubtitleFormat]
    embed_subtitles: bool

    # Thumbnail options
    write_thumbnail: bool
    embed_thumbnail: bool

    # Metadata options
    embed_metadata: bool
    write_info_json: bool

    # Batch-specific options
    concurrent_limit: int               # 1-10, max concurrent downloads
    stop_on_error: bool                 # Stop batch on first error
    ignore_errors: bool                 # Continue on individual errors

    # Path template
    path_template: Optional[str]

    # Authentication & webhook
    cookies_id: Optional[str]
    timeout_sec: int
    webhook_url: Optional[HttpUrl]
```

**File:** `app/models/responses.py`

Response models already existed:

- `BatchDownloadResponse`: Initial batch creation response
- `JobInfo`: Individual job information within batch
- `BatchStatusResponse`: Extended status with progress percentage

### 2. Service Layer

**File:** `app/services/batch_service.py` (New)

#### BatchState Class

Thread-safe container for batch metadata:

```python
class BatchState:
    batch_id: str
    urls: List[str]
    request: BatchDownloadRequest
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    job_ids: List[str]
    error_message: Optional[str]
```

#### BatchService Class

Main service class with the following methods:

**create_batch(request: BatchDownloadRequest) -> BatchDownloadResponse**
- Generates unique batch ID with format `batch_{uuid}`
- Creates individual `DownloadRequest` objects for each URL
- Creates job states via `JobStateManager`
- Substitutes `{batch_id}` in path templates
- Launches background processing task
- Returns initial batch status

**_process_batch(batch_id, job_ids, concurrent_limit, stop_on_error)**
- Uses `asyncio.Semaphore` for concurrency control
- Submits jobs to `QueueManager` with rate limiting
- Polls job status until completion
- Implements `stop_on_error` logic with `asyncio.Event`
- Updates batch status (running → completed/failed)

**get_batch_status(batch_id: str) -> BatchDownloadResponse**
- Retrieves all job states for the batch
- Calculates aggregate statistics:
  - `completed_jobs`: Jobs with status COMPLETED
  - `failed_jobs`: Jobs with status FAILED
  - `running_jobs`: Jobs with status RUNNING
  - `queued_jobs`: Jobs with status QUEUED
  - `cancelled_jobs`: Jobs with status CANCELLED
- Builds `JobInfo` objects with progress and file information
- Returns comprehensive batch status

**cancel_batch(batch_id: str) -> int**
- Iterates through all jobs in batch
- Cancels non-terminal jobs (QUEUED, RUNNING)
- Marks jobs as CANCELLED in state manager
- Returns count of cancelled jobs

**cleanup_old_batches(max_age_hours: int) -> int**
- Removes completed/failed batches older than threshold
- Helps prevent memory leaks in long-running services

#### Thread Safety

All batch state operations are protected by `threading.RLock()` to ensure thread-safe access across:
- Queue manager threads
- FastAPI worker threads
- Background processing tasks

### 3. API Endpoints

**File:** `app/api/v1/batch.py` (New)

#### POST /api/v1/batch/download

Creates a new batch download job.

**Request Body:**
```json
{
  "urls": [
    "https://example.com/video1",
    "https://example.com/video2",
    "https://example.com/video3"
  ],
  "quality": "1080p",
  "concurrent_limit": 3,
  "stop_on_error": false,
  "audio_only": false,
  "download_subtitles": false
}
```

**Response:** `202 Accepted`
```json
{
  "batch_id": "batch_abc123xyz",
  "status": "queued",
  "total_jobs": 3,
  "completed_jobs": 0,
  "failed_jobs": 0,
  "running_jobs": 0,
  "queued_jobs": 3,
  "jobs": [
    {
      "job_id": "batch_abc123xyz_job_000",
      "url": "https://example.com/video1",
      "status": "queued",
      "created_at": "2025-11-06T10:00:00Z"
    }
  ],
  "created_at": "2025-11-06T10:00:00Z"
}
```

**Validations:**
- Maximum 100 URLs per batch (413 error if exceeded)
- Minimum 1 URL required (422 error if empty)
- URL format validation (per DownloadRequest rules)
- Duplicate URL detection

**Error Codes:**
- `422 Unprocessable Entity`: Invalid request data
- `413 Payload Too Large`: Batch exceeds 100 URLs
- `503 Service Unavailable`: Queue is full

#### GET /api/v1/batch/{batch_id}

Retrieves current status of a batch download.

**Response:** `200 OK`
```json
{
  "batch_id": "batch_abc123xyz",
  "status": "running",
  "total_jobs": 3,
  "completed_jobs": 1,
  "failed_jobs": 0,
  "running_jobs": 2,
  "queued_jobs": 0,
  "jobs": [
    {
      "job_id": "batch_abc123xyz_job_000",
      "url": "https://example.com/video1",
      "status": "completed",
      "title": "Example Video 1",
      "progress": {
        "percent": 100.0,
        "downloaded_bytes": 52428800,
        "total_bytes": 52428800,
        "status": "completed"
      },
      "file_info": {
        "filename": "example-video-1.mp4",
        "file_url": "https://api.example.com/files/batch_abc123xyz/example-video-1.mp4",
        "size_bytes": 52428800
      },
      "created_at": "2025-11-06T10:00:00Z",
      "completed_at": "2025-11-06T10:05:00Z"
    },
    {
      "job_id": "batch_abc123xyz_job_001",
      "url": "https://example.com/video2",
      "status": "running",
      "progress": {
        "percent": 45.2,
        "downloaded_bytes": 23756800,
        "total_bytes": 52428800,
        "speed": 1048576.0,
        "eta": 27,
        "status": "downloading"
      },
      "created_at": "2025-11-06T10:00:00Z"
    }
  ],
  "created_at": "2025-11-06T10:00:00Z",
  "started_at": "2025-11-06T10:00:05Z",
  "duration_sec": 305.5
}
```

**Error Codes:**
- `404 Not Found`: Batch ID doesn't exist

#### DELETE /api/v1/batch/{batch_id}

Cancels all pending and running jobs in a batch.

**Response:** `200 OK`
```json
{
  "request_id": "batch_abc123xyz",
  "status": "cancelled",
  "cancelled_jobs": 2,
  "message": "Batch cancelled successfully, 2 jobs cancelled",
  "timestamp": "2025-11-06T10:10:00Z"
}
```

**Error Codes:**
- `404 Not Found`: Batch ID doesn't exist

### 4. Integration with Existing Components

#### QueueManager Integration

The batch service reuses the existing `QueueManager` for job execution:

```python
self.queue_manager.submit_job(
    job_id=job_id,
    coroutine=process_download_job(
        request_id=job_id,
        payload=download_request,
        job_state_manager=self.job_state_manager,
        settings=self.settings
    )
)
```

Key benefits:
- No duplication of download logic
- Consistent job execution across single and batch downloads
- Shared thread pool management
- Unified error handling

#### JobStateManager Integration

Individual jobs in a batch are tracked exactly like single downloads:

```python
job = self.job_state_manager.create_job(
    request_id=job_id,
    url=url,
    payload=download_request.model_dump(),
    status=JobStatus.QUEUED
)
```

Benefits:
- Each job in batch has independent status tracking
- Same progress reporting mechanism
- Consistent logging across download types
- Jobs queryable via existing `/api/v1/download/{job_id}` endpoint

### 5. Concurrency Control

#### Semaphore-Based Limiting

Concurrent downloads are controlled using `asyncio.Semaphore`:

```python
semaphore = asyncio.Semaphore(concurrent_limit)

async def process_job_with_limit(job_id: str):
    async with semaphore:
        # Submit and wait for job completion
        self.queue_manager.submit_job(...)
```

**How it works:**
1. Batch creates a semaphore with `concurrent_limit` permits
2. Each job acquires a permit before starting
3. Job releases permit when completed/failed/cancelled
4. Excess jobs wait until permits become available

**Example with concurrent_limit=3:**
- URLs 1-3: Start immediately
- URLs 4-10: Wait in queue
- When URL 1 completes, URL 4 starts
- Process continues until all jobs complete

#### Stop-on-Error Logic

When `stop_on_error=true`:

```python
should_stop = asyncio.Event()

if stop_on_error and job.status == JobStatus.FAILED:
    should_stop.set()
    batch_state.set_failed(f"Job {job_id} failed")

# In each job processor
if should_stop.is_set():
    job.set_cancelled()
    return
```

**Behavior:**
1. First job failure sets `should_stop` event
2. All waiting jobs check event before starting
3. Waiting jobs are immediately cancelled
4. Running jobs continue until completion
5. Batch marked as FAILED with error message

## Configuration

### Environment Variables

No new environment variables required. Batch downloads respect existing configuration:

- `MAX_CONCURRENT_DOWNLOADS`: Overall system limit
- `WORKERS`: Thread pool size
- `STORAGE_DIR`: Output directory
- `PUBLIC_BASE_URL`: Base URL for file access

### Limits and Defaults

| Parameter | Default | Min | Max | Description |
|-----------|---------|-----|-----|-------------|
| URLs per batch | - | 1 | 100 | Maximum batch size |
| concurrent_limit | 3 | 1 | 10 | Concurrent downloads per batch |
| timeout_sec | 1800 | 60 | 7200 | Per-job timeout |

## Error Handling

### Validation Errors

**Empty URL list:**
```json
{
  "error": "ValidationError",
  "message": "At least one URL is required",
  "status_code": 422
}
```

**Batch too large:**
```json
{
  "error": "RequestEntityTooLarge",
  "message": "Batch size exceeds maximum of 100 URLs",
  "status_code": 413
}
```

**Duplicate URLs:**
```json
{
  "error": "ValidationError",
  "message": "Duplicate URLs found in batch",
  "status_code": 422
}
```

### Runtime Errors

**Queue full:**
```json
{
  "error": "ServiceUnavailable",
  "message": "Queue at capacity: 50 active jobs",
  "status_code": 503
}
```

**Batch not found:**
```json
{
  "error": "NotFound",
  "message": "Batch not found: batch_invalid123",
  "status_code": 404
}
```

### Partial Failures

With `stop_on_error=false` (default), batch continues despite individual job failures:

```json
{
  "batch_id": "batch_abc123",
  "status": "completed",
  "total_jobs": 10,
  "completed_jobs": 7,
  "failed_jobs": 3,
  "running_jobs": 0,
  "queued_jobs": 0
}
```

Failed jobs include error messages in their `JobInfo`:

```json
{
  "job_id": "batch_abc123_job_005",
  "url": "https://invalid-domain.example/video",
  "status": "failed",
  "error": "Download error: Video unavailable",
  "created_at": "2025-11-06T10:00:00Z",
  "completed_at": "2025-11-06T10:00:30Z"
}
```

## Testing

### Manual Testing

**Create batch download:**
```bash
curl -X POST "http://localhost:8080/api/v1/batch/download" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "https://www.youtube.com/watch?v=9bZkp7q19f0"
    ],
    "quality": "1080p",
    "concurrent_limit": 2,
    "stop_on_error": false
  }'
```

**Check batch status:**
```bash
curl -X GET "http://localhost:8080/api/v1/batch/batch_abc123" \
  -H "X-API-Key: your-api-key"
```

**Cancel batch:**
```bash
curl -X DELETE "http://localhost:8080/api/v1/batch/batch_abc123" \
  -H "X-API-Key: your-api-key"
```

### Integration Testing

Key test scenarios:

1. **Concurrent limiting:**
   - Submit batch with 10 URLs, limit=3
   - Verify only 3 jobs running simultaneously
   - Verify jobs queue when limit reached

2. **Stop-on-error:**
   - Submit batch with stop_on_error=true
   - Include one invalid URL
   - Verify batch stops after first failure
   - Verify remaining jobs cancelled

3. **Continue-on-error:**
   - Submit batch with stop_on_error=false
   - Include invalid URLs
   - Verify batch continues despite failures
   - Verify final status shows partial completion

4. **Cancellation:**
   - Start batch with long-running downloads
   - Cancel batch mid-execution
   - Verify running jobs continue but queued jobs cancelled

## Performance Considerations

### Memory Usage

**Per batch:**
- `BatchState` object: ~1 KB
- Job states: ~2 KB per URL
- 100-URL batch: ~200 KB

**Cleanup strategy:**
- Completed batches retained for 24 hours by default
- Manual cleanup via `cleanup_old_batches()`
- Consider implementing automatic cleanup task

### Thread Pool

Batch downloads share the global thread pool with single downloads:

- Pool size controlled by `WORKERS` setting
- Default: 4 workers
- Recommendation: 2-8 workers depending on I/O vs CPU workload

### Database Considerations

Current implementation uses in-memory state:
- Fast access
- No persistence across restarts
- Not suitable for horizontal scaling

**Future enhancement:** Migrate to database backend for:
- Persistent batch state
- Multi-instance support
- Long-term history retention

## Monitoring and Observability

### Logging

Key log messages:

```
INFO: Creating batch batch_abc123 with 10 URLs, concurrent_limit=3
INFO: Batch batch_abc123 created with 10 jobs
INFO: Starting batch processing for batch_abc123
INFO: Job batch_abc123_job_000 submitted to queue
WARNING: Job batch_abc123_job_005 failed, triggering batch stop
INFO: Batch batch_abc123 completed successfully
INFO: Cancelled 5 jobs in batch batch_abc123
```

### Metrics

Recommended metrics to track:

- `batch_downloads_total`: Total batches created
- `batch_downloads_completed`: Successfully completed batches
- `batch_downloads_failed`: Failed batches
- `batch_job_count`: Distribution of jobs per batch
- `batch_duration_seconds`: Batch processing time
- `batch_concurrent_jobs`: Current concurrent jobs per batch

### Health Checks

Batch service health indicators:

```python
def is_healthy() -> bool:
    return (
        queue_manager.is_healthy() and
        len(batch_service._batches) < MAX_ACTIVE_BATCHES
    )
```

## Security Considerations

### Input Validation

- URL format validation (prevents SSRF)
- Batch size limits (prevents resource exhaustion)
- Duplicate detection (prevents redundant work)
- Path template sanitization (prevents directory traversal)

### Authentication

Batch endpoints require the same authentication as single downloads:
- API key via `X-API-Key` header
- Configurable via `REQUIRE_API_KEY` environment variable

### Rate Limiting

Consider implementing:
- Max batches per user per hour
- Max total URLs per user per day
- Automatic backoff on repeated failures

## Future Enhancements

### Priority Queue

Support for batch priorities:

```python
class BatchDownloadRequest(BaseModel):
    priority: int = Field(0, ge=0, le=10)
```

Higher priority batches get processed first.

### Progress Webhooks

Enhanced webhook support for batch completion:

```python
webhook_url: Optional[HttpUrl]
webhook_events: List[WebhookEvent] = [
    "batch.started",
    "batch.progress",
    "batch.completed"
]
```

### Scheduled Batches

Support for delayed batch execution:

```python
scheduled_at: Optional[datetime]
```

Batch queued but not processed until scheduled time.

### Batch Templates

Save batch configurations as templates:

```python
@router.post("/batch/templates")
async def save_batch_template(...)
```

Reuse common batch configurations.

## Troubleshooting

### Batch stuck in "running" status

**Symptom:** Batch remains in RUNNING status indefinitely

**Causes:**
- Jobs deadlocked in queue
- Background task crashed

**Solutions:**
1. Check queue manager health
2. Review job logs for stuck jobs
3. Manually cancel batch
4. Restart application if necessary

### High memory usage

**Symptom:** Memory consumption grows with batch count

**Causes:**
- Old batches not cleaned up
- Large metadata objects

**Solutions:**
1. Implement periodic cleanup
2. Reduce batch retention time
3. Consider database migration

### Slow batch processing

**Symptom:** Batches take longer than expected

**Causes:**
- concurrent_limit too low
- Network bandwidth limitations
- Source throttling

**Solutions:**
1. Increase concurrent_limit (up to 10)
2. Increase thread pool size
3. Implement exponential backoff for throttled sources

## File Reference

### New Files

- `/app/services/batch_service.py` (541 lines)
  - `BatchState` class
  - `BatchService` class
  - Singleton factory functions

- `/app/api/v1/batch.py` (238 lines)
  - `POST /batch/download` endpoint
  - `GET /batch/{batch_id}` endpoint
  - `DELETE /batch/{batch_id}` endpoint

### Modified Files

- `/app/api/v1/router.py`
  - Added `batch` router import
  - Included `batch.router` in main router

### Existing Files (Used)

- `/app/models/requests.py`
  - `BatchDownloadRequest` model (already existed)

- `/app/models/responses.py`
  - `BatchDownloadResponse` model (already existed)
  - `JobInfo` model (already existed)
  - `BatchStatusResponse` model (already existed)

- `/app/services/queue_manager.py`
  - `QueueManager` class (reused for job execution)

- `/app/core/state.py`
  - `JobStateManager` class (reused for job tracking)

## Conclusion

The Batch Downloads feature has been successfully implemented with:

- Clean separation of concerns (API → Service → Queue → State)
- Thread-safe concurrent processing with semaphore-based limiting
- Flexible error handling (stop-on-error vs continue-on-error)
- Comprehensive status tracking and progress reporting
- Full integration with existing download infrastructure
- Robust validation and error handling
- RESTful API design following existing patterns

The implementation follows the existing architecture patterns and integrates seamlessly with the modular v3.0.0 codebase.

**Next steps:**
1. Add unit tests for `BatchService`
2. Add integration tests for batch endpoints
3. Implement webhook notifications for batch completion
4. Consider database migration for persistence
5. Add batch analytics dashboard
