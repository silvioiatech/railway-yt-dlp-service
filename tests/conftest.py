import pytest
import os
import tempfile
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with safe configuration."""
    # Set safe test environment variables
    os.environ["PUBLIC_FILES_DIR"] = tempfile.mkdtemp()
    os.environ["API_KEY"] = ""  # Disable API key for tests
    os.environ["DRIVE_ENABLED"] = ""  # Disable Drive for tests
    os.environ["LOG_LEVEL"] = "ERROR"  # Reduce logging noise
    
    # Import app after setting environment variables
    from app import app
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_download_request():
    """Sample download request for testing."""
    return {
        "url": "https://example.com/test-video",
        "tag": "test-job-123",
        "expected_name": "test-video.mp4",
        "quality": "BEST_MP4",
        "dest": "LOCAL"
    }


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass