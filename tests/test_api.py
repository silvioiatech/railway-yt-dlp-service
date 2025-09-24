import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

@pytest.fixture
def api_key():
    return "test-api-key"

@pytest.fixture
def headers(api_key):
    return {"X-API-Key": api_key}

def test_root_endpoint():
    """Test root endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["service"] == "yt-dlp Streaming Service"
    assert data["version"] == "2.0.0"
    assert "features" in data

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/healthz")
    # May return 200 or 503 depending on system state
    assert response.status_code in [200, 503]
    
    data = response.json()
    assert "status" in data
    assert "checks" in data

def test_readiness_check():
    """Test readiness check endpoint."""
    response = client.get("/readyz")
    assert response.status_code in [200, 503]

def test_version_endpoint():
    """Test version endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    
    data = response.json()
    assert data["version"] == "2.0.0"

def test_download_no_auth():
    """Test download endpoint requires authentication."""
    response = client.post("/download", json={"url": "https://example.com"})
    assert response.status_code == 401

def test_download_invalid_auth(headers):
    """Test download endpoint with invalid auth."""
    invalid_headers = {"X-API-Key": "invalid-key"}
    response = client.post("/download", json={"url": "https://example.com"}, headers=invalid_headers)
    assert response.status_code == 401

@patch.dict('os.environ', {'API_KEY': 'test-api-key'})
def test_download_youtube_blocked(headers):
    """Test YouTube URLs are blocked when ALLOW_YT_DOWNLOADS=false."""
    response = client.post("/download", json={
        "url": "https://www.youtube.com/watch?v=test"
    }, headers=headers)
    assert response.status_code == 422  # Validation error

@patch.dict('os.environ', {'API_KEY': 'test-api-key'})
def test_download_valid_request(headers):
    """Test valid download request."""
    with patch('app.executor') as mock_executor:
        mock_executor.submit = Mock()
        
        response = client.post("/download", json={
            "url": "https://example.com/video",
            "remote": "test-remote",
            "path": "videos/{safe_title}.{ext}"
        }, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "QUEUED"
        assert "request_id" in data

def test_get_download_status_not_found():
    """Test getting status for non-existent job."""
    response = client.get("/downloads/non-existent-id")
    assert response.status_code == 404

@patch('app.job_states', {'test-id': {'status': 'DONE', 'bytes': 1000}})
def test_get_download_status_found():
    """Test getting status for existing job."""
    response = client.get("/downloads/test-id")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "DONE"
    assert data["request_id"] == "test-id"

if __name__ == "__main__":
    pytest.main([__file__])