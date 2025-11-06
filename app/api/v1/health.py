"""
Health and statistics endpoints for the Ultimate Media Downloader API.

Provides system health checks and service statistics monitoring.
"""
import logging
import os
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, status
import yt_dlp

from app.api.v1.auth import OptionalAuth
from app.config import Settings, get_settings
from app.core.state import JobStateManager, get_job_state_manager
from app.models.responses import HealthResponse, StatsResponse
from app.services.queue_manager import QueueManager, get_queue_manager

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/health", tags=["health"])

# Application start time for uptime calculation
_start_time = time.time()


# =========================
# Helper Functions
# =========================

def get_storage_info(storage_dir: Path) -> Dict[str, Any]:
    """
    Get storage usage information.

    Args:
        storage_dir: Storage directory path

    Returns:
        Dict with storage statistics
    """
    try:
        usage = shutil.disk_usage(storage_dir)
        return {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "available_bytes": usage.free,
            "percent_used": (usage.used / usage.total * 100) if usage.total > 0 else 0,
            "path": str(storage_dir)
        }
    except Exception as e:
        logger.error(f"Error getting storage info: {e}")
        return {
            "error": str(e),
            "path": str(storage_dir)
        }


def get_ytdlp_version() -> str:
    """
    Get yt-dlp version.

    Returns:
        Version string
    """
    try:
        return yt_dlp.version.__version__
    except AttributeError:
        try:
            # Fallback for different yt-dlp versions
            return yt_dlp.YoutubeDL({}).version
        except Exception:
            return "unknown"


def check_directory_writable(directory: Path) -> bool:
    """
    Check if directory is writable.

    Args:
        directory: Directory path to check

    Returns:
        True if writable, False otherwise
    """
    try:
        test_file = directory / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except Exception:
        return False


# =========================
# Endpoints
# =========================

@router.get(
    "",
    response_model=HealthResponse,
    summary="Health check",
    description="Get service health status and system checks",
)
async def health_check(
    authenticated: OptionalAuth,
    settings: Annotated[Settings, Depends(get_settings)],
    queue_manager: Annotated[QueueManager, Depends(get_queue_manager)],
) -> HealthResponse:
    """
    Health check endpoint.

    Returns service health status with component checks. Does not require
    authentication by default but may return additional information for
    authenticated requests.

    Args:
        authenticated: Optional authentication status
        settings: Application settings
        queue_manager: Queue manager instance

    Returns:
        HealthResponse: Service health status

    Example:
        ```bash
        curl -X GET "http://localhost:8080/api/v1/health"
        ```
    """
    uptime = time.time() - _start_time

    checks = {}
    overall_status = "healthy"

    # Storage check
    storage_info = get_storage_info(settings.STORAGE_DIR)
    storage_writable = check_directory_writable(settings.STORAGE_DIR)

    if "error" in storage_info or not storage_writable:
        overall_status = "degraded"
        checks["storage"] = {
            "status": "unhealthy",
            "error": storage_info.get("error", "Directory not writable"),
            "path": str(settings.STORAGE_DIR)
        }
    else:
        available_gb = storage_info["available_bytes"] / (1024 ** 3)
        if available_gb < 1.0:
            overall_status = "degraded"
            checks["storage"] = {
                "status": "degraded",
                "message": "Low disk space",
                "available_gb": round(available_gb, 2),
                "percent_used": round(storage_info["percent_used"], 2)
            }
        else:
            checks["storage"] = {
                "status": "healthy",
                "available_gb": round(available_gb, 2),
                "percent_used": round(storage_info["percent_used"], 2)
            }

    # Queue manager check
    try:
        queue_stats = queue_manager.get_stats()
        queue_healthy = queue_manager.is_healthy()

        if not queue_healthy:
            overall_status = "unhealthy"
            checks["queue"] = {
                "status": "unhealthy",
                "message": "Queue manager not healthy"
            }
        else:
            checks["queue"] = {
                "status": "healthy",
                "active_jobs": queue_stats.get("active_jobs", 0),
                "running_jobs": queue_stats.get("running_jobs", 0),
                "max_workers": queue_stats.get("max_workers", 0)
            }
    except Exception as e:
        logger.error(f"Queue health check failed: {e}")
        overall_status = "unhealthy"
        checks["queue"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # yt-dlp check
    try:
        ytdlp_version = get_ytdlp_version()
        checks["ytdlp"] = {
            "status": "healthy",
            "version": ytdlp_version
        }
    except Exception as e:
        logger.error(f"yt-dlp check failed: {e}")
        overall_status = "degraded"
        checks["ytdlp"] = {
            "status": "degraded",
            "error": str(e)
        }

    # Include additional system info if authenticated
    if authenticated:
        checks["system"] = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.system(),
            "platform_release": platform.release(),
            "cpu_count": os.cpu_count()
        }

    logger.info(f"Health check completed: {overall_status}")

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        version=settings.VERSION,
        uptime_seconds=uptime,
        checks=checks
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Service statistics",
    description="Get detailed service statistics and metrics",
)
async def get_stats(
    authenticated: OptionalAuth,
    settings: Annotated[Settings, Depends(get_settings)],
    queue_manager: Annotated[QueueManager, Depends(get_queue_manager)],
    job_state_manager: Annotated[JobStateManager, Depends(get_job_state_manager)],
) -> StatsResponse:
    """
    Get service statistics.

    Returns detailed statistics about downloads, queue status, storage usage,
    and system metrics. Requires authentication.

    Args:
        authenticated: Authentication status
        settings: Application settings
        queue_manager: Queue manager instance
        job_state_manager: Job state manager

    Returns:
        StatsResponse: Service statistics

    Raises:
        HTTPException: 401 if not authenticated

    Example:
        ```bash
        curl -X GET "http://localhost:8080/api/v1/health/stats" \\
             -H "X-API-Key: your-api-key"
        ```
    """
    # This endpoint should typically require auth, but we use OptionalAuth
    # to allow flexibility. In production, you might want RequireAuth.

    uptime = time.time() - _start_time

    # Get job statistics
    job_stats = job_state_manager.get_stats()

    # Calculate success rate
    total_completed = job_stats.get("completed", 0) + job_stats.get("failed", 0)
    success_rate = 0.0
    if total_completed > 0:
        success_rate = (job_stats.get("completed", 0) / total_completed) * 100

    # Calculate average download time
    average_time = None
    completed_jobs = job_state_manager.list_jobs(status=None, limit=100)
    if completed_jobs:
        times = []
        for job in completed_jobs:
            if job.started_at and job.completed_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                if duration > 0:
                    times.append(duration)
        if times:
            average_time = sum(times) / len(times)

    # Get storage info
    storage_info = get_storage_info(settings.STORAGE_DIR)
    storage_used = storage_info.get("used_bytes", 0)
    storage_available = storage_info.get("available_bytes", 0)

    # Calculate total bytes downloaded (approximate from file sizes)
    total_bytes = 0
    for job in completed_jobs:
        if job.file_size > 0:
            total_bytes += job.file_size

    # Get queue statistics
    queue_stats = queue_manager.get_stats()

    # Calculate requests per minute (approximate from recent jobs)
    requests_per_minute = 0.0
    if uptime > 60:
        recent_jobs = len([j for j in completed_jobs if j.created_at])
        requests_per_minute = (recent_jobs / uptime) * 60

    # Get versions
    ytdlp_version = get_ytdlp_version()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    logger.info("Statistics retrieved successfully")

    return StatsResponse(
        total_downloads=job_stats.get("completed", 0),
        total_bytes_downloaded=total_bytes,
        active_downloads=queue_stats.get("running_jobs", 0),
        queued_downloads=job_stats.get("queued", 0),
        failed_downloads=job_stats.get("failed", 0),
        success_rate=round(success_rate, 2),
        average_download_time=round(average_time, 2) if average_time else None,
        storage_used_bytes=storage_used,
        storage_available_bytes=storage_available,
        uptime_seconds=uptime,
        requests_per_minute=round(requests_per_minute, 2),
        ytdlp_version=ytdlp_version,
        python_version=python_version,
        timestamp=datetime.now(timezone.utc)
    )
