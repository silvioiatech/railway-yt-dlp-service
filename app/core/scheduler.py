"""
File deletion scheduler for automatic cleanup.

This module provides a thread-safe, singleton scheduler for automatic
file deletion with cancellation support. Copied from the excellent
implementation in process.py.
"""
import heapq
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Callable, Optional, NamedTuple

logger = logging.getLogger(__name__)


class DeletionTask(NamedTuple):
    """Task for scheduled file deletion."""
    timestamp: float
    task_id: str
    file_path: Path
    log_callback: Optional[Callable[[str, str], None]]


class FileDeletionScheduler:
    """Centralized scheduler for file deletions with cancellable tasks."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self._heap = []
        self._cancelled_tasks = set()
        self._condition = threading.Condition()
        self._worker_thread = None
        self._shutdown = False

        self._start_worker()

    def _start_worker(self):
        """Start the background worker thread."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="FileDeletionWorker",
                daemon=True  # Allow process to exit even if thread is stuck
            )
            self._worker_thread.start()
            logger.info("File deletion scheduler worker started")

    def _worker_loop(self):
        """Main worker loop that processes scheduled deletions."""
        logger.info("File deletion worker started")

        while not self._shutdown:
            with self._condition:
                # Wait until we have tasks or are shutting down
                while not self._heap and not self._shutdown:
                    self._condition.wait()

                if self._shutdown:
                    break

                # Get the next task
                current_time = time.time()

                # Remove cancelled tasks from the front of the heap
                while self._heap and self._heap[0].task_id in self._cancelled_tasks:
                    cancelled_task = heapq.heappop(self._heap)
                    self._cancelled_tasks.discard(cancelled_task.task_id)
                    logger.debug(f"Removed cancelled deletion task: {cancelled_task.task_id}")

                if not self._heap:
                    continue

                next_task = self._heap[0]

                # If it's time to execute, pop and process
                if next_task.timestamp <= current_time:
                    task = heapq.heappop(self._heap)

                    # Check if task was cancelled
                    if task.task_id in self._cancelled_tasks:
                        self._cancelled_tasks.discard(task.task_id)
                        logger.debug(f"Skipping cancelled deletion task: {task.task_id}")
                        continue

                    # Process the deletion outside the lock
                    self._condition.release()
                    try:
                        self._execute_deletion(task)
                    finally:
                        self._condition.acquire()
                else:
                    # Wait until the next task is ready
                    wait_time = next_task.timestamp - current_time
                    self._condition.wait(timeout=min(wait_time, 60))  # Max wait 1 minute

        logger.info("File deletion worker stopped")

    def _execute_deletion(self, task: DeletionTask):
        """Execute a file deletion task."""
        try:
            if task.file_path.exists():
                task.file_path.unlink()
                msg = f"Auto-deleted file: {task.file_path}"
                logger.info(msg)
                if task.log_callback:
                    task.log_callback(msg, "INFO")
            else:
                msg = f"File already deleted: {task.file_path}"
                logger.debug(msg)
                if task.log_callback:
                    task.log_callback(msg, "INFO")
        except Exception as e:
            msg = f"Failed to auto-delete file {task.file_path}: {e}"
            logger.error(msg)
            if task.log_callback:
                task.log_callback(msg, "ERROR")

    def schedule_deletion(
        self,
        file_path: Path,
        delay_seconds: int = 3600,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> tuple[str, float]:
        """
        Schedule a file for deletion after delay_seconds.

        Args:
            file_path: Path to file to delete
            delay_seconds: Delay before deletion in seconds
            log_callback: Optional callback for logging (msg, level)

        Returns:
            tuple[str, float]: (task_id, scheduled_timestamp)
        """
        task_id = str(uuid.uuid4())
        scheduled_time = time.time() + delay_seconds

        task = DeletionTask(
            timestamp=scheduled_time,
            task_id=task_id,
            file_path=file_path,
            log_callback=log_callback
        )

        with self._condition:
            heapq.heappush(self._heap, task)
            self._condition.notify()  # Wake up worker

        logger.debug(f"Scheduled deletion of {file_path} at {scheduled_time} (task: {task_id})")
        return task_id, scheduled_time

    def cancel_deletion(self, task_id: str) -> bool:
        """
        Cancel a scheduled deletion.

        Args:
            task_id: ID of task to cancel

        Returns:
            bool: True if task was found and cancelled, False otherwise
        """
        with self._condition:
            # Add to cancelled set - worker will skip these tasks
            if any(task.task_id == task_id for task in self._heap):
                self._cancelled_tasks.add(task_id)
                logger.debug(f"Cancelled deletion task: {task_id}")
                return True
            return False

    def shutdown(self):
        """Gracefully shutdown the scheduler."""
        logger.info("Shutting down file deletion scheduler")

        with self._condition:
            self._shutdown = True
            self._condition.notify_all()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
            if self._worker_thread.is_alive():
                logger.warning("File deletion worker did not shut down gracefully")

        logger.info("File deletion scheduler shut down complete")

    def get_pending_count(self) -> int:
        """Get the number of pending deletion tasks."""
        with self._condition:
            return len(self._heap) - len(self._cancelled_tasks)


# Global scheduler instance
def get_scheduler() -> FileDeletionScheduler:
    """Get the global FileDeletionScheduler instance."""
    return FileDeletionScheduler()
