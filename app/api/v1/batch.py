"""
Batch download endpoints for the Ultimate Media Downloader API.

Provides endpoints for creating, monitoring, and managing batch downloads
with multiple URLs processed concurrently.
"""
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.auth import RequireAuth
from app.config import Settings, get_settings
from app.core.exceptions import QueueFullError
from app.core.state import JobStateManager, get_job_state_manager
from app.models.requests import BatchDownloadRequest
from app.models.responses import BatchDownloadResponse, CancelResponse
from app.services.batch_service import BatchService, get_batch_service
from app.services.queue_manager import QueueManager, get_queue_manager

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/batch", tags=["batch"])


# =========================
# Dependencies
# =========================

def get_batch_service_dependency(
    queue_manager: Annotated[QueueManager, Depends(get_queue_manager)],
    job_state_manager: Annotated[JobStateManager, Depends(get_job_state_manager)],
    settings: Annotated[Settings, Depends(get_settings)]
) -> BatchService:
    """
    Dependency to get BatchService instance.

    Args:
        queue_manager: Queue manager dependency
        job_state_manager: Job state manager dependency
        settings: Application settings

    Returns:
        BatchService: Configured batch service instance
    """
    return get_batch_service(
        queue_manager=queue_manager,
        job_state_manager=job_state_manager,
        settings=settings
    )


# =========================
# Endpoints
# =========================

@router.post(
    "/download",
    response_model=BatchDownloadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create batch download",
    description="Submit multiple URLs for batch download with concurrent processing",
)
async def create_batch_download(
    payload: BatchDownloadRequest,
    auth: RequireAuth,
    batch_service: Annotated[BatchService, Depends(get_batch_service_dependency)],
) -> BatchDownloadResponse:
    """
    Create a batch download job.

    Submits multiple download requests to be processed concurrently with
    configurable concurrency limits and error handling strategies.

    Args:
        payload: Batch download request with URLs and options
        auth: Authentication dependency
        batch_service: Batch service for job management

    Returns:
        BatchDownloadResponse: Initial batch status with job details

    Raises:
        HTTPException: 503 if queue is full
        HTTPException: 422 if request validation fails
        HTTPException: 413 if batch size exceeds limit

    Example:
        ```bash
        curl -X POST "http://localhost:8080/api/v1/batch/download" \\
             -H "X-API-Key: your-api-key" \\
             -H "Content-Type: application/json" \\
             -d '{
               "urls": [
                 "https://example.com/video1",
                 "https://example.com/video2",
                 "https://example.com/video3"
               ],
               "quality": "1080p",
               "concurrent_limit": 3,
               "stop_on_error": false
             }'
        ```
    """
    # Validate batch size
    if len(payload.urls) > 100:
        logger.warning(f"Batch size {len(payload.urls)} exceeds maximum of 100")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Batch size exceeds maximum of 100 URLs"
        )

    if len(payload.urls) < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one URL is required"
        )

    logger.info(
        f"Creating batch download with {len(payload.urls)} URLs, "
        f"concurrent_limit={payload.concurrent_limit}"
    )

    try:
        # Create batch
        response = await batch_service.create_batch(request=payload)

        logger.info(
            f"Batch {response.batch_id} created successfully with "
            f"{response.total_jobs} jobs"
        )

        return response

    except QueueFullError as e:
        logger.error(f"Queue full when creating batch download")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except ValueError as e:
        logger.error(f"Validation error creating batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating batch download: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create batch download: {str(e)}"
        )


@router.get(
    "/{batch_id}",
    response_model=BatchDownloadResponse,
    summary="Get batch status",
    description="Retrieve the status and progress of a batch download",
)
async def get_batch_status(
    batch_id: str,
    auth: RequireAuth,
    batch_service: Annotated[BatchService, Depends(get_batch_service_dependency)],
) -> BatchDownloadResponse:
    """
    Get the status of a batch download.

    Retrieves current status, progress, and individual job details for
    a specific batch download.

    Args:
        batch_id: Unique batch identifier
        auth: Authentication dependency
        batch_service: Batch service for job management

    Returns:
        BatchDownloadResponse: Complete batch status with all jobs

    Raises:
        HTTPException: 404 if batch not found

    Example:
        ```bash
        curl -X GET "http://localhost:8080/api/v1/batch/batch_abc123" \\
             -H "X-API-Key: your-api-key"
        ```
    """
    try:
        response = await batch_service.get_batch_status(batch_id)
        return response

    except ValueError as e:
        logger.warning(f"Batch not found: {batch_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting batch status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get batch status: {str(e)}"
        )


@router.delete(
    "/{batch_id}",
    response_model=CancelResponse,
    summary="Cancel batch download",
    description="Cancel all pending and running jobs in a batch",
)
async def cancel_batch_download(
    batch_id: str,
    auth: RequireAuth,
    batch_service: Annotated[BatchService, Depends(get_batch_service_dependency)],
) -> CancelResponse:
    """
    Cancel a batch download.

    Attempts to cancel all running and queued jobs in the batch.
    Already completed jobs will not be affected.

    Args:
        batch_id: Unique batch identifier
        auth: Authentication dependency
        batch_service: Batch service for job management

    Returns:
        CancelResponse: Cancellation result with count of cancelled jobs

    Raises:
        HTTPException: 404 if batch not found

    Example:
        ```bash
        curl -X DELETE "http://localhost:8080/api/v1/batch/batch_abc123" \\
             -H "X-API-Key: your-api-key"
        ```
    """
    try:
        cancelled_count = await batch_service.cancel_batch(batch_id)

        logger.info(
            f"Batch {batch_id} cancelled successfully, "
            f"{cancelled_count} jobs cancelled"
        )

        return CancelResponse(
            request_id=batch_id,
            status="cancelled",
            cancelled_jobs=cancelled_count,
            message=f"Batch cancelled successfully, {cancelled_count} jobs cancelled",
            timestamp=datetime.now(timezone.utc)
        )

    except ValueError as e:
        logger.warning(f"Batch not found for cancellation: {batch_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel batch: {str(e)}"
        )
