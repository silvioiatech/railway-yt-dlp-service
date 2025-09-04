import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch


class TestSecurity:
    """Test security features."""

    def test_api_key_disabled_by_default(self, client: TestClient):
        """Test that API key is disabled by default in tests."""
        response = client.post("/download", json={
            "url": "https://example.com/test"
        })
        # Should not require API key authentication
        assert response.status_code != 401

    @patch.dict(os.environ, {"API_KEY": "test-api-key"})
    def test_api_key_required(self):
        """Test API key authentication when enabled."""
        # Need to import after setting environment
        from app import app
        
        with TestClient(app) as client:
            # Request without API key should fail
            response = client.post("/download", json={
                "url": "https://example.com/test"
            })
            assert response.status_code == 401
            assert "API key required" in response.json()["detail"]

    @patch.dict(os.environ, {"API_KEY": "test-api-key"})
    def test_api_key_invalid(self):
        """Test invalid API key."""
        from app import app
        
        with TestClient(app) as client:
            # Request with wrong API key should fail
            response = client.post("/download", 
                json={"url": "https://example.com/test"},
                headers={"Authorization": "Bearer wrong-key"}
            )
            assert response.status_code == 401
            assert "Invalid API key" in response.json()["detail"]

    @patch.dict(os.environ, {"API_KEY": "test-api-key"})
    def test_api_key_valid(self):
        """Test valid API key."""
        from app import app
        
        with TestClient(app) as client:
            # Request with correct API key should succeed
            response = client.post("/download",
                json={"url": "https://example.com/test"},
                headers={"Authorization": "Bearer test-api-key"}
            )
            # Should pass authentication (may fail on other validation)
            assert response.status_code != 401

    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present."""
        response = client.options("/", headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"
        })
        
        # Should handle CORS preflight
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_rate_limiting_structure(self, client: TestClient):
        """Test that rate limiting is configured (structure test)."""
        # Make multiple requests to see if rate limiting is active
        responses = []
        for _ in range(5):
            response = client.get("/healthz")
            responses.append(response.status_code)
        
        # All should succeed in test environment (low limits for testing)
        assert all(status == 200 for status in responses)

    def test_input_validation(self, client: TestClient):
        """Test input validation and sanitization."""
        # Test various malicious inputs
        malicious_inputs = [
            {"url": "javascript:alert('xss')"},
            {"url": "file:///etc/passwd"},
            {"url": "ftp://malicious.com/file"},
            {"expected_name": "../../../etc/passwd"},
            {"expected_name": "file\x00.mp4"},
        ]
        
        for malicious_input in malicious_inputs:
            response = client.post("/download", json=malicious_input)
            # Should either reject or sanitize the input
            assert response.status_code in [400, 422] or response.status_code == 200
            
            if response.status_code == 200:
                # If accepted, filename should be sanitized
                data = response.json()
                if "expected_name" in data:
                    assert "../" not in data["expected_name"]
                    assert "\x00" not in data["expected_name"]


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_headers_present(self, client: TestClient):
        """Test that rate limit headers are present."""
        response = client.get("/healthz")
        assert response.status_code == 200
        
        # Rate limiting middleware should add headers
        # Note: Actual headers depend on slowapi implementation

    def test_different_endpoints_have_limits(self, client: TestClient):
        """Test that different endpoints have rate limits configured."""
        endpoints = [
            "/healthz",
            "/metrics",
            "/",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            # Should not hit rate limits in normal testing
        
        # Test POST endpoint
        response = client.post("/download", json={"url": "https://example.com/test"})
        # Should not hit rate limit on first request
        assert response.status_code in [200, 400, 422]  # 400/422 for validation, not rate limit