"""
Pytest configuration and shared fixtures for all tests.

Provides common fixtures for mocking yt-dlp, authentication, and test data.
"""

import asyncio
import json
import os
import pytest
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

# Set environment variables for testing
os.environ['REQUIRE_API_KEY'] = 'false'
os.environ['API_KEY'] = 'test_api_key_for_tests'
os.environ['STORAGE_DIR'] = '/tmp/test_storage'

# Make event loop reusable for all async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =========================
# Application Fixtures
# =========================

@pytest.fixture
def app_settings():
    """Get application settings for tests."""
    from app.config import get_settings
    settings = get_settings()
    return settings


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create temporary storage directory for tests."""
    storage = tmp_path / "test_storage"
    storage.mkdir(parents=True, exist_ok=True)
    return storage


# =========================
# Authentication Fixtures
# =========================

@pytest.fixture
def api_key():
    """Default API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def auth_headers(api_key):
    """Create authentication headers."""
    return {"X-API-Key": api_key}


@pytest.fixture
def invalid_auth_headers():
    """Create invalid authentication headers."""
    return {"X-API-Key": "invalid_key"}


# =========================
# Channel Data Fixtures
# =========================

@pytest.fixture
def sample_channel_response():
    """Sample yt-dlp channel extraction response."""
    return {
        '_type': 'playlist',
        'channel_id': 'UC_test_channel_123',
        'channel': 'Test Channel',
        'uploader': 'Test Channel',
        'uploader_id': 'test_channel',
        'title': 'Test Channel',
        'description': 'A test channel for unit testing',
        'subscriber_count': 1000000,
        'extractor': 'youtube:tab',
        'entries': [
            {
                'id': 'test_video_1',
                'title': 'Test Video 1',
                'url': 'https://youtube.com/watch?v=test_video_1',
                'webpage_url': 'https://youtube.com/watch?v=test_video_1',
                'duration': 600,
                'view_count': 100000,
                'uploader': 'Test Channel',
                'upload_date': '20251105',
                'thumbnail': 'https://i.ytimg.com/vi/test_video_1/maxresdefault.jpg',
                'description': 'Test video 1 description'
            },
            {
                'id': 'test_video_2',
                'title': 'Test Video 2',
                'url': 'https://youtube.com/watch?v=test_video_2',
                'webpage_url': 'https://youtube.com/watch?v=test_video_2',
                'duration': 1200,
                'view_count': 50000,
                'uploader': 'Test Channel',
                'upload_date': '20251103',
                'thumbnail': 'https://i.ytimg.com/vi/test_video_2/maxresdefault.jpg',
                'description': 'Test video 2 description'
            },
            {
                'id': 'test_video_3',
                'title': 'Test Video 3',
                'url': 'https://youtube.com/watch?v=test_video_3',
                'webpage_url': 'https://youtube.com/watch?v=test_video_3',
                'duration': 300,
                'view_count': 200000,
                'uploader': 'Test Channel',
                'upload_date': '20251101',
                'thumbnail': 'https://i.ytimg.com/vi/test_video_3/maxresdefault.jpg',
                'description': 'Test video 3 description'
            }
        ]
    }


@pytest.fixture
def large_channel_response():
    """Large channel response for pagination testing."""
    entries = []
    for i in range(100):
        entries.append({
            'id': f'video_{i}',
            'title': f'Video {i}',
            'url': f'https://youtube.com/watch?v=video_{i}',
            'webpage_url': f'https://youtube.com/watch?v=video_{i}',
            'duration': 300 + i * 10,
            'view_count': 1000 + i * 100,
            'uploader': 'Test Channel',
            'upload_date': '20251105',
            'thumbnail': f'https://i.ytimg.com/vi/video_{i}/maxresdefault.jpg'
        })

    return {
        '_type': 'playlist',
        'channel_id': 'UC_large_channel',
        'channel': 'Large Test Channel',
        'entries': entries
    }


# =========================
# Playlist Data Fixtures
# =========================

@pytest.fixture
def sample_playlist_response():
    """Sample yt-dlp playlist extraction response."""
    return {
        '_type': 'playlist',
        'id': 'PLtest123',
        'title': 'Test Playlist',
        'uploader': 'Test Uploader',
        'description': 'A test playlist',
        'extractor': 'youtube:playlist',
        'entries': [
            {
                'id': 'playlist_video_1',
                'title': 'Playlist Video 1',
                'url': 'https://youtube.com/watch?v=playlist_video_1',
                'duration': 600,
                'view_count': 10000
            },
            {
                'id': 'playlist_video_2',
                'title': 'Playlist Video 2',
                'url': 'https://youtube.com/watch?v=playlist_video_2',
                'duration': 900,
                'view_count': 20000
            }
        ]
    }


# =========================
# Cookie Fixtures
# =========================

@pytest.fixture
def valid_netscape_cookies():
    """Valid Netscape format cookies for testing."""
    return """# Netscape HTTP Cookie File
# This is a generated file! Do not edit.

.youtube.com	TRUE	/	TRUE	1735689600	CONSENT	YES+cb.20210101-08-p0
.youtube.com	TRUE	/	FALSE	1735689600	VISITOR_INFO1_LIVE	abcdef123456
.youtube.com	TRUE	/	TRUE	1735689600	LOGIN_INFO	session_token_12345
.youtube.com	TRUE	/	FALSE	1735689600	PREF	f1=50000000
"""


@pytest.fixture
def multi_domain_cookies():
    """Cookies for multiple domains."""
    return """# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1735689600	YT_SESSION	yt_token_123
.google.com	TRUE	/	TRUE	1735689600	GOOGLE_SESSION	google_token_456
.example.com	TRUE	/	FALSE	1735689600	AUTH	example_auth_789
"""


@pytest.fixture
def invalid_cookies():
    """Invalid cookie format for testing validation."""
    return "This is not a valid Netscape cookie format"


@pytest.fixture
def encryption_key():
    """32-byte encryption key for testing."""
    return b'test_encryption_key_32_bytes!!'


# =========================
# Batch Data Fixtures
# =========================

@pytest.fixture
def sample_batch_urls():
    """Sample URLs for batch download testing."""
    return [
        "https://example.com/video1",
        "https://example.com/video2",
        "https://example.com/video3",
        "https://example.com/video4",
        "https://example.com/video5"
    ]


# =========================
# Mock Service Fixtures
# =========================

@pytest.fixture
def mock_ytdlp_wrapper():
    """Mock YtdlpWrapper for testing."""
    with patch('app.services.ytdlp_wrapper.YtdlpWrapper') as mock:
        instance = mock.return_value
        instance.extract_info = AsyncMock()
        instance.download = AsyncMock()
        yield instance


@pytest.fixture
def mock_queue_manager():
    """Mock QueueManager for testing."""
    with patch('app.services.queue_manager.QueueManager') as mock:
        instance = mock.return_value
        instance.submit_job = MagicMock()
        instance.cancel_job = MagicMock()
        instance.get_job_count = MagicMock(return_value=0)
        yield instance


@pytest.fixture
def mock_webhook_service():
    """Mock WebhookDeliveryService for testing."""
    with patch('app.services.webhook_service.WebhookDeliveryService') as mock:
        instance = mock.return_value
        instance.send_webhook = AsyncMock()
        yield instance


# =========================
# HTTP Client Fixtures
# =========================

@pytest.fixture
async def test_client():
    """Create HTTP test client for API testing."""
    from httpx import AsyncClient
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# =========================
# Helper Functions
# =========================

@pytest.fixture
def create_temp_cookie_file(tmp_path):
    """Factory fixture to create temporary cookie files."""
    def _create_file(content: str) -> Path:
        cookie_file = tmp_path / f"cookies_{id(content)}.txt"
        cookie_file.write_text(content)
        return cookie_file

    return _create_file


@pytest.fixture
def mock_download_response():
    """Mock successful download response."""
    def _create_response(request_id: str = "test_job_123"):
        return {
            'request_id': request_id,
            'status': 'completed',
            'file_path': '/storage/videos/test_video.mp4',
            'file_size': 10485760,  # 10MB
            'duration_sec': 30.5
        }

    return _create_response


# =========================
# Test Data Loaders
# =========================

@pytest.fixture
def load_fixture_json():
    """Load JSON fixture files."""
    def _load(filename: str) -> Dict[str, Any]:
        fixture_path = Path(__file__).parent / 'fixtures' / filename
        if not fixture_path.exists():
            return {}

        with open(fixture_path, 'r') as f:
            return json.load(f)

    return _load


# =========================
# Cleanup Fixtures
# =========================

@pytest.fixture(autouse=True)
def cleanup_test_files(tmp_path):
    """Automatically cleanup test files after each test."""
    yield

    # Cleanup logic runs after test
    for item in tmp_path.glob('**/*'):
        if item.is_file():
            try:
                item.unlink()
            except Exception:
                pass


# =========================
# Performance Fixtures
# =========================

@pytest.fixture
def benchmark_timer():
    """Simple timer for benchmarking test operations."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0

    return Timer()


# =========================
# Database/State Fixtures
# =========================

@pytest.fixture
def job_state_manager():
    """Create JobStateManager instance for testing."""
    from app.core.state import JobStateManager
    return JobStateManager()


@pytest.fixture
def clean_job_state():
    """Ensure clean job state between tests."""
    from app.core.state import JobStateManager

    manager = JobStateManager()
    # Clear any existing jobs
    manager._jobs.clear()

    yield manager

    # Cleanup after test
    manager._jobs.clear()
