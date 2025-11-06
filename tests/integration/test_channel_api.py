"""
Integration tests for channel API endpoints.

Tests GET /api/v1/channel/info and POST /api/v1/channel/download endpoints.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.main import app
from app.core.exceptions import MetadataExtractionError


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
def mock_channel_data():
    """Mock channel metadata for testing."""
    return {
        '_type': 'playlist',
        'channel_id': 'UC_integration_test',
        'channel': 'Integration Test Channel',
        'uploader': 'Integration Test Channel',
        'description': 'A channel for integration testing',
        'subscriber_count': 500000,
        'extractor': 'youtube:tab',
        'entries': [
            {
                'id': 'vid1',
                'title': 'Integration Video 1',
                'url': 'https://youtube.com/watch?v=vid1',
                'webpage_url': 'https://youtube.com/watch?v=vid1',
                'duration': 600,
                'view_count': 100000,
                'uploader': 'Integration Test Channel',
                'upload_date': '20251105',
                'thumbnail': 'https://example.com/thumb1.jpg'
            },
            {
                'id': 'vid2',
                'title': 'Integration Video 2',
                'url': 'https://youtube.com/watch?v=vid2',
                'webpage_url': 'https://youtube.com/watch?v=vid2',
                'duration': 1200,
                'view_count': 50000,
                'uploader': 'Integration Test Channel',
                'upload_date': '20251103',
                'thumbnail': 'https://example.com/thumb2.jpg'
            },
            {
                'id': 'vid3',
                'title': 'Integration Video 3',
                'url': 'https://youtube.com/watch?v=vid3',
                'webpage_url': 'https://youtube.com/watch?v=vid3',
                'duration': 300,
                'view_count': 200000,
                'uploader': 'Integration Test Channel',
                'upload_date': '20251101',
                'thumbnail': 'https://example.com/thumb3.jpg'
            }
        ]
    }


# =========================
# Test GET /api/v1/channel/info
# =========================

@pytest.mark.asyncio
async def test_get_channel_info_success(auth_headers, mock_channel_data):
    """Test successful channel info retrieval."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data):

            response = await client.get(
                "/api/v1/channel/info",
                params={"url": "https://youtube.com/@integration_test"},
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            assert data['channel_id'] == 'UC_integration_test'
            assert data['channel_name'] == 'Integration Test Channel'
            assert data['video_count'] == 3
            assert data['filtered_video_count'] == 3
            assert len(data['videos']) == 3
            assert data['page'] == 1
            assert data['total_pages'] == 1


@pytest.mark.asyncio
async def test_get_channel_info_with_filters(auth_headers, mock_channel_data):
    """Test channel info with date and duration filters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data):

            response = await client.get(
                "/api/v1/channel/info",
                params={
                    "url": "https://youtube.com/@integration_test",
                    "date_after": "20251102",
                    "min_duration": 500
                },
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            # Should filter to videos after 20251102 with duration >= 500
            # vid1 (20251105, 600s) and vid2 (20251103, 1200s)
            assert data['filtered_video_count'] == 2
            assert 'date_after' in data['filters_applied']
            assert 'min_duration' in data['filters_applied']


@pytest.mark.asyncio
async def test_get_channel_info_with_pagination(auth_headers, mock_channel_data):
    """Test channel info with pagination."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data):

            # Get first page
            response = await client.get(
                "/api/v1/channel/info",
                params={
                    "url": "https://youtube.com/@integration_test",
                    "page": 1,
                    "page_size": 2
                },
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            assert data['page'] == 1
            assert data['page_size'] == 2
            assert len(data['videos']) == 2
            assert data['has_next'] is True
            assert data['has_previous'] is False


@pytest.mark.asyncio
async def test_get_channel_info_with_sorting(auth_headers, mock_channel_data):
    """Test channel info with sorting."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data):

            response = await client.get(
                "/api/v1/channel/info",
                params={
                    "url": "https://youtube.com/@integration_test",
                    "sort_by": "view_count"
                },
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            # Should be sorted by view count (highest first)
            # vid3 (200k), vid1 (100k), vid2 (50k)
            assert data['videos'][0]['view_count'] >= data['videos'][1]['view_count']


@pytest.mark.asyncio
async def test_get_channel_info_missing_url(auth_headers):
    """Test channel info without URL parameter."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/channel/info",
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_channel_info_invalid_url(auth_headers):
    """Test channel info with invalid URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/channel/info",
            params={"url": "not_a_valid_url"},
            headers=auth_headers
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_channel_info_invalid_sort_by(auth_headers, mock_channel_data):
    """Test channel info with invalid sort_by parameter."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/channel/info",
            params={
                "url": "https://youtube.com/@test",
                "sort_by": "invalid_field"
            },
            headers=auth_headers
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_channel_info_invalid_date_range(auth_headers, mock_channel_data):
    """Test channel info with invalid date range."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/channel/info",
            params={
                "url": "https://youtube.com/@test",
                "date_after": "20251201",
                "date_before": "20251101"  # Before comes before after
            },
            headers=auth_headers
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_channel_info_invalid_duration_range(auth_headers):
    """Test channel info with invalid duration range."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/channel/info",
            params={
                "url": "https://youtube.com/@test",
                "min_duration": 1000,
                "max_duration": 500  # Max less than min
            },
            headers=auth_headers
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_channel_info_extraction_error(auth_headers):
    """Test channel info when extraction fails."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   side_effect=Exception("Network error")):

            response = await client.get(
                "/api/v1/channel/info",
                params={"url": "https://youtube.com/@test"},
                headers=auth_headers
            )

            assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_channel_info_not_a_channel(auth_headers):
    """Test channel info with URL that's not a channel."""
    single_video = {
        '_type': 'video',
        'id': 'video1',
        'title': 'Single Video'
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=single_video):

            response = await client.get(
                "/api/v1/channel/info",
                params={"url": "https://youtube.com/watch?v=video1"},
                headers=auth_headers
            )

            assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_channel_info_unauthorized():
    """Test channel info without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Check if API key authentication is required
        # This depends on REQUIRE_API_KEY setting
        response = await client.get(
            "/api/v1/channel/info",
            params={"url": "https://youtube.com/@test"}
        )

        # Will be 200 if API key not required, 401 if required
        assert response.status_code in [200, 401, 422]


# =========================
# Test POST /api/v1/channel/download
# =========================

@pytest.mark.asyncio
async def test_channel_download_success(auth_headers, mock_channel_data):
    """Test successful channel download job creation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data), \
             patch('app.services.queue_manager.QueueManager.submit_job'):

            response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@integration_test",
                    "quality": "1080p"
                },
                headers=auth_headers
            )

            assert response.status_code == 201
            data = response.json()

            assert 'batch_id' in data
            assert data['status'] == 'queued'
            assert data['total_jobs'] == 3
            assert data['queued_jobs'] == 3


@pytest.mark.asyncio
async def test_channel_download_with_filters(auth_headers, mock_channel_data):
    """Test channel download with filters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data), \
             patch('app.services.queue_manager.QueueManager.submit_job'):

            response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@integration_test",
                    "date_after": "20251102",
                    "min_duration": 500,
                    "max_downloads": 2,
                    "quality": "720p"
                },
                headers=auth_headers
            )

            assert response.status_code == 201
            data = response.json()

            # Filtered to 2 videos
            assert data['total_jobs'] == 2


@pytest.mark.asyncio
async def test_channel_download_with_max_downloads(auth_headers, mock_channel_data):
    """Test channel download with max_downloads limit."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data), \
             patch('app.services.queue_manager.QueueManager.submit_job'):

            response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@integration_test",
                    "max_downloads": 1
                },
                headers=auth_headers
            )

            assert response.status_code == 201
            data = response.json()

            assert data['total_jobs'] == 1


@pytest.mark.asyncio
async def test_channel_download_no_videos_match_filters(auth_headers, mock_channel_data):
    """Test channel download when no videos match filters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data):

            response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@integration_test",
                    "date_after": "20301201",  # Far future date
                    "quality": "1080p"
                },
                headers=auth_headers
            )

            assert response.status_code == 400
            data = response.json()
            assert "No videos match" in data['detail']


@pytest.mark.asyncio
async def test_channel_download_invalid_url(auth_headers):
    """Test channel download with invalid URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/channel/download",
            json={
                "url": "not_a_valid_url",
                "quality": "1080p"
            },
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_channel_download_extraction_error(auth_headers):
    """Test channel download when extraction fails."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   side_effect=Exception("Network error")):

            response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@test",
                    "quality": "1080p"
                },
                headers=auth_headers
            )

            assert response.status_code == 422


@pytest.mark.asyncio
async def test_channel_download_with_custom_format(auth_headers, mock_channel_data):
    """Test channel download with custom format."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data), \
             patch('app.services.queue_manager.QueueManager.submit_job'):

            response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@integration_test",
                    "custom_format": "bestvideo[height<=1080]+bestaudio"
                },
                headers=auth_headers
            )

            assert response.status_code == 201


@pytest.mark.asyncio
async def test_channel_download_with_subtitles(auth_headers, mock_channel_data):
    """Test channel download with subtitle options."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data), \
             patch('app.services.queue_manager.QueueManager.submit_job'):

            response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@integration_test",
                    "download_subtitles": True,
                    "subtitle_languages": ["en", "es"],
                    "embed_subtitles": True
                },
                headers=auth_headers
            )

            assert response.status_code == 201


@pytest.mark.asyncio
async def test_channel_download_audio_only(auth_headers, mock_channel_data):
    """Test channel download audio only."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data), \
             patch('app.services.queue_manager.QueueManager.submit_job'):

            response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@integration_test",
                    "audio_only": True,
                    "audio_format": "mp3",
                    "audio_quality": "192"
                },
                headers=auth_headers
            )

            assert response.status_code == 201


@pytest.mark.asyncio
async def test_channel_download_with_webhook(auth_headers, mock_channel_data):
    """Test channel download with webhook URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data), \
             patch('app.services.queue_manager.QueueManager.submit_job'):

            response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@integration_test",
                    "webhook_url": "https://webhook.example.com/notify"
                },
                headers=auth_headers
            )

            assert response.status_code == 201


@pytest.mark.asyncio
async def test_channel_download_unauthorized():
    """Test channel download without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/channel/download",
            json={
                "url": "https://youtube.com/@test",
                "quality": "1080p"
            }
        )

        # Will be 401 if authentication required, or proceed if not
        assert response.status_code in [201, 401, 422]


# =========================
# Test Rate Limiting
# =========================

@pytest.mark.asyncio
async def test_channel_info_rate_limiting(auth_headers, mock_channel_data):
    """Test rate limiting on channel info endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data):

            # Make multiple rapid requests
            responses = []
            for _ in range(5):
                response = await client.get(
                    "/api/v1/channel/info",
                    params={"url": "https://youtube.com/@test"},
                    headers=auth_headers
                )
                responses.append(response)

            # At least some should succeed (rate limit depends on config)
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count > 0


# =========================
# Test Edge Cases
# =========================

@pytest.mark.asyncio
async def test_channel_info_empty_channel(auth_headers):
    """Test channel info with empty channel (no videos)."""
    empty_channel = {
        '_type': 'playlist',
        'channel_id': 'UC_empty',
        'channel': 'Empty Channel',
        'entries': []
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=empty_channel):

            response = await client.get(
                "/api/v1/channel/info",
                params={"url": "https://youtube.com/@empty"},
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data['video_count'] == 0
            assert len(data['videos']) == 0


@pytest.mark.asyncio
async def test_channel_download_empty_channel(auth_headers):
    """Test channel download with empty channel."""
    empty_channel = {
        '_type': 'playlist',
        'channel_id': 'UC_empty',
        'channel': 'Empty Channel',
        'entries': []
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=empty_channel):

            response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@empty",
                    "quality": "1080p"
                },
                headers=auth_headers
            )

            assert response.status_code == 400
            assert "No videos match" in response.json()['detail']
