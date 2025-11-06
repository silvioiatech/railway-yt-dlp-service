"""
Application state management for job tracking and status.

Provides in-memory job state tracking with thread-safe access.
Can be extended to use database backend in the future.
"""
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.models.enums import JobStatus


class JobState:
    """
    Thread-safe job state container.

    Tracks download job status, progress, logs, and metadata.
    """

    def __init__(self, request_id: str, **kwargs):
        self.request_id = request_id
        self.status = kwargs.get('status', JobStatus.QUEUED)
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.updated_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = kwargs.get('started_at')
        self.completed_at: Optional[datetime] = kwargs.get('completed_at')

        # Request data
        self.url: str = kwargs.get('url', '')
        self.payload: Dict[str, Any] = kwargs.get('payload', {})

        # Progress tracking
        self.progress_percent: float = 0.0
        self.bytes_downloaded: int = 0
        self.bytes_total: int = 0
        self.download_speed: float = 0.0
        self.eta_seconds: Optional[int] = None

        # Results
        self.file_path: Optional[Path] = kwargs.get('file_path')
        self.file_url: Optional[str] = kwargs.get('file_url')
        self.file_size: int = kwargs.get('file_size', 0)
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})

        # Logs
        self.logs: List[Dict[str, Any]] = []
        self.error_message: Optional[str] = None

        # Deletion scheduling
        self.deletion_task_id: Optional[str] = None
        self.deletion_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job state to dictionary for API responses."""
        return {
            'request_id': self.request_id,
            'status': self.status.value if isinstance(self.status, JobStatus) else self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'url': self.url,
            'progress': {
                'percent': self.progress_percent,
                'bytes_downloaded': self.bytes_downloaded,
                'bytes_total': self.bytes_total,
                'speed': self.download_speed,
                'eta_seconds': self.eta_seconds,
            },
            'file_path': str(self.file_path) if self.file_path else None,
            'file_url': self.file_url,
            'file_size': self.file_size,
            'metadata': self.metadata,
            'logs': self.logs[-100:],  # Last 100 log entries
            'error_message': self.error_message,
            'deletion_scheduled': self.deletion_time is not None,
            'deletion_time': datetime.fromtimestamp(self.deletion_time).isoformat() if self.deletion_time else None,
        }

    def update_progress(
        self,
        percent: Optional[float] = None,
        bytes_downloaded: Optional[int] = None,
        bytes_total: Optional[int] = None,
        speed: Optional[float] = None,
        eta: Optional[int] = None
    ):
        """Update download progress."""
        if percent is not None:
            self.progress_percent = percent
        if bytes_downloaded is not None:
            self.bytes_downloaded = bytes_downloaded
        if bytes_total is not None:
            self.bytes_total = bytes_total
        if speed is not None:
            self.download_speed = speed
        if eta is not None:
            self.eta_seconds = eta
        self.updated_at = datetime.now(timezone.utc)

    def add_log(self, message: str, level: str = "INFO"):
        """Add a log entry."""
        self.logs.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level,
            'message': message
        })
        self.updated_at = datetime.now(timezone.utc)

    def set_running(self):
        """Mark job as running."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def set_completed(self, file_path: Optional[Path] = None, file_url: Optional[str] = None):
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        if file_path:
            self.file_path = file_path
        if file_url:
            self.file_url = file_url

    def set_failed(self, error_message: str):
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def set_cancelled(self):
        """Mark job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class JobStateManager:
    """
    Thread-safe manager for all job states.

    Provides centralized access to job information with thread safety.
    """

    def __init__(self):
        self._jobs: Dict[str, JobState] = {}
        self._lock = threading.RLock()

    def create_job(self, request_id: str, **kwargs) -> JobState:
        """
        Create a new job state.

        Args:
            request_id: Unique job identifier
            **kwargs: Job initialization parameters

        Returns:
            JobState: Created job state
        """
        with self._lock:
            job = JobState(request_id, **kwargs)
            self._jobs[request_id] = job
            return job

    def get_job(self, request_id: str) -> Optional[JobState]:
        """
        Get job state by ID.

        Args:
            request_id: Job identifier

        Returns:
            Optional[JobState]: Job state or None if not found
        """
        with self._lock:
            return self._jobs.get(request_id)

    def update_job(self, request_id: str, **kwargs) -> bool:
        """
        Update job state.

        Args:
            request_id: Job identifier
            **kwargs: Fields to update

        Returns:
            bool: True if job was found and updated
        """
        with self._lock:
            job = self._jobs.get(request_id)
            if not job:
                return False

            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)

            job.updated_at = datetime.now(timezone.utc)
            return True

    def delete_job(self, request_id: str) -> bool:
        """
        Delete job state.

        Args:
            request_id: Job identifier

        Returns:
            bool: True if job was found and deleted
        """
        with self._lock:
            if request_id in self._jobs:
                del self._jobs[request_id]
                return True
            return False

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: Optional[int] = None
    ) -> List[JobState]:
        """
        List all jobs, optionally filtered by status.

        Args:
            status: Filter by job status
            limit: Maximum number of jobs to return

        Returns:
            List[JobState]: List of job states
        """
        with self._lock:
            jobs = list(self._jobs.values())

            if status:
                jobs = [j for j in jobs if j.status == status]

            # Sort by created_at descending (newest first)
            jobs.sort(key=lambda x: x.created_at, reverse=True)

            if limit:
                jobs = jobs[:limit]

            return jobs

    def get_stats(self) -> Dict[str, Any]:
        """
        Get job statistics.

        Returns:
            Dict[str, Any]: Statistics summary
        """
        with self._lock:
            total = len(self._jobs)
            by_status = {}

            for job in self._jobs.values():
                status = job.status.value if isinstance(job.status, JobStatus) else job.status
                by_status[status] = by_status.get(status, 0) + 1

            return {
                'total_jobs': total,
                'by_status': by_status,
                'queued': by_status.get(JobStatus.QUEUED.value, 0),
                'running': by_status.get(JobStatus.RUNNING.value, 0),
                'completed': by_status.get(JobStatus.COMPLETED.value, 0),
                'failed': by_status.get(JobStatus.FAILED.value, 0),
                'cancelled': by_status.get(JobStatus.CANCELLED.value, 0),
            }


# Global job state manager instance
_job_state_manager: Optional[JobStateManager] = None
_manager_lock = threading.Lock()


def get_job_state_manager() -> JobStateManager:
    """Get the global JobStateManager instance."""
    global _job_state_manager
    if _job_state_manager is None:
        with _manager_lock:
            if _job_state_manager is None:
                _job_state_manager = JobStateManager()
    return _job_state_manager
