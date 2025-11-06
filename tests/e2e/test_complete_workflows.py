"""
End-to-end tests for complete download workflows.

Tests real-world scenarios combining multiple features.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from app.main import app


# =========================
# Fixtures
# =========================

@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    return {"X-API-Key": "test_api_key"}


@pytest.fixture
def mock_channel_data():
    """Mock channel data for testing."""
    return {
        '_type': 'playlist',
        'channel_id': 'UC_e2e_test',
        'channel': 'E2E Test Channel',
        'uploader': 'E2E Test Channel',
        'entries': [
            {
                'id': 'e2e_vid1',
                'title': 'E2E Video 1',
                'url': 'https://youtube.com/watch?v=e2e_vid1',
                'webpage_url': 'https://youtube.com/watch?v=e2e_vid1',
                'duration': 600,
                'view_count': 100000,
                'upload_date': '20251105'
            },
            {
                'id': 'e2e_vid2',
                'title': 'E2E Video 2',
                'url': 'https://youtube.com/watch?v=e2e_vid2',
                'webpage_url': 'https://youtube.com/watch?v=e2e_vid2',
                'duration': 1200,
                'view_count': 50000,
                'upload_date': '20251103'
            }
        ]
    }


@pytest.fixture
def valid_cookies():
    """Valid test cookies."""
    return """# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1735689600	CONSENT	YES+cb
.youtube.com	TRUE	/	FALSE	1735689600	VISITOR	abc123
"""


# =========================
# E2E: Channel Download Workflow
# =========================

@pytest.mark.asyncio
async def test_e2e_channel_download_complete_workflow(auth_headers, mock_channel_data):
    """Test complete channel download workflow."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data), \
             patch('app.services.queue_manager.QueueManager.submit_job'):

            # Step 1: Get channel info first (browse before downloading)
            info_response = await client.get(
                "/api/v1/channel/info",
                params={
                    "url": "https://youtube.com/@e2e_test",
                    "date_after": "20251101",
                    "min_duration": 500
                },
                headers=auth_headers
            )

            assert info_response.status_code == 200
            channel_info = info_response.json()

            # Verify we can see filtered videos
            assert channel_info['filtered_video_count'] >= 1

            # Step 2: Create channel download job with same filters
            download_response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@e2e_test",
                    "date_after": "20251101",
                    "min_duration": 500,
                    "quality": "1080p",
                    "download_subtitles": True
                },
                headers=auth_headers
            )

            assert download_response.status_code == 201
            batch_data = download_response.json()

            # Verify batch was created
            assert 'batch_id' in batch_data
            assert batch_data['total_jobs'] >= 1


# =========================
# E2E: Batch Download with Webhooks
# =========================

@pytest.mark.asyncio
async def test_e2e_batch_download_with_webhooks(auth_headers):
    """Test batch download with webhook notifications."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()), \
             patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_webhook:

            # Create batch with webhook
            batch_response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": [
                        "https://example.com/video1",
                        "https://example.com/video2"
                    ],
                    "quality": "720p",
                    "webhook_url": "https://webhook.example.com/notify"
                },
                headers=auth_headers
            )

            assert batch_response.status_code == 202
            batch_id = batch_response.json()['batch_id']

            # Monitor batch status
            status_response = await client.get(
                f"/api/v1/batch/{batch_id}",
                headers=auth_headers
            )

            assert status_response.status_code == 200


# =========================
# E2E: Download with Cookies
# =========================

@pytest.mark.asyncio
async def test_e2e_download_with_cookies(auth_headers, valid_cookies):
    """Test downloading private content with cookies."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Upload cookies
        cookies_response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies,
                "name": "private_video_cookies"
            },
            headers=auth_headers
        )

        assert cookies_response.status_code == 201
        cookie_id = cookies_response.json()['cookie_id']

        # Step 2: Use cookies in download
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.download',
                   new_callable=MagicMock):
            download_response = await client.post(
                "/api/v1/download",
                json={
                    "url": "https://example.com/private_video",
                    "cookies_id": cookie_id,
                    "quality": "1080p"
                },
                headers=auth_headers
            )

            # Should accept the download
            assert download_response.status_code in [200, 201, 202]

        # Step 3: Cleanup - delete cookies
        delete_response = await client.delete(
            f"/api/v1/cookies/{cookie_id}",
            headers=auth_headers
        )

        assert delete_response.status_code == 200


# =========================
# E2E: Mixed Playlist + Channel + Batch
# =========================

@pytest.mark.asyncio
async def test_e2e_mixed_download_types(auth_headers, mock_channel_data):
    """Test combining different download types."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock) as mock_extract, \
             patch('app.services.queue_manager.QueueManager.submit_job'), \
             patch('asyncio.create_task', return_value=MagicMock()):

            # Setup mocks
            mock_extract.return_value = mock_channel_data

            # 1. Single video download
            single_response = await client.post(
                "/api/v1/download",
                json={
                    "url": "https://example.com/video1",
                    "quality": "1080p"
                },
                headers=auth_headers
            )

            assert single_response.status_code in [200, 201, 202]

            # 2. Channel download
            channel_response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@test",
                    "max_downloads": 5,
                    "quality": "720p"
                },
                headers=auth_headers
            )

            assert channel_response.status_code == 201

            # 3. Batch download
            batch_response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": [
                        "https://example.com/batch1",
                        "https://example.com/batch2"
                    ],
                    "concurrent_limit": 2
                },
                headers=auth_headers
            )

            assert batch_response.status_code == 202


# =========================
# E2E: Browser Cookie Extraction + Channel Download
# =========================

@pytest.mark.asyncio
async def test_e2e_browser_cookies_with_channel_download(auth_headers, mock_channel_data, valid_cookies, tmp_path):
    """Test extracting browser cookies and using them for channel download."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.cookie_manager.yt_dlp.YoutubeDL') as mock_ydl, \
             patch('app.services.cookie_manager.tempfile.NamedTemporaryFile') as mock_temp, \
             patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=mock_channel_data), \
             patch('app.services.queue_manager.QueueManager.submit_job'):

            # Setup cookie extraction mock
            temp_file = tmp_path / "temp_cookies.txt"
            temp_file.write_text(valid_cookies)
            mock_temp.return_value.__enter__.return_value.name = str(temp_file)
            mock_ydl.return_value.__enter__.return_value.cookiejar = None

            # Step 1: Extract cookies from browser
            cookies_response = await client.post(
                "/api/v1/cookies",
                json={
                    "browser": "chrome",
                    "name": "chrome_for_channel"
                },
                headers=auth_headers
            )

            assert cookies_response.status_code == 201
            cookie_id = cookies_response.json()['cookie_id']

            # Step 2: Use cookies for channel download
            download_response = await client.post(
                "/api/v1/channel/download",
                json={
                    "url": "https://youtube.com/@members_only",
                    "cookies_id": cookie_id,
                    "quality": "1080p"
                },
                headers=auth_headers
            )

            assert download_response.status_code == 201


# =========================
# E2E: Error Recovery Workflow
# =========================

@pytest.mark.asyncio
async def test_e2e_error_recovery_workflow(auth_headers):
    """Test error recovery in batch downloads."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            # Create batch with stop_on_error=False (continue on errors)
            batch_response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": [
                        "https://example.com/video1",
                        "https://example.com/invalid",  # This might fail
                        "https://example.com/video3"
                    ],
                    "concurrent_limit": 1,
                    "stop_on_error": False  # Continue despite errors
                },
                headers=auth_headers
            )

            assert batch_response.status_code == 202
            batch_id = batch_response.json()['batch_id']

            # Check status
            status_response = await client.get(
                f"/api/v1/batch/{batch_id}",
                headers=auth_headers
            )

            assert status_response.status_code == 200


# =========================
# E2E: Rate Limiting Workflow
# =========================

@pytest.mark.asyncio
async def test_e2e_rate_limiting_workflow(auth_headers):
    """Test rate limiting across multiple requests."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.download',
                   new_callable=MagicMock):

            # Make multiple rapid requests
            requests_count = 5
            responses = []

            for i in range(requests_count):
                response = await client.post(
                    "/api/v1/download",
                    json={
                        "url": f"https://example.com/video{i}",
                        "quality": "720p"
                    },
                    headers=auth_headers
                )
                responses.append(response)

            # Some should succeed
            success_count = sum(1 for r in responses if r.status_code < 400)
            assert success_count > 0


# =========================
# E2E: Pagination Workflow
# =========================

@pytest.mark.asyncio
async def test_e2e_pagination_workflow(auth_headers):
    """Test pagination across large channel."""
    # Create large channel data
    large_channel = {
        '_type': 'playlist',
        'channel_id': 'UC_large',
        'channel': 'Large Channel',
        'entries': [
            {
                'id': f'vid{i}',
                'title': f'Video {i}',
                'url': f'https://youtube.com/watch?v=vid{i}',
                'webpage_url': f'https://youtube.com/watch?v=vid{i}',
                'duration': 600,
                'view_count': 10000 + i * 1000,
                'upload_date': '20251105'
            }
            for i in range(50)  # 50 videos
        ]
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.extract_info',
                   new_callable=AsyncMock,
                   return_value=large_channel):

            # Page through results
            page_1 = await client.get(
                "/api/v1/channel/info",
                params={
                    "url": "https://youtube.com/@large",
                    "page": 1,
                    "page_size": 20
                },
                headers=auth_headers
            )

            assert page_1.status_code == 200
            data_1 = page_1.json()
            assert data_1['has_next'] is True
            assert data_1['has_previous'] is False

            # Get second page
            page_2 = await client.get(
                "/api/v1/channel/info",
                params={
                    "url": "https://youtube.com/@large",
                    "page": 2,
                    "page_size": 20
                },
                headers=auth_headers
            )

            assert page_2.status_code == 200
            data_2 = page_2.json()
            assert data_2['has_previous'] is True


# =========================
# E2E: Quality Selection Workflow
# =========================

@pytest.mark.asyncio
async def test_e2e_quality_selection_workflow(auth_headers):
    """Test different quality selection methods."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.download',
                   new_callable=MagicMock):

            # 1. Preset quality
            preset_response = await client.post(
                "/api/v1/download",
                json={
                    "url": "https://example.com/video1",
                    "quality": "1080p"
                },
                headers=auth_headers
            )

            assert preset_response.status_code in [200, 201, 202]

            # 2. Custom format string
            custom_response = await client.post(
                "/api/v1/download",
                json={
                    "url": "https://example.com/video2",
                    "custom_format": "bestvideo[height<=1080]+bestaudio"
                },
                headers=auth_headers
            )

            assert custom_response.status_code in [200, 201, 202]

            # 3. Audio only
            audio_response = await client.post(
                "/api/v1/download",
                json={
                    "url": "https://example.com/video3",
                    "audio_only": True,
                    "audio_format": "mp3",
                    "audio_quality": "320"
                },
                headers=auth_headers
            )

            assert audio_response.status_code in [200, 201, 202]


# =========================
# E2E: Metadata and Subtitles Workflow
# =========================

@pytest.mark.asyncio
async def test_e2e_metadata_and_subtitles_workflow(auth_headers):
    """Test downloading with metadata and subtitle options."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.download',
                   new_callable=MagicMock):

            response = await client.post(
                "/api/v1/download",
                json={
                    "url": "https://example.com/video",
                    "quality": "1080p",
                    "download_subtitles": True,
                    "subtitle_languages": ["en", "es", "fr"],
                    "subtitle_format": "srt",
                    "embed_subtitles": True,
                    "write_thumbnail": True,
                    "embed_thumbnail": True,
                    "embed_metadata": True,
                    "write_info_json": True
                },
                headers=auth_headers
            )

            assert response.status_code in [200, 201, 202]


# =========================
# E2E: Long Running Batch
# =========================

@pytest.mark.asyncio
async def test_e2e_long_running_batch_monitoring(auth_headers):
    """Test monitoring a long-running batch download."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('asyncio.create_task', return_value=MagicMock()):
            # Create large batch
            batch_response = await client.post(
                "/api/v1/batch/download",
                json={
                    "urls": [f"https://example.com/video{i}" for i in range(20)],
                    "concurrent_limit": 3,
                    "quality": "720p"
                },
                headers=auth_headers
            )

            assert batch_response.status_code == 202
            batch_id = batch_response.json()['batch_id']

            # Poll status multiple times
            for _ in range(3):
                status_response = await client.get(
                    f"/api/v1/batch/{batch_id}",
                    headers=auth_headers
                )

                assert status_response.status_code == 200

                await asyncio.sleep(0.1)  # Small delay
