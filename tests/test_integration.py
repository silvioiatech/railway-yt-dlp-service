"""Integration tests for the complete multi-token workflow."""

import json
import os
import tempfile
import time
from unittest.mock import patch

from fastapi.testclient import TestClient

import app
from app import FILE_REGISTRY, ONCE_TOKENS


class TestCompleteWorkflow:
    """Test the complete multi-token workflow end-to-end."""

    def setup_method(self):
        """Set up test environment."""
        # Clear registries
        ONCE_TOKENS.clear()
        FILE_REGISTRY.clear()
        
        # Create temp directory for test files
        self.temp_dir = tempfile.mkdtemp()
        app.PUBLIC_FILES_DIR = self.temp_dir
        
        # Create client
        self.client = TestClient(app.app)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enhanced_download_request_with_multi_tokens(self):
        """Test download request with multi-token support."""
        # Test the enhanced download request model
        download_data = {
            "url": "https://example.com/video",
            "tag": "test_multi_token",
            "expected_name": "test_video.mp4",
            "quality": "BEST_MP4",
            "dest": "LOCAL",
            "separate_audio_video": True,
            "audio_format": "m4a",
            "token_count": 3,
            "custom_ttl": 7200
        }
        
        response = self.client.post("/download", json=download_data)
        
        # Should accept the request (doesn't actually download in test)
        assert response.status_code == 200
        result = response.json()
        assert result["accepted"] is True
        assert result["tag"] == "test_multi_token"

    def test_mint_workflow(self):
        """Test the complete minting workflow."""
        # 1. Create a test file and initial token
        filename = "test_video.mp4"
        test_file = os.path.join(self.temp_dir, filename)
        with open(test_file, "wb") as f:
            f.write(b"fake video content" * 1000)
        
        initial_url = app.make_single_use_url(filename, "initial_tag")
        file_id = list(FILE_REGISTRY.keys())[0]
        
        # 2. List files to verify it appears
        response = self.client.get("/files")
        assert response.status_code == 200
        
        files_data = response.json()
        assert files_data["total_files"] == 1
        assert files_data["files"][0]["file_id"] == file_id
        assert files_data["files"][0]["filename"] == filename
        assert files_data["files"][0]["active_tokens"] == 1
        
        # 3. Mint additional tokens
        mint_data = {
            "file_id": file_id,
            "count": 2,
            "ttl_sec": 3600,
            "tag": "minted_tokens"
        }
        
        response = self.client.post("/mint", json=mint_data)
        assert response.status_code == 200
        
        mint_result = response.json()
        assert mint_result["success"] is True
        assert mint_result["file_id"] == file_id
        assert mint_result["tokens_created"] == 2
        assert len(mint_result["urls"]) == 2
        assert mint_result["expires_in_sec"] == 3600
        
        # 4. Verify file now has 3 tokens total
        response = self.client.get("/files")
        files_data = response.json()
        assert files_data["files"][0]["active_tokens"] == 3
        
        # 5. Test one of the minted URLs
        minted_token = mint_result["urls"][0].split("/")[-1]
        
        # Mock the file content for serving
        response = self.client.get(f"/once/{minted_token}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "video/mp4"

    def test_range_requests_still_work(self):
        """Test that HTTP Range requests still work with new token system."""
        # Create a test file
        filename = "test_video.mp4"
        test_file = os.path.join(self.temp_dir, filename)
        content = b"0123456789" * 100  # 1000 bytes
        with open(test_file, "wb") as f:
            f.write(content)
        
        # Create token
        url = app.make_single_use_url(filename, "range_test")
        token = url.split("/")[-1]
        
        # Test range request
        headers = {"Range": "bytes=100-199"}
        response = self.client.get(f"/once/{token}", headers=headers)
        
        assert response.status_code == 206  # Partial Content
        assert response.headers["content-range"] == "bytes 100-199/1000"
        assert response.headers["content-length"] == "100"
        assert len(response.content) == 100

    def test_smart_ttl_functionality(self):
        """Test smart TTL functionality."""
        filename = "test_video.mp4"
        test_file = os.path.join(self.temp_dir, filename)
        with open(test_file, "wb") as f:
            f.write(b"content")
        
        # Create tokens with different TTLs
        short_ttl_url = app.make_single_use_url(filename, "short", ttl_sec=120)  # 2 minutes
        long_ttl_url = app.make_single_use_url(filename, "long", ttl_sec=7200)   # 2 hours
        
        short_token = short_ttl_url.split("/")[-1]
        long_token = long_ttl_url.split("/")[-1]
        
        # Verify different expiry times
        short_meta = ONCE_TOKENS[short_token]
        long_meta = ONCE_TOKENS[long_token]
        
        ttl_diff = long_meta["expiry"] - short_meta["expiry"]
        assert abs(ttl_diff - (7200 - 120)) < 5  # Allow 5 second tolerance

    def test_enhanced_gc_functionality(self):
        """Test enhanced garbage collection."""
        filename = "test_video.mp4"
        test_file = os.path.join(self.temp_dir, filename)
        with open(test_file, "wb") as f:
            f.write(b"content")
        
        # Create multiple tokens
        urls = app.make_multiple_use_urls(filename, "gc_test", count=3)
        tokens = [url.split("/")[-1] for url in urls]
        file_id = list(FILE_REGISTRY.keys())[0]
        
        # Consume first token
        meta1 = ONCE_TOKENS[tokens[0]]
        meta1["consumed"] = True
        app._maybe_delete_and_purge(tokens[0])
        
        # File should still exist
        assert os.path.exists(test_file)
        assert len(FILE_REGISTRY[file_id]["tokens"]) == 2
        
        # Consume second token
        meta2 = ONCE_TOKENS[tokens[1]]
        meta2["consumed"] = True
        app._maybe_delete_and_purge(tokens[1])
        
        # File should still exist
        assert os.path.exists(test_file)
        assert len(FILE_REGISTRY[file_id]["tokens"]) == 1
        
        # Consume last token
        meta3 = ONCE_TOKENS[tokens[2]]
        meta3["consumed"] = True
        app._maybe_delete_and_purge(tokens[2])
        
        # Now file should be deleted
        assert not os.path.exists(test_file)
        assert file_id not in FILE_REGISTRY

    def test_backward_compatibility(self):
        """Test that existing API responses are backward compatible."""
        filename = "test_video.mp4"
        test_file = os.path.join(self.temp_dir, filename)
        with open(test_file, "wb") as f:
            f.write(b"content")
        
        # Create a single token (old style)
        url = app.make_single_use_url(filename, "compat_test")
        
        # Should still work with existing code expectations
        assert url.startswith("/once/")
        token = url.split("/")[-1]
        
        # Token metadata should have expected fields
        meta = ONCE_TOKENS[token]
        expected_fields = ["path", "size", "active", "consumed", "last_seen", "expiry", "tag", "file_id"]
        for field in expected_fields:
            assert field in meta

    def test_api_key_protection_on_new_endpoints(self):
        """Test that new endpoints respect API key protection."""
        # Temporarily set an API key
        original_api_key = app.API_KEY
        app.API_KEY = "test-api-key"
        
        try:
            # Test /mint endpoint without API key
            response = self.client.post("/mint", json={"file_id": "test", "count": 1})
            assert response.status_code == 401
            
            # Test /files endpoint without API key
            response = self.client.get("/files")
            assert response.status_code == 401
            
            # Test with API key
            headers = {"Authorization": "Bearer test-api-key"}
            
            response = self.client.get("/files", headers=headers)
            assert response.status_code == 200
            
        finally:
            # Restore original API key
            app.API_KEY = original_api_key

    def test_error_handling(self):
        """Test error handling in various scenarios."""
        # Test minting tokens for non-existent file
        response = self.client.post("/mint", json={
            "file_id": "nonexistent",
            "count": 1
        })
        assert response.status_code == 404
        
        # Test invalid token access
        response = self.client.get("/once/invalid_token")
        assert response.status_code == 404
        
        # Test validation errors
        response = self.client.post("/mint", json={
            "file_id": "test",
            "count": 0  # Invalid count
        })
        assert response.status_code == 422

    def test_performance_with_many_tokens(self):
        """Test performance with many tokens."""
        filename = "test_video.mp4"
        test_file = os.path.join(self.temp_dir, filename)
        with open(test_file, "wb") as f:
            f.write(b"content")
        
        # Create many tokens for the same file
        start_time = time.time()
        urls = app.make_multiple_use_urls(filename, "perf_test", count=50)
        creation_time = time.time() - start_time
        
        # Should be reasonably fast (less than 1 second)
        assert creation_time < 1.0
        assert len(urls) == 50
        assert len(ONCE_TOKENS) == 50
        assert len(FILE_REGISTRY) == 1
        
        # File registry should track all tokens
        file_id = list(FILE_REGISTRY.keys())[0]
        assert len(FILE_REGISTRY[file_id]["tokens"]) == 50