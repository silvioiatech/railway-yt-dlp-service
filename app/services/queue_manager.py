"""
Background job queue manager with asyncio integration.

This module provides a thread-safe queue manager for background download
jobs using ThreadPoolExecutor with asyncio.run_coroutine_threadsafe bridge.
"""
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable, Dict, Optional

from app.config import get_settings
from app.core.exceptions import QueueFullError

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Manage background job queue with thread pool execution.

    Provides a bridge between sync ThreadPoolExecutor and async coroutines,
    allowing async download jobs to run in background threads while maintaining
    proper lifecycle management.
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        max_concurrent_downloads: Optional[int] = None
    ):
        """
        Initialize queue manager.

        Args:
            max_workers: Maximum worker threads (defaults to config)
            max_concurrent_downloads: Max concurrent downloads (defaults to config)
        """
        settings = get_settings()
        self.max_workers = max_workers or settings.WORKERS
        self.max_concurrent_downloads = (
            max_concurrent_downloads or settings.MAX_CONCURRENT_DOWNLOADS
        )

        self.executor: Optional[ThreadPoolExecutor] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.shutdown_event = threading.Event()
        self.active_jobs: Dict[str, Future] = {}
        self.job_semaphore: Optional[asyncio.Semaphore] = None
        self._lock = threading.RLock()
        self._started = False

    async def start(self):
        """
        Start the queue manager.

        Creates thread pool executor and sets up event loop reference.
        """
        if self._started:
            logger.warning("Queue manager already started")
            return

        with self._lock:
            if self._started:
                return

            logger.info(
                f"Starting queue manager with {self.max_workers} workers, "
                f"max {self.max_concurrent_downloads} concurrent downloads"
            )

            # Create executor
            self.executor = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="download-worker-"
            )

            # Get current event loop
            self.event_loop = asyncio.get_event_loop()

            # Create semaphore for concurrency control
            self.job_semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

            self._started = True
            logger.info("Queue manager started successfully")

    async def shutdown(self, wait: bool = True, timeout: float = 30.0):
        """
        Shutdown the queue manager gracefully.

        Args:
            wait: Whether to wait for running jobs to complete
            timeout: Maximum time to wait for shutdown
        """
        if not self._started:
            logger.warning("Queue manager not started")
            return

        logger.info("Shutting down queue manager...")
        self.shutdown_event.set()

        with self._lock:
            if self.executor:
                # Cancel all active jobs if not waiting
                if not wait:
                    logger.info(f"Cancelling {len(self.active_jobs)} active jobs")
                    for job_id, future in self.active_jobs.items():
                        if not future.done():
                            future.cancel()
                            logger.debug(f"Cancelled job {job_id}")

                # Shutdown executor
                self.executor.shutdown(wait=wait, cancel_futures=not wait)
                logger.info("Thread pool executor shutdown complete")

            self.executor = None
            self.event_loop = None
            self._started = False

        logger.info("Queue manager shutdown complete")

    def submit_job(
        self,
        job_id: str,
        coroutine: Any,
        callback: Optional[Callable[[Future], None]] = None
    ) -> Future:
        """
        Submit an async coroutine to run in the thread pool.

        Args:
            job_id: Unique job identifier
            coroutine: Async coroutine to execute
            callback: Optional callback when job completes

        Returns:
            Future object for the submitted job

        Raises:
            QueueFullError: If queue is at capacity
            RuntimeError: If queue manager not started
        """
        if not self._started or not self.executor:
            raise RuntimeError("Queue manager not started")

        if self.shutdown_event.is_set():
            raise RuntimeError("Queue manager is shutting down")

        with self._lock:
            # Check if we're at capacity (atomic with lock)
            if len(self.active_jobs) >= self.max_concurrent_downloads * 2:
                logger.warning(f"Queue at capacity: {len(self.active_jobs)} active jobs")
                raise QueueFullError(len(self.active_jobs))

            # Submit coroutine to executor
            future = self.executor.submit(
                self._run_coroutine,
                job_id,
                coroutine
            )

            # Store active job
            self.active_jobs[job_id] = future

            # Add completion callback
            if callback:
                future.add_done_callback(callback)

            # Add cleanup callback
            future.add_done_callback(lambda f: self._cleanup_job(job_id))

            logger.info(
                f"Submitted job {job_id} to queue "
                f"({len(self.active_jobs)} active jobs)"
            )

            return future

    def _run_coroutine(self, job_id: str, coroutine: Any) -> Any:
        """
        Run async coroutine in executor thread.

        Args:
            job_id: Job identifier
            coroutine: Async coroutine to run

        Returns:
            Result of coroutine execution
        """
        if not self.event_loop:
            raise RuntimeError("Event loop not available")

        try:
            logger.debug(f"Running job {job_id} in executor thread")

            # Use run_coroutine_threadsafe to execute in event loop
            future = asyncio.run_coroutine_threadsafe(coroutine, self.event_loop)

            # Wait for completion with timeout
            # Extract timeout from coroutine if available, default to 2 hours
            timeout = getattr(coroutine, 'timeout_sec', 7200)  # Default 2 hours
            result = future.result(timeout=timeout)

            logger.debug(f"Job {job_id} completed successfully")
            return result

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            raise

    def _cleanup_job(self, job_id: str):
        """
        Clean up completed job from active jobs.

        Args:
            job_id: Job identifier to clean up
        """
        with self._lock:
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
                logger.debug(
                    f"Cleaned up job {job_id} "
                    f"({len(self.active_jobs)} active jobs remaining)"
                )

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a job.

        Args:
            job_id: Job identifier

        Returns:
            Status dictionary or None if job not found
        """
        with self._lock:
            future = self.active_jobs.get(job_id)
            if not future:
                return None

            status = {
                'job_id': job_id,
                'running': future.running(),
                'done': future.done(),
                'cancelled': future.cancelled(),
            }

            if future.done() and not future.cancelled():
                try:
                    future.result()
                    status['success'] = True
                except Exception as e:
                    status['success'] = False
                    status['error'] = str(e)

            return status

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job identifier to cancel

        Returns:
            True if job was cancelled, False if not found or already done
        """
        with self._lock:
            future = self.active_jobs.get(job_id)
            if not future:
                logger.warning(f"Job {job_id} not found for cancellation")
                return False

            if future.done():
                logger.warning(f"Job {job_id} already completed")
                return False

            cancelled = future.cancel()
            if cancelled:
                logger.info(f"Cancelled job {job_id}")
            else:
                logger.warning(f"Failed to cancel job {job_id}")

            return cancelled

    def get_stats(self) -> Dict[str, Any]:
        """
        Get queue manager statistics.

        Returns:
            Dictionary with queue statistics
        """
        with self._lock:
            active_count = len(self.active_jobs)
            running_count = sum(1 for f in self.active_jobs.values() if f.running())
            done_count = sum(1 for f in self.active_jobs.values() if f.done())

            return {
                'started': self._started,
                'max_workers': self.max_workers,
                'max_concurrent_downloads': self.max_concurrent_downloads,
                'active_jobs': active_count,
                'running_jobs': running_count,
                'completed_jobs': done_count,
                'shutdown_pending': self.shutdown_event.is_set(),
            }

    def is_healthy(self) -> bool:
        """
        Check if queue manager is healthy.

        Returns:
            True if queue is healthy and accepting jobs
        """
        if not self._started:
            return False

        if self.shutdown_event.is_set():
            return False

        # Check executor status safely (handle different executor implementations)
        try:
            if not self.executor or self.executor._shutdown:
                return False
        except AttributeError:
            # Fallback for executor implementations without _shutdown attribute
            if not self.executor:
                return False

        return True

    async def wait_for_capacity(self, timeout: float = 60.0) -> bool:
        """
        Wait for queue capacity to become available.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if capacity is available, False if timeout
        """
        if not self.job_semaphore:
            return False

        try:
            async with asyncio.timeout(timeout):
                async with self.job_semaphore:
                    return True
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for queue capacity after {timeout}s")
            return False

    # Note: Context manager support removed because __exit__ cannot properly
    # handle async shutdown. Users should call shutdown() explicitly.


# Global queue manager instance
_queue_manager: Optional[QueueManager] = None
_manager_lock = threading.Lock()


def get_queue_manager() -> QueueManager:
    """
    Get the global QueueManager instance.

    Returns:
        QueueManager: Global queue manager

    Note:
        The queue manager must be started before use with start()
    """
    global _queue_manager
    if _queue_manager is None:
        with _manager_lock:
            if _queue_manager is None:
                _queue_manager = QueueManager()
    return _queue_manager


async def initialize_queue_manager() -> QueueManager:
    """
    Initialize and start the global queue manager.

    Returns:
        QueueManager: Started queue manager instance
    """
    manager = get_queue_manager()
    if not manager._started:
        await manager.start()
    return manager


async def shutdown_queue_manager(wait: bool = True, timeout: float = 30.0):
    """
    Shutdown the global queue manager.

    Args:
        wait: Whether to wait for running jobs
        timeout: Maximum wait time
    """
    global _queue_manager
    if _queue_manager and _queue_manager._started:
        await _queue_manager.shutdown(wait=wait, timeout=timeout)
        _queue_manager = None
