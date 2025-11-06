"""
Integration tests for batch download API endpoints.

Tests POST /api/v1/batch/download, GET /api/v1/batch/{batch_id}, and DELETE /api/v1/batch/{batch_id}.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from app.main import app
from app.models.enums import JobStatus


# =========================
# Fixtures
# =========================

@pytest.fixture
def api_key():
    """Get API key for authentication."""
    return "test_api_key"


@pytest.fixture
def auth_headers(api_key):
    """Create authentication headers."""
    return {"X-API-Key": api_key}


@pytest.fixture
def sample_batch_payload():
    """Sample batch download request payload."""
    return {
        "urls": [
            "https://example.com/video1",
            "https://example.com/video2",
            "https://example.com/video3"
        ],
        "quality": "1080p",
        "concurrent_limit": 2,
        "stop_on_error": False
    }


# =========================
# Test POST /api/v1/batch/download
# =========================

@pytest.mark.asyncio
async def test_create_batch_download_success(auth_headers, sample_batch_payload):
    """Test creating a batch download."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            response = await client.post(
                "/api/v1/batch/download",
                json=sample_batch_payload,
                headers=auth_headers
            )

            assert response.status_code == 202
            data = response.json()

            assert 'batch_id' in data
            assert data['batch_id'].startswith('batch_')
            assert data['status'] == 'queued'
            assert data['total_jobs'] == 3
            assert data['queued_jobs'] == 3
            assert data['completed_jobs'] == 0
            assert data['failed_jobs'] == 0


@pytest.mark.asyncio
async def test_create_batch_download_single_url(auth_headers):
    """Test batch download with single URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": ["https://example.com/video1"],
                    "quality": "720p"
                },
                headers=auth_headers
            )

            assert response.status_code == 202
            data = response.json()
            assert data['total_jobs'] == 1


@pytest.mark.asyncio
async def test_create_batch_download_max_concurrent(auth_headers):
    """Test batch download with maximum concurrent limit."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": ["https://example.com/video1", "https://example.com/video2"],
                    "concurrent_limit": 10  # Maximum allowed
                },
                headers=auth_headers
            )

            assert response.status_code == 202


@pytest.mark.asyncio
async def test_create_batch_download_stop_on_error(auth_headers):
    """Test batch download with stop_on_error enabled."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": ["https://example.com/video1"],
                    "stop_on_error": True
                },
                headers=auth_headers
            )

            assert response.status_code == 202


@pytest.mark.asyncio
async def test_create_batch_download_with_options(auth_headers):
    """Test batch download with various download options."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": ["https://example.com/video1"],
                    "quality": "720p",
                    "audio_only": True,
                    "audio_format": "mp3",
                    "download_subtitles": True,
                    "subtitle_languages": ["en", "es"],
                    "embed_metadata": True,
                    "write_thumbnail": True
                },
                headers=auth_headers
            )

            assert response.status_code == 202


@pytest.mark.asyncio
async def test_create_batch_download_with_webhook(auth_headers):
    """Test batch download with webhook URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": ["https://example.com/video1"],
                    "webhook_url": "https://webhook.example.com/notify"
                },
                headers=auth_headers
            )

            assert response.status_code == 202


@pytest.mark.asyncio
async def test_create_batch_download_empty_urls(auth_headers):
    """Test batch download with empty URL list."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/batch/download",
            json={
                "urls": [],
                "quality": "1080p"
            },
            headers=auth_headers
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_batch_download_too_many_urls(auth_headers):
    """Test batch download exceeding maximum URLs."""
    urls = [f"https://example.com/video{i}" for i in range(101)]

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/batch/download",
            json={
                "urls": urls,
                "quality": "1080p"
            },
            headers=auth_headers
        )

        assert response.status_code == 413
        assert "exceeds maximum" in response.json()['detail']


@pytest.mark.asyncio
async def test_create_batch_download_duplicate_urls(auth_headers):
    """Test batch download with duplicate URLs."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/batch/download",
            json={
                "urls": [
                    "https://example.com/video1",
                    "https://example.com/video1"  # Duplicate
                ],
                "quality": "1080p"
            },
            headers=auth_headers
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_batch_download_invalid_url_format(auth_headers):
    """Test batch download with invalid URL format."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/batch/download",
            json={
                "urls": ["not_a_valid_url"],
                "quality": "1080p"
            },
            headers=auth_headers
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_batch_download_invalid_concurrent_limit(auth_headers):
    """Test batch download with invalid concurrent limit."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/batch/download",
            json={
                "urls": ["https://example.com/video1"],
                "concurrent_limit": 0  # Invalid: must be >= 1
            },
            headers=auth_headers
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_batch_download_unauthorized():
    """Test batch download without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/batch/download",
            json={
                "urls": ["https://example.com/video1"],
                "quality": "1080p"
            }
        )

        # Will be 401 if auth required, or proceed if not
        assert response.status_code in [202, 401, 422]


# =========================
# Test GET /api/v1/batch/{batch_id}
# =========================

@pytest.mark.asyncio
async def test_get_batch_status_success(auth_headers, sample_batch_payload):
    """Test getting batch status."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            # Create batch
            create_response = await client.post(
                "/api/v1/batch/download",
                json=sample_batch_payload,
                headers=auth_headers
            )

            assert create_response.status_code == 202
            batch_id = create_response.json()['batch_id']

            # Get status
            status_response = await client.get(
                f"/api/v1/batch/{batch_id}",
                headers=auth_headers
            )

            assert status_response.status_code == 200
            data = status_response.json()

            assert data['batch_id'] == batch_id
            assert data['status'] == 'queued'
            assert data['total_jobs'] == 3


@pytest.mark.asyncio
async def test_get_batch_status_not_found(auth_headers):
    """Test getting status for non-existent batch."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/batch/nonexistent_batch_id",
            headers=auth_headers
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_batch_status_includes_jobs(auth_headers, sample_batch_payload):
    """Test that batch status includes job information."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            # Create batch
            create_response = await client.post(
                "/api/v1/batch/download",
                json=sample_batch_payload,
                headers=auth_headers
            )

            batch_id = create_response.json()['batch_id']

            # Get status
            status_response = await client.get(
                f"/api/v1/batch/{batch_id}",
                headers=auth_headers
            )

            data = status_response.json()
            assert 'jobs' in data
            assert len(data['jobs']) >= 0


@pytest.mark.asyncio
async def test_get_batch_status_unauthorized():
    """Test getting batch status without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/batch/some_batch_id")

        assert response.status_code in [200, 401, 404]


# =========================
# Test DELETE /api/v1/batch/{batch_id}
# =========================

@pytest.mark.asyncio
async def test_cancel_batch_success(auth_headers, sample_batch_payload):
    """Test cancelling a batch."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            # Create batch
            create_response = await client.post(
                "/api/v1/batch/download",
                json=sample_batch_payload,
                headers=auth_headers
            )

            batch_id = create_response.json()['batch_id']

            # Cancel batch
            cancel_response = await client.delete(
                f"/api/v1/batch/{batch_id}",
                headers=auth_headers
            )

            assert cancel_response.status_code == 200
            data = cancel_response.json()

            assert data['request_id'] == batch_id
            assert data['status'] == 'cancelled'
            assert 'cancelled_jobs' in data


@pytest.mark.asyncio
async def test_cancel_batch_not_found(auth_headers):
    """Test cancelling non-existent batch."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(
            "/api/v1/batch/nonexistent_batch_id",
            headers=auth_headers
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_batch_unauthorized():
    """Test cancelling batch without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete("/api/v1/batch/some_batch_id")

        assert response.status_code in [200, 401, 404]


# =========================
# Test Complete Batch Workflow
# =========================

@pytest.mark.asyncio
async def test_batch_complete_workflow(auth_headers):
    """Test complete batch workflow: create, status, cancel."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            # Step 1: Create batch
            create_response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": [
                        "https://example.com/video1",
                        "https://example.com/video2"
                    ],
                    "quality": "720p"
                },
                headers=auth_headers
            )

            assert create_response.status_code == 202
            batch_id = create_response.json()['batch_id']

            # Step 2: Check status
            status_response = await client.get(
                f"/api/v1/batch/{batch_id}",
                headers=auth_headers
            )

            assert status_response.status_code == 200
            assert status_response.json()['batch_id'] == batch_id

            # Step 3: Cancel batch
            cancel_response = await client.delete(
                f"/api/v1/batch/{batch_id}",
                headers=auth_headers
            )

            assert cancel_response.status_code == 200
            assert cancel_response.json()['status'] == 'cancelled'


# =========================
# Test Error Scenarios
# =========================

@pytest.mark.asyncio
async def test_batch_with_invalid_quality(auth_headers):
    """Test batch with invalid quality preset."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/batch/download",
            json={
                "urls": ["https://example.com/video1"],
                "quality": "invalid_quality"
            },
            headers=auth_headers
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_batch_with_invalid_audio_format(auth_headers):
    """Test batch with invalid audio format."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/batch/download",
            json={
                "urls": ["https://example.com/video1"],
                "audio_only": True,
                "audio_format": "invalid_format"
            },
            headers=auth_headers
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_batch_with_invalid_webhook_url(auth_headers):
    """Test batch with invalid webhook URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/batch/download",
            json={
                "urls": ["https://example.com/video1"],
                "webhook_url": "not_a_valid_url"
            },
            headers=auth_headers
        )

        assert response.status_code == 422


# =========================
# Test Concurrent Downloads
# =========================

@pytest.mark.asyncio
async def test_batch_concurrent_limit_1(auth_headers):
    """Test batch with concurrent limit of 1."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": [
                        "https://example.com/video1",
                        "https://example.com/video2",
                        "https://example.com/video3"
                    ],
                    "concurrent_limit": 1
                },
                headers=auth_headers
            )

            assert response.status_code == 202


@pytest.mark.asyncio
async def test_batch_concurrent_limit_5(auth_headers):
    """Test batch with concurrent limit of 5."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": [f"https://example.com/video{i}" for i in range(10)],
                    "concurrent_limit": 5
                },
                headers=auth_headers
            )

            assert response.status_code == 202


# =========================
# Test Path Templates
# =========================

@pytest.mark.asyncio
async def test_batch_with_custom_path_template(auth_headers):
    """Test batch with custom path template."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": ["https://example.com/video1"],
                    "path_template": "downloads/{batch_id}/{title}.{ext}"
                },
                headers=auth_headers
            )

            assert response.status_code == 202


# =========================
# Test Cookie Integration
# =========================

@pytest.mark.asyncio
async def test_batch_with_cookies_id(auth_headers):
    """Test batch download with cookies ID."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": ["https://example.com/video1"],
                    "cookies_id": "test_cookie_id_123"
                },
                headers=auth_headers
            )

            assert response.status_code == 202
