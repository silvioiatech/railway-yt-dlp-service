"""
Batch download service for managing multiple concurrent downloads.

Provides batch job creation, status tracking, and cancellation with
concurrent download limits and error handling strategies.
"""
import asyncio
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import Settings
from app.core.state import JobState, JobStateManager
from app.models.enums import JobStatus
from app.models.requests import BatchDownloadRequest, DownloadRequest
from app.models.responses import (
    BatchDownloadResponse,
    FileInfo,
    JobInfo,
    ProgressInfo,
    VideoMetadata,
)
from app.services.queue_manager import QueueManager

logger = logging.getLogger(__name__)


class BatchState:
    """
    Thread-safe batch state container.

    Tracks batch job status, individual jobs, and aggregate statistics.
    """

    def __init__(self, batch_id: str, urls: List[str], request: BatchDownloadRequest):
        self.batch_id = batch_id
        self.urls = urls
        self.request = request
        self.status = JobStatus.QUEUED
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.job_ids: List[str] = []
        self.error_message: Optional[str] = None
        self._lock = threading.RLock()

    def add_job_id(self, job_id: str):
        """Add a job ID to the batch."""
        with self._lock:
            self.job_ids.append(job_id)

    def set_running(self):
        """Mark batch as running."""
        with self._lock:
            self.status = JobStatus.RUNNING
            self.started_at = datetime.now(timezone.utc)

    def set_completed(self):
        """Mark batch as completed."""
        with self._lock:
            self.status = JobStatus.COMPLETED
            self.completed_at = datetime.now(timezone.utc)

    def set_failed(self, error_message: str):
        """Mark batch as failed."""
        with self._lock:
            self.status = JobStatus.FAILED
            self.error_message = error_message
            self.completed_at = datetime.now(timezone.utc)

    def set_cancelled(self):
        """Mark batch as cancelled."""
        with self._lock:
            self.status = JobStatus.CANCELLED
            self.completed_at = datetime.now(timezone.utc)


class BatchService:
    """
    Service for managing batch download operations.

    Handles batch creation, concurrent download limiting, progress tracking,
    and error handling according to batch configuration.
    """

    def __init__(
        self,
        queue_manager: QueueManager,
        job_state_manager: JobStateManager,
        settings: Settings
    ):
        """
        Initialize batch service.

        Args:
            queue_manager: Queue manager for job submission
            job_state_manager: Job state manager for tracking
            settings: Application settings
        """
        self.queue_manager = queue_manager
        self.job_state_manager = job_state_manager
        self.settings = settings
        self._batches: Dict[str, BatchState] = {}
        self._lock = threading.RLock()

    async def create_batch(
        self,
        request: BatchDownloadRequest
    ) -> BatchDownloadResponse:
        """
        Create a batch download job.

        Creates individual download jobs for each URL with concurrent limiting
        and error handling according to batch configuration.

        Args:
            request: Batch download request

        Returns:
            BatchDownloadResponse: Initial batch status
        """
        # Generate unique batch ID
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"

        logger.info(
            f"Creating batch {batch_id} with {len(request.urls)} URLs, "
            f"concurrent_limit={request.concurrent_limit}, "
            f"stop_on_error={request.stop_on_error}"
        )

        # Create batch state
        batch_state = BatchState(
            batch_id=batch_id,
            urls=request.urls,
            request=request
        )

        with self._lock:
            self._batches[batch_id] = batch_state

        # Create individual download requests for each URL
        job_ids = []
        for idx, url in enumerate(request.urls):
            # Generate unique job ID
            job_id = f"{batch_id}_job_{idx:03d}"

            # Create download request from batch request
            download_request = DownloadRequest(
                url=url,
                quality=request.quality,
                custom_format=request.custom_format,
                video_format=request.video_format,
                audio_only=request.audio_only,
                audio_format=request.audio_format,
                audio_quality=request.audio_quality,
                download_subtitles=request.download_subtitles,
                subtitle_languages=request.subtitle_languages,
                subtitle_format=request.subtitle_format,
                embed_subtitles=request.embed_subtitles,
                write_thumbnail=request.write_thumbnail,
                embed_thumbnail=request.embed_thumbnail,
                embed_metadata=request.embed_metadata,
                write_info_json=request.write_info_json,
                path_template=request.path_template.replace(
                    "{batch_id}", batch_id
                ) if request.path_template else None,
                cookies_id=request.cookies_id,
                timeout_sec=request.timeout_sec,
                webhook_url=request.webhook_url
            )

            # Create job state
            job = self.job_state_manager.create_job(
                request_id=job_id,
                url=url,
                payload=download_request.model_dump(),
                status=JobStatus.QUEUED
            )
            job.add_log(f"Job created as part of batch {batch_id}", "INFO")

            job_ids.append(job_id)
            batch_state.add_job_id(job_id)

        # Start batch processing in background
        asyncio.create_task(
            self._process_batch(
                batch_id=batch_id,
                job_ids=job_ids,
                concurrent_limit=request.concurrent_limit,
                stop_on_error=request.stop_on_error
            )
        )

        logger.info(f"Batch {batch_id} created with {len(job_ids)} jobs")

        # Return initial batch status
        return await self.get_batch_status(batch_id)

    async def _process_batch(
        self,
        batch_id: str,
        job_ids: List[str],
        concurrent_limit: int,
        stop_on_error: bool
    ):
        """
        Process batch downloads with concurrency control.

        Args:
            batch_id: Batch identifier
            job_ids: List of job IDs in the batch
            concurrent_limit: Maximum concurrent downloads
            stop_on_error: Whether to stop on first error
        """
        batch_state = self._batches.get(batch_id)
        if not batch_state:
            logger.error(f"Batch {batch_id} not found for processing")
            return

        batch_state.set_running()
        logger.info(f"Starting batch processing for {batch_id}")

        # Import here to avoid circular dependency
        from app.api.v1.download import process_download_job

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrent_limit)

        # Track if we should stop on error
        should_stop = asyncio.Event()

        async def process_job_with_limit(job_id: str):
            """Process a single job with concurrency limit."""
            # Wait for semaphore
            async with semaphore:
                if should_stop.is_set():
                    # Cancel job if stop_on_error triggered
                    job = self.job_state_manager.get_job(job_id)
                    if job:
                        job.set_cancelled()
                        job.add_log("Job cancelled due to batch error", "INFO")
                    return

                try:
                    # Get job state
                    job = self.job_state_manager.get_job(job_id)
                    if not job:
                        logger.error(f"Job {job_id} not found")
                        return

                    # Submit to queue manager
                    self.queue_manager.submit_job(
                        job_id=job_id,
                        coroutine=process_download_job(
                            request_id=job_id,
                            payload=DownloadRequest(**job.payload),
                            job_state_manager=self.job_state_manager,
                            settings=self.settings
                        )
                    )

                    # Wait for job completion by polling
                    while True:
                        await asyncio.sleep(1)
                        job = self.job_state_manager.get_job(job_id)
                        if not job:
                            break
                        if job.status in [
                            JobStatus.COMPLETED,
                            JobStatus.FAILED,
                            JobStatus.CANCELLED
                        ]:
                            break

                    # Check if job failed and stop_on_error is enabled
                    if stop_on_error and job and job.status == JobStatus.FAILED:
                        logger.warning(
                            f"Job {job_id} failed, triggering batch stop"
                        )
                        should_stop.set()
                        batch_state.set_failed(
                            f"Job {job_id} failed: {job.error_message}"
                        )

                except Exception as e:
                    logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
                    if stop_on_error:
                        should_stop.set()
                        batch_state.set_failed(f"Job processing error: {str(e)}")

        # Process all jobs concurrently
        try:
            tasks = [process_job_with_limit(job_id) for job_id in job_ids]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Mark batch as completed if not already failed/cancelled
            if batch_state.status == JobStatus.RUNNING:
                batch_state.set_completed()
                logger.info(f"Batch {batch_id} completed successfully")

        except Exception as e:
            logger.error(f"Batch {batch_id} processing error: {e}", exc_info=True)
            batch_state.set_failed(f"Batch processing error: {str(e)}")

    async def get_batch_status(self, batch_id: str) -> BatchDownloadResponse:
        """
        Get status of a batch download.

        Args:
            batch_id: Batch identifier

        Returns:
            BatchDownloadResponse: Current batch status

        Raises:
            ValueError: If batch not found
        """
        batch_state = self._batches.get(batch_id)
        if not batch_state:
            raise ValueError(f"Batch not found: {batch_id}")

        # Collect job information
        jobs_info: List[JobInfo] = []
        completed_count = 0
        failed_count = 0
        running_count = 0
        queued_count = 0
        cancelled_count = 0

        for job_id in batch_state.job_ids:
            job = self.job_state_manager.get_job(job_id)
            if not job:
                continue

            # Count by status
            if job.status == JobStatus.COMPLETED:
                completed_count += 1
            elif job.status == JobStatus.FAILED:
                failed_count += 1
            elif job.status == JobStatus.RUNNING:
                running_count += 1
            elif job.status == JobStatus.QUEUED:
                queued_count += 1
            elif job.status == JobStatus.CANCELLED:
                cancelled_count += 1

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
                    file_path=str(job.file_path.relative_to(self.settings.STORAGE_DIR)),
                    size_bytes=job.file_size,
                    format=job.file_path.suffix.lstrip('.'),
                    mime_type=None
                )

            # Extract title from metadata
            title = None
            if job.metadata:
                title = job.metadata.get('title')

            jobs_info.append(
                JobInfo(
                    job_id=job.request_id,
                    url=job.url,
                    status=job.status,
                    title=title,
                    progress=progress,
                    file_info=file_info,
                    error=job.error_message,
                    created_at=job.created_at,
                    completed_at=job.completed_at
                )
            )

        # Calculate duration if completed
        duration_sec = None
        if batch_state.started_at and batch_state.completed_at:
            duration_sec = (
                batch_state.completed_at - batch_state.started_at
            ).total_seconds()

        return BatchDownloadResponse(
            batch_id=batch_id,
            status=batch_state.status,
            total_jobs=len(batch_state.job_ids),
            completed_jobs=completed_count,
            failed_jobs=failed_count,
            running_jobs=running_count,
            queued_jobs=queued_count,
            jobs=jobs_info,
            created_at=batch_state.created_at,
            started_at=batch_state.started_at,
            completed_at=batch_state.completed_at,
            duration_sec=duration_sec,
            error=batch_state.error_message
        )

    async def cancel_batch(self, batch_id: str) -> int:
        """
        Cancel a batch download.

        Cancels all pending and running jobs in the batch.

        Args:
            batch_id: Batch identifier

        Returns:
            int: Number of jobs cancelled

        Raises:
            ValueError: If batch not found
        """
        batch_state = self._batches.get(batch_id)
        if not batch_state:
            raise ValueError(f"Batch not found: {batch_id}")

        logger.info(f"Cancelling batch {batch_id}")

        # Cancel all jobs
        cancelled_count = 0
        for job_id in batch_state.job_ids:
            job = self.job_state_manager.get_job(job_id)
            if not job:
                continue

            # Only cancel non-terminal jobs
            if job.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                # Try to cancel in queue manager
                self.queue_manager.cancel_job(job_id)

                # Mark as cancelled
                job.set_cancelled()
                job.add_log("Job cancelled as part of batch cancellation", "INFO")
                cancelled_count += 1

        # Mark batch as cancelled
        batch_state.set_cancelled()

        logger.info(f"Cancelled {cancelled_count} jobs in batch {batch_id}")

        return cancelled_count

    def get_batch_list(self) -> List[str]:
        """
        Get list of all batch IDs.

        Returns:
            List[str]: List of batch identifiers
        """
        with self._lock:
            return list(self._batches.keys())

    def cleanup_old_batches(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed batches.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            int: Number of batches cleaned up
        """
        now = datetime.now(timezone.utc)
        cleaned = 0

        with self._lock:
            batch_ids_to_remove = []

            for batch_id, batch_state in self._batches.items():
                # Only clean up terminal states
                if batch_state.status not in [
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED
                ]:
                    continue

                # Check age
                if batch_state.completed_at:
                    age_hours = (now - batch_state.completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        batch_ids_to_remove.append(batch_id)

            # Remove old batches
            for batch_id in batch_ids_to_remove:
                del self._batches[batch_id]
                cleaned += 1

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old batches")

        return cleaned


# Global batch service instance
_batch_service: Optional[BatchService] = None
_service_lock = threading.Lock()


def get_batch_service(
    queue_manager: QueueManager,
    job_state_manager: JobStateManager,
    settings: Settings
) -> BatchService:
    """
    Get the global BatchService instance.

    Args:
        queue_manager: Queue manager dependency
        job_state_manager: Job state manager dependency
        settings: Application settings

    Returns:
        BatchService: Global batch service instance
    """
    global _batch_service
    if _batch_service is None:
        with _service_lock:
            if _batch_service is None:
                _batch_service = BatchService(
                    queue_manager=queue_manager,
                    job_state_manager=job_state_manager,
                    settings=settings
                )
    return _batch_service
