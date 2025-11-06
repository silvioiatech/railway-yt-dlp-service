"""
Download endpoints for the Ultimate Media Downloader API.

Provides endpoints for creating, monitoring, and managing single video downloads.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.auth import RequireAuth
from app.config import Settings, get_settings
from app.core.exceptions import (
    DownloadError,
    DownloadTimeoutError,
    JobNotFoundError,
    QueueFullError,
)
from app.core.state import JobState, JobStateManager, get_job_state_manager
from app.models.enums import JobStatus
from app.models.requests import DownloadRequest
from app.models.responses import (
    CancelResponse,
    DownloadResponse,
    FileInfo,
    LogsResponse,
    ProgressInfo,
    VideoMetadata,
)
from app.services.queue_manager import QueueManager, get_queue_manager
from app.services.ytdlp_wrapper import YtdlpWrapper
from app.services.webhook_service import (
    WebhookDeliveryService,
    WebhookEvent,
    get_webhook_service,
)

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/download", tags=["downloads"])


# =========================
# Dependencies
# =========================

def get_ytdlp_wrapper(
    settings: Annotated[Settings, Depends(get_settings)]
) -> YtdlpWrapper:
    """
    Dependency to get YtdlpWrapper instance.

    Args:
        settings: Application settings

    Returns:
        YtdlpWrapper: Configured wrapper instance
    """
    return YtdlpWrapper(storage_dir=settings.STORAGE_DIR)


# =========================
# Helper Functions
# =========================

async def process_download_job(
    request_id: str,
    payload: DownloadRequest,
    job_state_manager: JobStateManager,
    settings: Settings
):
    """
    Process a download job asynchronously.

    This function is executed in a background thread via the queue manager.

    Args:
        request_id: Unique job identifier
        payload: Download request payload
        job_state_manager: Job state manager for tracking
        settings: Application settings
    """
    job = job_state_manager.get_job(request_id)
    if not job:
        logger.error(f"Job {request_id} not found in state manager")
        return

    # Get webhook service
    webhook_service = get_webhook_service()
    webhook_url = str(payload.webhook_url) if payload.webhook_url else None

    try:
        # Mark job as running
        job.set_running()
        job.add_log("Starting download", "INFO")

        # Send download.started webhook
        if webhook_url:
            await webhook_service.send_webhook(
                url=webhook_url,
                event_type=WebhookEvent.DOWNLOAD_STARTED,
                payload={
                    "request_id": request_id,
                    "url": payload.url,
                    "status": "started",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                }
            )

        # Create ytdlp wrapper
        ytdlp = YtdlpWrapper(storage_dir=settings.STORAGE_DIR)

        # Progress callback with webhook support
        def progress_callback(progress_data: Dict[str, Any]):
            """Update job progress from yt-dlp."""
            if progress_data.get('status') == 'downloading':
                job.update_progress(
                    percent=progress_data.get('percent', 0.0),
                    bytes_downloaded=progress_data.get('downloaded_bytes', 0),
                    bytes_total=progress_data.get('total_bytes'),
                    speed=progress_data.get('speed', 0.0),
                    eta=progress_data.get('eta')
                )

                # Send progress webhook (throttled internally)
                if webhook_url:
                    # Fire and forget webhook (don't await to avoid blocking download)
                    asyncio.create_task(
                        webhook_service.send_webhook(
                            url=webhook_url,
                            event_type=WebhookEvent.DOWNLOAD_PROGRESS,
                            payload={
                                "request_id": request_id,
                                "url": payload.url,
                                "status": "downloading",
                                "progress": {
                                    "percent": job.progress_percent,
                                    "downloaded_bytes": job.bytes_downloaded,
                                    "total_bytes": job.bytes_total,
                                    "speed": job.download_speed,
                                    "eta": job.eta_seconds
                                },
                                "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                            }
                        )
                    )

            elif progress_data.get('status') == 'post_processing':
                job.add_log("Post-processing download", "INFO")
            elif progress_data.get('status') == 'error':
                job.add_log(f"Download error: {progress_data.get('error')}", "ERROR")

        # Perform download
        job.add_log(f"Downloading from {payload.url}", "INFO")
        result = await ytdlp.download(
            request_id=request_id,
            request=payload,
            progress_callback=progress_callback
        )

        # Extract file information
        file_path = Path(result.get('file_path', ''))
        if file_path.exists():
            file_size = file_path.stat().st_size
            relative_path = file_path.relative_to(settings.STORAGE_DIR)

            # Generate public URL if configured
            file_url = None
            if settings.PUBLIC_BASE_URL:
                file_url = f"{settings.PUBLIC_BASE_URL}/files/{relative_path}"

            # Update job with results
            job.set_completed(file_path=file_path, file_url=file_url)
            job.file_size = file_size
            job.metadata = result.get('metadata', {})
            job.add_log(f"Download completed: {file_path.name}", "INFO")

            logger.info(f"Download completed successfully: {request_id}")

            # Send download.completed webhook
            if webhook_url:
                await webhook_service.send_webhook(
                    url=webhook_url,
                    event_type=WebhookEvent.DOWNLOAD_COMPLETED,
                    payload={
                        "request_id": request_id,
                        "url": payload.url,
                        "title": job.metadata.get('title'),
                        "file_url": file_url,
                        "file_path": str(relative_path),
                        "file_size": file_size,
                        "status": "completed",
                        "duration": job.metadata.get('duration'),
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                    }
                )
                # Clean up throttle cache
                await webhook_service.cleanup_throttle_cache(request_id)
        else:
            raise DownloadError(f"Downloaded file not found: {file_path}")

    except DownloadTimeoutError as e:
        logger.error(f"Download timeout for {request_id}: {e}")
        job.set_failed(f"Download timeout: {e.message}")
        job.add_log(f"Download timeout: {e.message}", "ERROR")

        # Send download.failed webhook
        if webhook_url:
            await webhook_service.send_webhook(
                url=webhook_url,
                event_type=WebhookEvent.DOWNLOAD_FAILED,
                payload={
                    "request_id": request_id,
                    "url": payload.url,
                    "status": "failed",
                    "error": f"Download timeout: {e.message}",
                    "error_type": "timeout",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                }
            )
            await webhook_service.cleanup_throttle_cache(request_id)

    except DownloadError as e:
        logger.error(f"Download error for {request_id}: {e}")
        job.set_failed(str(e))
        job.add_log(f"Download failed: {e}", "ERROR")

        # Send download.failed webhook
        if webhook_url:
            await webhook_service.send_webhook(
                url=webhook_url,
                event_type=WebhookEvent.DOWNLOAD_FAILED,
                payload={
                    "request_id": request_id,
                    "url": payload.url,
                    "status": "failed",
                    "error": str(e),
                    "error_type": "download_error",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                }
            )
            await webhook_service.cleanup_throttle_cache(request_id)

    except Exception as e:
        logger.error(f"Unexpected error for {request_id}: {e}", exc_info=True)
        job.set_failed(f"Unexpected error: {str(e)}")
        job.add_log(f"Unexpected error: {str(e)}", "ERROR")

        # Send download.failed webhook
        if webhook_url:
            await webhook_service.send_webhook(
                url=webhook_url,
                event_type=WebhookEvent.DOWNLOAD_FAILED,
                payload={
                    "request_id": request_id,
                    "url": payload.url,
                    "status": "failed",
                    "error": str(e),
                    "error_type": "unexpected_error",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                }
            )
            await webhook_service.cleanup_throttle_cache(request_id)


def convert_job_to_response(job: JobState, settings: Settings) -> DownloadResponse:
    """
    Convert JobState to DownloadResponse model.

    Args:
        job: Job state object
        settings: Application settings

    Returns:
        DownloadResponse: API response model
    """
    # Build progress info
    progress = ProgressInfo(
        percent=job.progress_percent,
        downloaded_bytes=job.bytes_downloaded,
        total_bytes=job.bytes_total if job.bytes_total > 0 else None,
        speed=job.download_speed if job.download_speed > 0 else None,
        eta=job.eta_seconds,
        status=job.status.value
    )

    # Build file info if available
    file_info = None
    if job.file_path:
        file_info = FileInfo(
            filename=job.file_path.name,
            file_url=job.file_url,
            file_path=str(job.file_path.relative_to(settings.STORAGE_DIR)),
            size_bytes=job.file_size,
            format=job.file_path.suffix.lstrip('.'),
            mime_type=None  # Could be determined from extension
        )

    # Build metadata if available
    metadata = None
    if job.metadata:
        metadata = VideoMetadata(
            title=job.metadata.get('title'),
            description=job.metadata.get('description'),
            uploader=job.metadata.get('uploader'),
            uploader_id=job.metadata.get('uploader_id'),
            upload_date=job.metadata.get('upload_date'),
            duration=job.metadata.get('duration'),
            view_count=job.metadata.get('view_count'),
            like_count=job.metadata.get('like_count'),
            comment_count=job.metadata.get('comment_count'),
            width=job.metadata.get('width'),
            height=job.metadata.get('height'),
            fps=job.metadata.get('fps'),
            vcodec=job.metadata.get('vcodec'),
            acodec=job.metadata.get('acodec'),
            thumbnail=job.metadata.get('thumbnail'),
            webpage_url=job.metadata.get('webpage_url'),
            extractor=job.metadata.get('extractor')
        )

    # Calculate duration if completed
    duration_sec = None
    if job.started_at and job.completed_at:
        duration_sec = (job.completed_at - job.started_at).total_seconds()

    # Build logs URL
    logs_url = None
    if settings.PUBLIC_BASE_URL:
        logs_url = f"{settings.PUBLIC_BASE_URL}/api/v1/download/{job.request_id}/logs"

    return DownloadResponse(
        request_id=job.request_id,
        status=job.status,
        progress=progress,
        file_info=file_info,
        metadata=metadata,
        error=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_sec=duration_sec,
        logs_url=logs_url,
        webhook_sent=False
    )


# =========================
# Endpoints
# =========================

@router.post(
    "",
    response_model=DownloadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create download job",
    description="Submit a new download job to the queue",
)
async def create_download(
    payload: DownloadRequest,
    auth: RequireAuth,
    queue_manager: Annotated[QueueManager, Depends(get_queue_manager)],
    job_state_manager: Annotated[JobStateManager, Depends(get_job_state_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DownloadResponse:
    """
    Create a new download job.

    Submits a download request to the background queue and returns immediately
    with the job status. The download will be processed asynchronously.

    Args:
        payload: Download request parameters
        auth: Authentication dependency
        queue_manager: Queue manager for job submission
        job_state_manager: Job state manager for tracking
        settings: Application settings

    Returns:
        DownloadResponse: Job status with request_id for tracking

    Raises:
        HTTPException: 503 if queue is full
        HTTPException: 422 if request validation fails

    Example:
        ```bash
        curl -X POST "http://localhost:8080/api/v1/download" \\
             -H "X-API-Key: your-api-key" \\
             -H "Content-Type: application/json" \\
             -d '{
               "url": "https://example.com/video",
               "quality": "1080p",
               "audio_only": false
             }'
        ```
    """
    # Generate unique request ID
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    logger.info(f"Creating download job {request_id} for URL: {payload.url}")

    try:
        # Create job state
        job = job_state_manager.create_job(
            request_id=request_id,
            url=payload.url,
            payload=payload.model_dump(),
            status=JobStatus.QUEUED
        )
        job.add_log("Job created and queued", "INFO")

        # Submit to queue
        queue_manager.submit_job(
            job_id=request_id,
            coroutine=process_download_job(
                request_id=request_id,
                payload=payload,
                job_state_manager=job_state_manager,
                settings=settings
            )
        )

        logger.info(f"Job {request_id} submitted to queue successfully")

        # Return initial response
        return convert_job_to_response(job, settings)

    except QueueFullError as e:
        logger.error(f"Queue full when creating job {request_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating job {request_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create download job: {str(e)}"
        )


@router.get(
    "/{request_id}",
    response_model=DownloadResponse,
    summary="Get download status",
    description="Retrieve the status and details of a download job",
)
async def get_download_status(
    request_id: str,
    auth: RequireAuth,
    job_state_manager: Annotated[JobStateManager, Depends(get_job_state_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DownloadResponse:
    """
    Get the status of a download job.

    Retrieves current status, progress, and results for a specific download job.

    Args:
        request_id: Unique job identifier
        auth: Authentication dependency
        job_state_manager: Job state manager
        settings: Application settings

    Returns:
        DownloadResponse: Complete job status and details

    Raises:
        HTTPException: 404 if job not found

    Example:
        ```bash
        curl -X GET "http://localhost:8080/api/v1/download/req_abc123" \\
             -H "X-API-Key: your-api-key"
        ```
    """
    job = job_state_manager.get_job(request_id)
    if not job:
        logger.warning(f"Job not found: {request_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Download job not found: {request_id}"
        )

    return convert_job_to_response(job, settings)


@router.get(
    "/{request_id}/logs",
    response_model=LogsResponse,
    summary="Get download logs",
    description="Retrieve logs for a specific download job",
)
async def get_download_logs(
    request_id: str,
    auth: RequireAuth,
    job_state_manager: Annotated[JobStateManager, Depends(get_job_state_manager)],
) -> LogsResponse:
    """
    Get logs for a download job.

    Retrieves all log entries generated during job processing.

    Args:
        request_id: Unique job identifier
        auth: Authentication dependency
        job_state_manager: Job state manager

    Returns:
        LogsResponse: Job logs

    Raises:
        HTTPException: 404 if job not found

    Example:
        ```bash
        curl -X GET "http://localhost:8080/api/v1/download/req_abc123/logs" \\
             -H "X-API-Key: your-api-key"
        ```
    """
    job = job_state_manager.get_job(request_id)
    if not job:
        logger.warning(f"Job not found: {request_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Download job not found: {request_id}"
        )

    # Format logs as strings
    log_lines = [
        f"[{log['timestamp']}] {log['level']}: {log['message']}"
        for log in job.logs
    ]

    return LogsResponse(
        request_id=request_id,
        logs=log_lines,
        log_level="INFO",
        total_lines=len(log_lines),
        truncated=False
    )


@router.delete(
    "/{request_id}",
    response_model=CancelResponse,
    summary="Cancel download",
    description="Cancel a running or queued download job",
)
async def cancel_download(
    request_id: str,
    auth: RequireAuth,
    queue_manager: Annotated[QueueManager, Depends(get_queue_manager)],
    job_state_manager: Annotated[JobStateManager, Depends(get_job_state_manager)],
) -> CancelResponse:
    """
    Cancel a download job.

    Attempts to cancel a running or queued download. Already completed jobs
    cannot be cancelled.

    Args:
        request_id: Unique job identifier
        auth: Authentication dependency
        queue_manager: Queue manager
        job_state_manager: Job state manager

    Returns:
        CancelResponse: Cancellation result

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 409 if job already completed

    Example:
        ```bash
        curl -X DELETE "http://localhost:8080/api/v1/download/req_abc123" \\
             -H "X-API-Key: your-api-key"
        ```
    """
    job = job_state_manager.get_job(request_id)
    if not job:
        logger.warning(f"Job not found for cancellation: {request_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Download job not found: {request_id}"
        )

    # Check if job is already completed
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel job in status: {job.status.value}"
        )

    # Attempt to cancel in queue manager
    cancelled = queue_manager.cancel_job(request_id)

    if cancelled:
        job.set_cancelled()
        job.add_log("Job cancelled by user", "INFO")
        message = "Job cancelled successfully"
        logger.info(f"Job {request_id} cancelled successfully")
    else:
        # Job might have completed just before cancellation
        message = "Job could not be cancelled (may have already completed)"
        logger.warning(f"Failed to cancel job {request_id}")

    return CancelResponse(
        request_id=request_id,
        status="cancelled" if cancelled else "failed",
        cancelled_jobs=1 if cancelled else 0,
        message=message,
        timestamp=datetime.now(timezone.utc)
    )
