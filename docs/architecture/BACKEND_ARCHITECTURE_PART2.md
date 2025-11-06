# Ultimate Media Downloader - Backend Architecture Part 2

## Response Models

**File: `app/models/responses.py`**

```python
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadResponse(BaseModel):
    """Response model for download job."""

    request_id: str = Field(..., description="Unique request identifier")
    status: JobStatus = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    # File information
    file_url: Optional[str] = Field(None, description="URL to download file")
    file_path: Optional[str] = Field(None, description="Relative file path")
    file_size: Optional[int] = Field(None, description="File size in bytes")

    # Metadata
    title: Optional[str] = Field(None, description="Video title")
    duration: Optional[int] = Field(None, description="Duration in seconds")
    format: Optional[str] = Field(None, description="Download format")

    # Progress
    progress_percent: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage")
    downloaded_bytes: Optional[int] = Field(None, description="Downloaded bytes")
    total_bytes: Optional[int] = Field(None, description="Total bytes")
    speed: Optional[float] = Field(None, description="Download speed (bytes/sec)")
    eta: Optional[int] = Field(None, description="Estimated time remaining (seconds)")

    # Lifecycle
    deletion_time: Optional[datetime] = Field(None, description="Scheduled deletion time")
    logs_url: Optional[str] = Field(None, description="URL to job logs")

    # Error information
    error: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Error code for programmatic handling")


class FormatInfo(BaseModel):
    """Format information model."""

    format_id: str
    ext: str
    resolution: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    tbr: Optional[float] = None
    format_note: Optional[str] = None
    quality: Optional[str] = None


class FormatsResponse(BaseModel):
    """Response model for available formats."""

    url: str
    title: str
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    uploader: Optional[str] = None

    formats: Dict[str, List[FormatInfo]] = Field(
        ...,
        description="Categorized formats (combined, video_only, audio_only)"
    )

    recommended_format: str = Field(..., description="Recommended format string")
    best_video_format: Optional[str] = None
    best_audio_format: Optional[str] = None


class PlaylistVideoInfo(BaseModel):
    """Playlist video information."""

    id: str
    title: str
    url: str
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    uploader: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    playlist_index: Optional[int] = None


class PlaylistPreviewResponse(BaseModel):
    """Response model for playlist preview."""

    playlist_id: str
    playlist_title: str
    playlist_uploader: Optional[str] = None
    total_videos: int

    # Pagination
    page: int = 1
    page_size: int = 50
    total_pages: int

    videos: List[PlaylistVideoInfo] = Field(..., description="List of videos in playlist")

    # Metadata
    playlist_url: str
    thumbnail: Optional[str] = None
    description: Optional[str] = None


class ChannelInfo(BaseModel):
    """Channel information model."""

    channel_id: str
    channel_name: str
    channel_url: str
    subscriber_count: Optional[int] = None
    video_count: Optional[int] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None


class ChannelInfoResponse(BaseModel):
    """Response model for channel information."""

    channel: ChannelInfo
    videos: List[PlaylistVideoInfo]

    # Pagination and filtering
    total_videos: int
    page: int = 1
    page_size: int = 50
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class BatchJobInfo(BaseModel):
    """Individual job in batch."""

    url: str
    request_id: str
    status: JobStatus
    title: Optional[str] = None
    error: Optional[str] = None
    file_url: Optional[str] = None


class BatchDownloadResponse(BaseModel):
    """Response model for batch downloads."""

    batch_id: str
    status: JobStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    total_urls: int
    completed: int = 0
    failed: int = 0
    running: int = 0
    queued: int = 0

    jobs: List[BatchJobInfo] = Field(..., description="Individual job statuses")

    # Overall progress
    progress_percent: float = Field(0.0, ge=0, le=100)


class MetadataResponse(BaseModel):
    """Response model for metadata extraction."""

    id: str
    url: str
    title: str
    description: Optional[str] = None

    # Uploader info
    uploader: Optional[str] = None
    uploader_id: Optional[str] = None
    uploader_url: Optional[str] = None
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None

    # Video stats
    upload_date: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None

    # Content info
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    thumbnail: Optional[str] = None

    # Formats
    formats: Optional[List[FormatInfo]] = None

    # Subtitles
    subtitles: Optional[Dict[str, List[Dict[str, str]]]] = None
    automatic_captions: Optional[Dict[str, List[Dict[str, str]]]] = None


class LogEntry(BaseModel):
    """Log entry model."""

    timestamp: datetime
    level: str
    message: str


class LogsResponse(BaseModel):
    """Response model for job logs."""

    request_id: str
    logs: List[LogEntry]
    total_count: int


class CookiesResponse(BaseModel):
    """Response model for cookies upload."""

    cookie_id: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class HealthCheck(BaseModel):
    """Individual health check."""

    name: str
    status: str  # "healthy", "unhealthy", "unknown"
    message: Optional[str] = None
    latency_ms: Optional[float] = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    version: str
    uptime_seconds: float

    checks: List[HealthCheck]


class StatsResponse(BaseModel):
    """Response model for service statistics."""

    # Job statistics
    total_jobs: int
    jobs_by_status: Dict[JobStatus, int]

    # Performance
    average_download_time: Optional[float] = None
    success_rate: float

    # Storage
    storage_used_bytes: int
    storage_available_bytes: int
    active_files: int

    # Queue
    queue_size: int
    active_downloads: int

    # Uptime
    uptime_seconds: float
    started_at: datetime


class CancelResponse(BaseModel):
    """Response model for cancellation."""

    request_id: str
    status: str
    message: str
```

---

## Background Job System

**File: `app/services/queue_manager.py`**

```python
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from uuid import UUID
import uuid

from app.core.exceptions import JobNotFoundError
from app.models.responses import JobStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Job:
    """Represents a download job."""

    def __init__(
        self,
        job_id: str,
        job_type: str,
        payload: Dict[str, Any],
        callback: Optional[Callable] = None
    ):
        self.job_id = job_id
        self.job_type = job_type
        self.payload = payload
        self.callback = callback
        self.status = JobStatus.QUEUED
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress = 0.0
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.task: Optional[asyncio.Task] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            'job_id': self.job_id,
            'job_type': self.job_type,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
            'result': self.result,
            'error': self.error,
        }


class QueueManager:
    """Manages background job processing with concurrency control."""

    def __init__(
        self,
        max_workers: int = 4,
        max_concurrent_downloads: int = 10
    ):
        self.max_workers = max_workers
        self.max_concurrent_downloads = max_concurrent_downloads

        self.jobs: Dict[str, Job] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.workers: list[asyncio.Task] = []
        self.running = False

        # Statistics
        self.stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
        }

    async def start(self):
        """Start the queue manager and workers."""
        if self.running:
            logger.warning("Queue manager already running")
            return

        self.running = True

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)

        logger.info(f"Queue manager started with {self.max_workers} workers")

    async def shutdown(self):
        """Gracefully shutdown the queue manager."""
        logger.info("Shutting down queue manager...")
        self.running = False

        # Wait for queue to empty (with timeout)
        try:
            await asyncio.wait_for(self.queue.join(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("Queue did not empty within timeout")

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)

        logger.info("Queue manager shutdown complete")

    async def _worker(self, worker_id: int):
        """Worker task that processes jobs from the queue."""
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Get job from queue
                job = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                try:
                    logger.info(f"Worker {worker_id} processing job {job.job_id}")
                    await self._process_job(job)
                finally:
                    self.queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)

        logger.info(f"Worker {worker_id} stopped")

    async def _process_job(self, job: Job):
        """Process a single job."""
        try:
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)

            # Execute job callback
            if job.callback:
                result = await job.callback(job)
                job.result = result
                job.status = JobStatus.COMPLETED
                self.stats['completed_jobs'] += 1
            else:
                raise ValueError("Job has no callback")

            job.completed_at = datetime.now(timezone.utc)
            logger.info(f"Job {job.job_id} completed successfully")

        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED
            job.error = "Job was cancelled"
            logger.info(f"Job {job.job_id} was cancelled")
            raise

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            self.stats['failed_jobs'] += 1
            logger.error(f"Job {job.job_id} failed: {e}", exc_info=True)

        finally:
            job.completed_at = datetime.now(timezone.utc)

    async def submit_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        callback: Callable,
        job_id: Optional[str] = None
    ) -> str:
        """
        Submit a new job to the queue.

        Args:
            job_type: Type of job (download, playlist, batch, etc.)
            payload: Job payload data
            callback: Async function to execute
            job_id: Optional custom job ID

        Returns:
            Job ID string
        """
        if not self.running:
            raise RuntimeError("Queue manager is not running")

        # Generate or validate job ID
        if job_id is None:
            job_id = str(uuid.uuid4())
        else:
            try:
                UUID(job_id)  # Validate UUID format
            except ValueError:
                raise ValueError(f"Invalid job_id format: {job_id}")

        # Create job
        job = Job(
            job_id=job_id,
            job_type=job_type,
            payload=payload,
            callback=callback
        )

        # Store job
        self.jobs[job_id] = job
        self.stats['total_jobs'] += 1

        # Add to queue
        await self.queue.put(job)

        logger.info(f"Job {job_id} submitted (type: {job_type}, queue size: {self.queue.qsize()})")

        return job_id

    async def get_job(self, job_id: str) -> Job:
        """Get job by ID."""
        job = self.jobs.get(job_id)
        if not job:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        job = await self.get_job(job_id)

        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False  # Already finished

        if job.task and not job.task.done():
            job.task.cancel()

        job.status = JobStatus.CANCELLED
        job.error = "Cancelled by user"
        job.completed_at = datetime.now(timezone.utc)

        logger.info(f"Job {job_id} cancelled")
        return True

    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        status_counts = defaultdict(int)
        for job in self.jobs.values():
            status_counts[job.status.value] += 1

        return {
            'total_jobs': self.stats['total_jobs'],
            'completed_jobs': self.stats['completed_jobs'],
            'failed_jobs': self.stats['failed_jobs'],
            'queue_size': self.queue.qsize(),
            'jobs_by_status': dict(status_counts),
            'active_workers': len([w for w in self.workers if not w.done()]),
        }

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove completed jobs older than max_age_hours."""
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - (max_age_hours * 3600)

        to_remove = []
        for job_id, job in self.jobs.items():
            if job.completed_at and job.completed_at.timestamp() < cutoff:
                to_remove.append(job_id)

        for job_id in to_remove:
            del self.jobs[job_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old jobs")

        return len(to_remove)
```

---

## Download Manager Service

**File: `app/services/download_manager.py`**

```python
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone, timedelta

from app.core.exceptions import DownloadError
from app.models.requests import DownloadRequest, PlaylistDownloadRequest, ChannelDownloadRequest
from app.models.responses import JobStatus
from app.services.ytdlp_wrapper import YtdlpWrapper
from app.services.file_manager import FileManager
from app.services.webhook_service import WebhookService
from app.services.auth_manager import AuthManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DownloadManager:
    """Orchestrates download operations."""

    def __init__(
        self,
        storage_dir: Path,
        file_manager: FileManager,
        auth_manager: AuthManager,
        webhook_service: WebhookService
    ):
        self.storage_dir = storage_dir
        self.file_manager = file_manager
        self.auth_manager = auth_manager
        self.webhook_service = webhook_service
        self.ytdlp = YtdlpWrapper(storage_dir)

        # Progress tracking
        self.progress_callbacks: Dict[str, Any] = {}

    async def download_single(
        self,
        request_id: str,
        request: DownloadRequest,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Download a single video.

        Args:
            request_id: Unique request identifier
            request: Download request
            progress_callback: Optional progress callback

        Returns:
            Download result dictionary
        """
        logger.info(f"Starting download {request_id} for URL: {request.url}")

        try:
            # Get cookies if specified
            cookies_path = None
            if request.cookies_id:
                cookies_path = await self.auth_manager.get_cookies_path(request.cookies_id)

            # Register progress callback
            if progress_callback:
                self.progress_callbacks[request_id] = progress_callback

            # Execute download
            result = await self.ytdlp.download(
                request_id=request_id,
                request=request,
                cookies_path=cookies_path,
                progress_callback=lambda p: self._handle_progress(request_id, p)
            )

            # Get file path
            file_path = Path(result['file_path'])
            relative_path = file_path.relative_to(self.storage_dir)

            # Schedule cleanup
            deletion_time = await self.file_manager.schedule_deletion(
                file_path=file_path,
                delay_hours=1
            )

            # Build response
            response = {
                'request_id': request_id,
                'status': JobStatus.COMPLETED,
                'file_path': str(relative_path),
                'file_size': file_path.stat().st_size if file_path.exists() else None,
                'title': result.get('title'),
                'duration': result.get('duration'),
                'format': result.get('format'),
                'deletion_time': deletion_time,
            }

            # Send webhook if configured
            if request.webhook_url:
                await self.webhook_service.send_webhook(
                    url=str(request.webhook_url),
                    event='download.completed',
                    data=response
                )

            logger.info(f"Download {request_id} completed successfully")
            return response

        except Exception as e:
            logger.error(f"Download {request_id} failed: {e}", exc_info=True)

            # Send failure webhook
            if request.webhook_url:
                await self.webhook_service.send_webhook(
                    url=str(request.webhook_url),
                    event='download.failed',
                    data={
                        'request_id': request_id,
                        'error': str(e),
                    }
                )

            raise DownloadError(f"Download failed: {str(e)}")

        finally:
            # Clean up progress callback
            self.progress_callbacks.pop(request_id, None)

    def _handle_progress(self, request_id: str, progress: Dict[str, Any]):
        """Handle progress updates from yt-dlp."""
        callback = self.progress_callbacks.get(request_id)
        if callback:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error for {request_id}: {e}")

    async def download_playlist(
        self,
        request_id: str,
        request: PlaylistDownloadRequest,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Download a playlist."""
        logger.info(f"Starting playlist download {request_id} for URL: {request.url}")

        try:
            # Get cookies if specified
            cookies_path = None
            if request.cookies_id:
                cookies_path = await self.auth_manager.get_cookies_path(request.cookies_id)

            # Extract playlist info first
            playlist_info = await self.ytdlp.extract_info(
                url=request.url,
                download=False,
                cookies_path=cookies_path
            )

            if playlist_info.get('_type') != 'playlist':
                raise ValueError("URL is not a playlist")

            # Execute playlist download
            result = await self.ytdlp.download_playlist(
                request_id=request_id,
                request=request,
                cookies_path=cookies_path,
                progress_callback=lambda p: self._handle_progress(request_id, p)
            )

            # Send webhook
            if request.webhook_url:
                await self.webhook_service.send_webhook(
                    url=str(request.webhook_url),
                    event='playlist.completed',
                    data={
                        'request_id': request_id,
                        'playlist_title': playlist_info.get('title'),
                        'video_count': len(playlist_info.get('entries', [])),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Playlist download {request_id} failed: {e}", exc_info=True)
            raise DownloadError(f"Playlist download failed: {str(e)}")

    async def get_formats(self, url: str, cookies_id: Optional[str] = None) -> Dict[str, Any]:
        """Get available formats for a URL."""
        cookies_path = None
        if cookies_id:
            cookies_path = await self.auth_manager.get_cookies_path(cookies_id)

        return await self.ytdlp.get_formats(url, cookies_path)

    async def extract_metadata(self, url: str, cookies_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract metadata without downloading."""
        cookies_path = None
        if cookies_id:
            cookies_path = await self.auth_manager.get_cookies_path(cookies_id)

        return await self.ytdlp.extract_info(url, download=False, cookies_path=cookies_path)
```

---

## File Management & Auto-Cleanup

**File: `app/services/file_manager.py`**

```python
import asyncio
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
import aiofiles
import aiofiles.os

from app.utils.logger import get_logger

logger = get_logger(__name__)


class FileManager:
    """Manages file operations and auto-cleanup."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Track scheduled deletions
        self.scheduled_deletions: Dict[str, asyncio.Task] = {}

    async def schedule_deletion(
        self,
        file_path: Path,
        delay_hours: float = 1.0
    ) -> datetime:
        """
        Schedule file deletion after specified delay.

        Args:
            file_path: Path to file
            delay_hours: Hours until deletion

        Returns:
            Scheduled deletion datetime
        """
        deletion_time = datetime.now(timezone.utc) + timedelta(hours=delay_hours)
        delay_seconds = delay_hours * 3600

        # Create deletion task
        task = asyncio.create_task(self._delete_after_delay(file_path, delay_seconds))
        task_id = str(file_path)
        self.scheduled_deletions[task_id] = task

        logger.info(f"Scheduled deletion of {file_path} at {deletion_time}")
        return deletion_time

    async def _delete_after_delay(self, file_path: Path, delay_seconds: float):
        """Delete file after delay."""
        try:
            await asyncio.sleep(delay_seconds)

            if file_path.exists():
                await aiofiles.os.remove(file_path)
                logger.info(f"Auto-deleted file: {file_path}")

                # Clean up empty parent directories
                await self._cleanup_empty_dirs(file_path.parent)
            else:
                logger.debug(f"File already deleted: {file_path}")

        except asyncio.CancelledError:
            logger.info(f"Deletion cancelled for: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
        finally:
            # Remove from tracking
            task_id = str(file_path)
            self.scheduled_deletions.pop(task_id, None)

    async def cancel_deletion(self, file_path: Path) -> bool:
        """Cancel scheduled deletion."""
        task_id = str(file_path)
        task = self.scheduled_deletions.get(task_id)

        if task and not task.done():
            task.cancel()
            logger.info(f"Cancelled deletion for: {file_path}")
            return True

        return False

    async def _cleanup_empty_dirs(self, directory: Path):
        """Recursively remove empty directories."""
        try:
            if directory == self.storage_dir:
                return  # Don't delete root storage dir

            if directory.exists() and directory.is_dir():
                if not any(directory.iterdir()):
                    await aiofiles.os.rmdir(directory)
                    logger.debug(f"Removed empty directory: {directory}")
                    # Recurse to parent
                    await self._cleanup_empty_dirs(directory.parent)
        except Exception as e:
            logger.error(f"Error cleaning up directory {directory}: {e}")

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_size = 0
        file_count = 0

        for file_path in self.storage_dir.rglob('*'):
            if file_path.is_file():
                file_count += 1
                total_size += file_path.stat().st_size

        # Get disk usage
        usage = shutil.disk_usage(self.storage_dir)

        return {
            'storage_dir': str(self.storage_dir),
            'files_count': file_count,
            'total_size_bytes': total_size,
            'disk_total_bytes': usage.total,
            'disk_used_bytes': usage.used,
            'disk_free_bytes': usage.free,
        }

    async def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up files older than max_age_hours."""
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=max_age_hours)

        deleted_count = 0

        for file_path in self.storage_dir.rglob('*'):
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff_time:
                    try:
                        await aiofiles.os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to clean up {file_path}: {e}")

        logger.info(f"Cleaned up {deleted_count} old files")
        return deleted_count
```

This provides comprehensive models, queue management, download orchestration, and file management. Would you like me to continue with:

1. **API Route Handlers** (all endpoints implementation)
2. **Middleware Components** (auth, rate limiting, security)
3. **Webhook Service**
4. **Configuration Management**
5. **Complete Testing Suite**
6. **Deployment Configuration** (Docker, Railway)

Let me know which sections to detail next!
