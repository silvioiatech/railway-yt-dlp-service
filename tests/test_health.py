import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health and monitoring endpoints."""

    def test_root_endpoint(self, client: TestClient):
        """Test the root endpoint returns correct information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["ok"] is True
        assert data["service"] == "Railway yt-dlp Service"
        assert data["version"] == "1.0.0"
        assert "time" in data
        assert "default_dest" in data
        assert "drive_enabled" in data

    def test_healthz_endpoint(self, client: TestClient):
        """Test the health check endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "checks" in data
        
        # Check required health checks
        checks = data["checks"]
        assert "storage" in checks
        assert "drive" in checks
        assert "memory" in checks

    def test_metrics_endpoint(self, client: TestClient):
        """Test the metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        
        # Should return either Prometheus format or JSON fallback
        content_type = response.headers.get("content-type", "")
        if "text/plain" in content_type:
            # Prometheus format
            assert "python_info" in response.text
        else:
            # JSON fallback
            data = response.json()
            assert "jobs" in data
            assert "tokens" in data
            assert "timestamp" in data

    def test_security_headers(self, client: TestClient):
        """Test that security headers are present."""
        response = client.get("/")
        headers = response.headers
        
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("x-xss-protection") == "1; mode=block"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_openapi_docs(self, client: TestClient):
        """Test that API documentation is available."""
        # Test OpenAPI JSON
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_data = response.json()
        assert openapi_data["info"]["title"] == "Railway yt-dlp Service"
        assert openapi_data["info"]["version"] == "1.0.0"
        
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")