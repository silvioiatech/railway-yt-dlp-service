import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestDownloadAPI:
    """Test download API endpoints."""

    def test_download_request_validation(self, client: TestClient):
        """Test download request validation."""
        # Test missing URL
        response = client.post("/download", json={})
        assert response.status_code == 422  # Validation error
        
        # Test invalid request
        response = client.post("/download", json={"url": ""})
        assert response.status_code == 400
        assert "Missing url" in response.json()["detail"]

    def test_download_request_success(self, client: TestClient, sample_download_request):
        """Test successful download request submission."""
        response = client.post("/download", json=sample_download_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["accepted"] is True
        assert data["tag"] == sample_download_request["tag"]
        assert data["expected_name"] == sample_download_request["expected_name"]
        assert data["note"] == "processing"

    def test_download_filename_sanitization(self, client: TestClient):
        """Test that filenames are properly sanitized."""
        request_data = {
            "url": "https://example.com/test",
            "expected_name": "bad/file\\name<>:|?*.mp4"
        }
        
        response = client.post("/download", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # Should sanitize dangerous characters
        assert "/" not in data["expected_name"]
        assert "\\" not in data["expected_name"]
        assert "<" not in data["expected_name"]

    def test_download_drive_disabled(self, client: TestClient):
        """Test that Drive destination fails when Drive is disabled."""
        request_data = {
            "url": "https://example.com/test",
            "dest": "DRIVE"
        }
        
        response = client.post("/download", json=request_data)
        assert response.status_code == 400
        assert "Drive not configured" in response.json()["detail"]

    def test_status_endpoint(self, client: TestClient):
        """Test job status endpoint."""
        # Test unknown job
        response = client.get("/status?tag=unknown-job")
        assert response.status_code == 404
        
        data = response.json()
        assert data["tag"] == "unknown-job"
        assert data["status"] == "unknown"

    def test_result_endpoint(self, client: TestClient):
        """Test job result endpoint."""
        # Test unknown job
        response = client.get("/result?tag=unknown-job")
        assert response.status_code == 404
        
        data = response.json()
        assert data["tag"] == "unknown-job"
        assert data["status"] == "unknown"

    def test_status_endpoint_with_job(self, client: TestClient, sample_download_request):
        """Test status endpoint after submitting a job."""
        # Submit job
        response = client.post("/download", json=sample_download_request)
        assert response.status_code == 200
        
        tag = sample_download_request["tag"]
        
        # Check status
        response = client.get(f"/status?tag={tag}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["tag"] == tag
        assert data["status"] in ["queued", "downloading"]

    def test_once_token_invalid(self, client: TestClient):
        """Test serving with invalid token."""
        response = client.get("/once/invalid-token")
        assert response.status_code == 404
        assert "Expired or invalid link" in response.json()["detail"]

    @patch('app.os.path.exists')
    def test_once_token_file_not_found(self, mock_exists, client: TestClient):
        """Test serving when file doesn't exist."""
        # Mock token exists but file doesn't
        from app import ONCE_TOKENS
        
        token = "test-token"
        ONCE_TOKENS[token] = {
            "path": "/nonexistent/file.mp4",
            "size": 1000,
            "active": 0,
            "consumed": False,
            "last_seen": 0,
            "expiry": 999999999999,
            "tag": "test"
        }
        
        mock_exists.return_value = False
        
        response = client.get(f"/once/{token}")
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]
        
        # Token should be removed
        assert token not in ONCE_TOKENS


class TestUtilityFunctions:
    """Test utility functions."""

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from app import sanitize_filename
        
        # Test normal filename
        assert sanitize_filename("normal_file.mp4") == "normal_file.mp4"
        
        # Test dangerous characters
        result = sanitize_filename("bad/file\\name<>:|?*.mp4")
        assert "/" not in result
        assert "\\" not in result
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result

    @pytest.mark.asyncio
    async def test_safe_callback(self):
        """Test safe callback function."""
        from app import safe_callback
        
        # Should not raise exception even with invalid URL
        await safe_callback("invalid-url", {"test": "data"})
        
        # Should not raise exception with empty URL
        await safe_callback("", {"test": "data"})

    def test_job_set(self):
        """Test job registry function."""
        from app import job_set, JOBS
        
        tag = "test-job"
        job_set(tag, status="queued", test_field="test_value")
        
        assert tag in JOBS
        job = JOBS[tag]
        assert job["tag"] == tag
        assert job["status"] == "queued"
        assert job["test_field"] == "test_value"
        assert "updated_at" in job