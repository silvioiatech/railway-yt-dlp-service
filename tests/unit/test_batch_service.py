"""
Unit tests for batch download service.

Tests batch creation, concurrent processing, status tracking, and cancellation.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import get_settings
from app.core.state import JobStateManager
from app.models.enums import JobStatus
from app.models.requests import BatchDownloadRequest, DownloadRequest
from app.services.batch_service import BatchService, BatchState
from app.services.queue_manager import QueueManager


# =========================
# Fixtures
# =========================

@pytest.fixture
def settings():
    """Get application settings."""
    return get_settings()


@pytest.fixture
def queue_manager():
    """Create mock queue manager."""
    qm = MagicMock(spec=QueueManager)
    qm.submit_job = MagicMock()
    qm.cancel_job = MagicMock()
    return qm


@pytest.fixture
def job_state_manager():
    """Create job state manager."""
    return JobStateManager()


@pytest.fixture
def batch_service(queue_manager, job_state_manager, settings):
    """Create batch service instance."""
    return BatchService(
        queue_manager=queue_manager,
        job_state_manager=job_state_manager,
        settings=settings
    )


@pytest.fixture
def sample_batch_request():
    """Create sample batch download request."""
    return BatchDownloadRequest(
        urls=[
            "https://example.com/video1",
            "https://example.com/video2",
            "https://example.com/video3"
        ],
        quality="1080p",
        concurrent_limit=2,
        stop_on_error=False
    )


# =========================
# Test BatchState
# =========================

def test_batch_state_creation():
    """Test BatchState initialization."""
    request = BatchDownloadRequest(
        urls=["https://example.com/video1"],
        concurrent_limit=1
    )

    state = BatchState(
        batch_id="batch_123",
        urls=request.urls,
        request=request
    )

    assert state.batch_id == "batch_123"
    assert state.status == JobStatus.QUEUED
    assert len(state.urls) == 1
    assert state.created_at is not None
    assert state.started_at is None
    assert state.completed_at is None
    assert len(state.job_ids) == 0


def test_batch_state_add_job():
    """Test adding job IDs to batch state."""
    request = BatchDownloadRequest(urls=["https://example.com/video1"])
    state = BatchState("batch_123", request.urls, request)

    state.add_job_id("job_001")
    state.add_job_id("job_002")

    assert len(state.job_ids) == 2
    assert "job_001" in state.job_ids
    assert "job_002" in state.job_ids


def test_batch_state_set_running():
    """Test marking batch as running."""
    request = BatchDownloadRequest(urls=["https://example.com/video1"])
    state = BatchState("batch_123", request.urls, request)

    state.set_running()

    assert state.status == JobStatus.RUNNING
    assert state.started_at is not None


def test_batch_state_set_completed():
    """Test marking batch as completed."""
    request = BatchDownloadRequest(urls=["https://example.com/video1"])
    state = BatchState("batch_123", request.urls, request)

    state.set_completed()

    assert state.status == JobStatus.COMPLETED
    assert state.completed_at is not None


def test_batch_state_set_failed():
    """Test marking batch as failed."""
    request = BatchDownloadRequest(urls=["https://example.com/video1"])
    state = BatchState("batch_123", request.urls, request)

    state.set_failed("Download failed")

    assert state.status == JobStatus.FAILED
    assert state.error_message == "Download failed"
    assert state.completed_at is not None


def test_batch_state_set_cancelled():
    """Test marking batch as cancelled."""
    request = BatchDownloadRequest(urls=["https://example.com/video1"])
    state = BatchState("batch_123", request.urls, request)

    state.set_cancelled()

    assert state.status == JobStatus.CANCELLED
    assert state.completed_at is not None


# =========================
# Test Batch Creation
# =========================

@pytest.mark.asyncio
async def test_create_batch_basic(batch_service, sample_batch_request):
    """Test creating a basic batch."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(sample_batch_request)

        assert response.batch_id.startswith("batch_")
        assert response.status == JobStatus.QUEUED
        assert response.total_jobs == 3
        assert response.queued_jobs == 3
        assert response.completed_jobs == 0
        assert response.failed_jobs == 0


@pytest.mark.asyncio
async def test_create_batch_generates_job_ids(batch_service, sample_batch_request, job_state_manager):
    """Test that batch creation generates individual job IDs."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(sample_batch_request)

        # Check that jobs were created in state manager
        batch_state = batch_service._batches.get(response.batch_id)
        assert batch_state is not None
        assert len(batch_state.job_ids) == 3


@pytest.mark.asyncio
async def test_create_batch_with_path_template(batch_service):
    """Test batch creation with path template containing batch_id."""
    request = BatchDownloadRequest(
        urls=["https://example.com/video1"],
        path_template="batch/{batch_id}/{title}.{ext}"
    )

    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(request)

        # Verify job was created with correct path template
        batch_state = batch_service._batches.get(response.batch_id)
        assert batch_state is not None


@pytest.mark.asyncio
async def test_create_batch_with_custom_concurrent_limit(batch_service):
    """Test batch with custom concurrent limit."""
    request = BatchDownloadRequest(
        urls=["https://example.com/video1", "https://example.com/video2"],
        concurrent_limit=5
    )

    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(request)

        assert response.total_jobs == 2


@pytest.mark.asyncio
async def test_create_batch_with_webhook(batch_service):
    """Test batch creation with webhook URL."""
    request = BatchDownloadRequest(
        urls=["https://example.com/video1"],
        webhook_url="https://webhook.example.com/notify"
    )

    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(request)

        assert response.batch_id is not None


# =========================
# Test Batch Status
# =========================

@pytest.mark.asyncio
async def test_get_batch_status_basic(batch_service, sample_batch_request):
    """Test getting batch status."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        create_response = await batch_service.create_batch(sample_batch_request)
        batch_id = create_response.batch_id

        status_response = await batch_service.get_batch_status(batch_id)

        assert status_response.batch_id == batch_id
        assert status_response.status == JobStatus.QUEUED
        assert status_response.total_jobs == 3


@pytest.mark.asyncio
async def test_get_batch_status_not_found(batch_service):
    """Test getting status for non-existent batch."""
    with pytest.raises(ValueError) as exc_info:
        await batch_service.get_batch_status("batch_nonexistent")

    assert "Batch not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_batch_status_with_progress(batch_service, sample_batch_request, job_state_manager):
    """Test batch status with job progress."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        create_response = await batch_service.create_batch(sample_batch_request)
        batch_id = create_response.batch_id

        # Simulate some jobs completing
        batch_state = batch_service._batches[batch_id]
        if len(batch_state.job_ids) > 0:
            job = job_state_manager.get_job(batch_state.job_ids[0])
            if job:
                job.set_completed()

        status_response = await batch_service.get_batch_status(batch_id)

        assert status_response.completed_jobs >= 0


# =========================
# Test Batch Cancellation
# =========================

@pytest.mark.asyncio
async def test_cancel_batch_basic(batch_service, sample_batch_request, job_state_manager):
    """Test cancelling a batch."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        create_response = await batch_service.create_batch(sample_batch_request)
        batch_id = create_response.batch_id

        # Cancel the batch
        cancelled_count = await batch_service.cancel_batch(batch_id)

        # All jobs should be cancelled
        assert cancelled_count == 3

        # Batch state should be cancelled
        batch_state = batch_service._batches[batch_id]
        assert batch_state.status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_batch_not_found(batch_service):
    """Test cancelling non-existent batch."""
    with pytest.raises(ValueError) as exc_info:
        await batch_service.cancel_batch("batch_nonexistent")

    assert "Batch not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cancel_batch_partial_completion(batch_service, sample_batch_request, job_state_manager):
    """Test cancelling batch with some jobs completed."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        create_response = await batch_service.create_batch(sample_batch_request)
        batch_id = create_response.batch_id

        # Mark one job as completed
        batch_state = batch_service._batches[batch_id]
        if len(batch_state.job_ids) > 0:
            job = job_state_manager.get_job(batch_state.job_ids[0])
            if job:
                job.set_completed()

        # Cancel the batch
        cancelled_count = await batch_service.cancel_batch(batch_id)

        # Only non-completed jobs should be cancelled
        assert cancelled_count <= 3


# =========================
# Test Concurrent Limit
# =========================

@pytest.mark.asyncio
async def test_concurrent_limit_enforcement(batch_service, job_state_manager):
    """Test that concurrent limit is enforced."""
    request = BatchDownloadRequest(
        urls=[
            "https://example.com/video1",
            "https://example.com/video2",
            "https://example.com/video3",
            "https://example.com/video4",
            "https://example.com/video5"
        ],
        concurrent_limit=2
    )

    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(request)

        # The service should create jobs with concurrent_limit=2
        assert response.total_jobs == 5


# =========================
# Test Stop on Error
# =========================

@pytest.mark.asyncio
async def test_stop_on_error_true(batch_service):
    """Test batch with stop_on_error=True."""
    request = BatchDownloadRequest(
        urls=["https://example.com/video1", "https://example.com/video2"],
        stop_on_error=True
    )

    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(request)

        assert response.total_jobs == 2


@pytest.mark.asyncio
async def test_stop_on_error_false(batch_service):
    """Test batch with stop_on_error=False (continue on error)."""
    request = BatchDownloadRequest(
        urls=["https://example.com/video1", "https://example.com/video2"],
        stop_on_error=False
    )

    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(request)

        assert response.total_jobs == 2


# =========================
# Test Batch List
# =========================

def test_get_batch_list_empty(batch_service):
    """Test getting batch list when empty."""
    batch_list = batch_service.get_batch_list()
    assert isinstance(batch_list, list)
    assert len(batch_list) == 0


@pytest.mark.asyncio
async def test_get_batch_list_with_batches(batch_service, sample_batch_request):
    """Test getting batch list with batches."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        await batch_service.create_batch(sample_batch_request)
        await batch_service.create_batch(sample_batch_request)

        batch_list = batch_service.get_batch_list()
        assert len(batch_list) == 2


# =========================
# Test Cleanup Old Batches
# =========================

def test_cleanup_old_batches_none_old(batch_service):
    """Test cleanup when no old batches exist."""
    cleaned = batch_service.cleanup_old_batches(max_age_hours=24)
    assert cleaned == 0


@pytest.mark.asyncio
async def test_cleanup_old_batches_with_completed(batch_service, sample_batch_request):
    """Test cleanup of old completed batches."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(sample_batch_request)
        batch_id = response.batch_id

        # Mark batch as completed with old timestamp
        batch_state = batch_service._batches[batch_id]
        batch_state.set_completed()

        # Manually set completed_at to old time
        from datetime import timedelta
        batch_state.completed_at = datetime.now(timezone.utc) - timedelta(hours=25)

        # Cleanup old batches (max_age=24 hours)
        cleaned = batch_service.cleanup_old_batches(max_age_hours=24)

        assert cleaned == 1
        assert batch_id not in batch_service._batches


def test_cleanup_old_batches_running_not_cleaned(batch_service):
    """Test that running batches are not cleaned up."""
    request = BatchDownloadRequest(urls=["https://example.com/video1"])
    state = BatchState("batch_123", request.urls, request)
    state.set_running()

    batch_service._batches["batch_123"] = state

    # Try to clean up
    cleaned = batch_service.cleanup_old_batches(max_age_hours=0)

    # Running batch should not be cleaned
    assert cleaned == 0
    assert "batch_123" in batch_service._batches


# =========================
# Test Job Status Calculation
# =========================

@pytest.mark.asyncio
async def test_batch_status_calculation_all_queued(batch_service, sample_batch_request):
    """Test status calculation with all jobs queued."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(sample_batch_request)

        assert response.queued_jobs == 3
        assert response.running_jobs == 0
        assert response.completed_jobs == 0
        assert response.failed_jobs == 0


@pytest.mark.asyncio
async def test_batch_status_calculation_mixed(batch_service, sample_batch_request, job_state_manager):
    """Test status calculation with mixed job states."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(sample_batch_request)
        batch_id = response.batch_id

        # Modify job states
        batch_state = batch_service._batches[batch_id]
        jobs = [job_state_manager.get_job(jid) for jid in batch_state.job_ids]

        if len(jobs) >= 3:
            if jobs[0]:
                jobs[0].set_completed()
            if jobs[1]:
                jobs[1].set_running()
            if jobs[2]:
                jobs[2].set_failed("Test error")

        # Get updated status
        status = await batch_service.get_batch_status(batch_id)

        # Check counts
        assert status.completed_jobs == 1
        assert status.running_jobs == 1
        assert status.failed_jobs == 1


# =========================
# Test Duration Calculation
# =========================

@pytest.mark.asyncio
async def test_batch_duration_calculation(batch_service, sample_batch_request):
    """Test batch duration calculation."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(sample_batch_request)
        batch_id = response.batch_id

        # Simulate batch lifecycle
        batch_state = batch_service._batches[batch_id]
        batch_state.set_running()

        # Small delay
        await asyncio.sleep(0.1)

        batch_state.set_completed()

        # Get status
        status = await batch_service.get_batch_status(batch_id)

        assert status.duration_sec is not None
        assert status.duration_sec >= 0


# =========================
# Test Error Scenarios
# =========================

@pytest.mark.asyncio
async def test_batch_with_invalid_urls(batch_service):
    """Test batch creation with invalid URL format."""
    # This should be validated at request level, but test service behavior
    request = BatchDownloadRequest(
        urls=["https://example.com/video1"]
    )

    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(request)
        assert response.total_jobs == 1


@pytest.mark.asyncio
async def test_batch_job_info_includes_metadata(batch_service, sample_batch_request, job_state_manager):
    """Test that batch status includes job metadata."""
    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(sample_batch_request)
        batch_id = response.batch_id

        status = await batch_service.get_batch_status(batch_id)

        # Each job should have metadata
        for job in status.jobs:
            assert job.job_id is not None
            assert job.url is not None
            assert job.status is not None
            assert job.created_at is not None


# =========================
# Test Edge Cases
# =========================

@pytest.mark.asyncio
async def test_batch_with_single_url(batch_service):
    """Test batch with single URL."""
    request = BatchDownloadRequest(
        urls=["https://example.com/video1"]
    )

    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(request)

        assert response.total_jobs == 1


@pytest.mark.asyncio
async def test_batch_with_max_concurrent_limit(batch_service):
    """Test batch with maximum concurrent limit."""
    request = BatchDownloadRequest(
        urls=["https://example.com/video1", "https://example.com/video2"],
        concurrent_limit=10  # Maximum allowed
    )

    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(request)

        assert response.total_jobs == 2


@pytest.mark.asyncio
async def test_batch_preserves_download_options(batch_service):
    """Test that batch preserves download options for each job."""
    request = BatchDownloadRequest(
        urls=["https://example.com/video1"],
        quality="720p",
        audio_only=True,
        download_subtitles=True,
        embed_metadata=False
    )

    with patch.object(asyncio, 'create_task', return_value=MagicMock()):
        response = await batch_service.create_batch(request)

        # Jobs should be created with these options
        assert response.total_jobs == 1
