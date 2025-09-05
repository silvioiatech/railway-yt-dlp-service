"""Tests for the enhanced /status endpoint."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os

from app import app


class TestStatusEndpoint:
    """Test the enhanced /status endpoint that provides both system and job status."""

    def test_system_status_basic_functionality(self, client: TestClient):
        """Test that system status endpoint returns proper structure."""
        response = client.get("/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "state" in data
        assert "timestamp" in data
        assert "components" in data
        
        # Check required components
        components = data["components"]
        assert "storage" in components
        assert "drive" in components
        assert "security" in components
        assert "rate_limiting" in components
        
        # Each component should have required fields
        for comp_name, comp_data in components.items():
            assert "configured" in comp_data
            assert "state" in comp_data
            assert "details" in comp_data
            assert comp_data["state"] in ["active", "degraded", "inactive"]

    def test_system_status_state_logic(self, client: TestClient):
        """Test that overall state is determined correctly."""
        response = client.get("/status")
        data = response.json()
        
        overall_state = data["state"]
        components = data["components"]
        
        # Overall state should be one of the valid states
        assert overall_state in ["active", "degraded", "inactive"]
        
        # If storage is inactive, overall should be inactive
        if components["storage"]["state"] == "inactive":
            assert overall_state == "inactive"
        
        # If any component is degraded, overall should be degraded (unless storage is inactive)
        elif any(comp["state"] == "degraded" for comp in components.values()):
            assert overall_state == "degraded"

    def test_system_status_with_security(self, client: TestClient):
        """Test system status shows security configuration."""
        response = client.get("/status")
        data = response.json()
        
        security = data["components"]["security"]
        # Just check structure is correct - actual config depends on environment
        assert "configured" in security
        assert "state" in security 
        assert "details" in security
        assert "api_key_protection" in security["details"]
        assert "cors_restricted" in security["details"]

    def test_system_status_with_drive_configured(self, client: TestClient):
        """Test system status shows drive configuration."""
        response = client.get("/status")
        data = response.json()
        
        drive = data["components"]["drive"]
        # Just check structure is correct - actual config depends on environment
        assert "configured" in drive
        assert "state" in drive
        assert "details" in drive

    @patch('os.path.exists')
    @patch('os.access')
    def test_system_status_storage_issues(self, mock_access, mock_exists, client: TestClient):
        """Test system status when storage has issues."""
        mock_exists.return_value = False
        mock_access.return_value = False
        
        response = client.get("/status")
        data = response.json()
        
        storage = data["components"]["storage"]
        assert storage["configured"] is True  # PUBLIC_FILES_DIR is set
        assert storage["state"] == "degraded"  # Directory doesn't exist
        assert storage["details"]["directory_exists"] is False

    def test_job_status_backward_compatibility(self, client: TestClient):
        """Test that job status functionality still works as before."""
        # Test unknown job
        response = client.get("/status?tag=unknown-job")
        assert response.status_code == 404
        
        data = response.json()
        assert data["tag"] == "unknown-job"
        assert data["status"] == "unknown"

    def test_job_status_with_existing_job(self, client: TestClient):
        """Test job status when a job exists in the registry."""
        from app import JOBS, job_set
        
        # Add a test job
        test_tag = "test-job-123"
        job_set(test_tag, status="downloading", dest="LOCAL")
        
        try:
            response = client.get(f"/status?tag={test_tag}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["tag"] == test_tag
            assert data["status"] == "downloading"
            assert data["dest"] == "LOCAL"
        finally:
            # Clean up
            if test_tag in JOBS:
                del JOBS[test_tag]

    def test_status_endpoint_rate_limiting(self, client: TestClient):
        """Test that rate limiting is applied to status endpoint."""
        # Make multiple requests to check rate limiting is working
        responses = []
        for i in range(5):
            response = client.get("/status")
            responses.append(response.status_code)
        
        # All should succeed initially (rate limit should be generous)
        assert all(status == 200 for status in responses)

    def test_system_status_secret_safety(self, client: TestClient):
        """Test that system status doesn't expose sensitive information."""
        response = client.get("/status")
        data = response.json()
        
        # Convert to string and check for common secret patterns
        response_str = str(data)
        
        # Should not contain actual secrets
        assert "password" not in response_str.lower()
        assert "secret" not in response_str.lower()
        assert "key" not in response_str.lower() or "api_key_protection" in response_str
        
        # Should not expose actual configuration values
        for comp_data in data["components"].values():
            details = comp_data.get("details", {})
            for value in details.values():
                if isinstance(value, str):
                    # Values should not look like secrets (no long random strings)
                    assert len(value) < 50 or value in ["check_failed", "ok", "failed"]

    @patch('app._check_storage_config')
    def test_system_status_handles_exceptions(self, mock_storage_check, client: TestClient):
        """Test that system status handles component check exceptions gracefully."""
        mock_storage_check.side_effect = Exception("Test exception")
        
        response = client.get("/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["state"] == "inactive"
        assert "error" in data
        assert data["error"] == "status_check_failed"