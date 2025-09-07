"""Tests for multi-token one-time URLs functionality."""

import os
import tempfile
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Import the app and override the PUBLIC_FILES_DIR for testing
import app
from app import FILE_REGISTRY, ONCE_TOKENS


class TestMultiTokenURLs:
    """Test multi-token one-time URL functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Clear registries
        ONCE_TOKENS.clear()
        FILE_REGISTRY.clear()
        
        # Create temp directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_video.mp4")
        
        # Create a test file
        with open(self.test_file, "wb") as f:
            f.write(b"fake video content" * 1000)  # Make it somewhat realistic size
        
        # Override the PUBLIC_FILES_DIR
        app.PUBLIC_FILES_DIR = self.temp_dir

    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_make_single_use_url_basic(self):
        """Test basic single use URL creation."""
        filename = "test_video.mp4"
        tag = "test_tag"
        
        url = app.make_single_use_url(filename, tag)
        
        assert url.startswith("/once/")
        assert len(ONCE_TOKENS) == 1
        assert len(FILE_REGISTRY) == 1
        
        # Check token metadata
        token = url.split("/")[-1]
        meta = ONCE_TOKENS[token]
        assert meta["tag"] == tag
        assert meta["path"] == self.test_file
        assert meta["active"] == 0
        assert meta["consumed"] is False
        assert "file_id" in meta

    def test_make_single_use_url_custom_ttl(self):
        """Test single use URL creation with custom TTL."""
        filename = "test_video.mp4"
        tag = "test_tag"
        custom_ttl = 3600  # 1 hour
        
        url = app.make_single_use_url(filename, tag, ttl_sec=custom_ttl)
        
        token = url.split("/")[-1]
        meta = ONCE_TOKENS[token]
        
        # Check that expiry is approximately now + custom_ttl
        expected_expiry = time.time() + custom_ttl
        assert abs(meta["expiry"] - expected_expiry) < 5  # Allow 5 second tolerance

    def test_make_multiple_use_urls(self):
        """Test creating multiple URLs for the same file."""
        filename = "test_video.mp4"
        tag = "test_tag"
        count = 3
        
        urls = app.make_multiple_use_urls(filename, tag, count)
        
        assert len(urls) == count
        assert len(ONCE_TOKENS) == count
        assert len(FILE_REGISTRY) == 1  # Still just one file
        
        # All tokens should reference the same file
        file_id = list(FILE_REGISTRY.keys())[0]
        file_info = FILE_REGISTRY[file_id]
        assert len(file_info["tokens"]) == count
        
        # Each URL should be unique
        assert len(set(urls)) == count

    def test_mint_additional_tokens(self):
        """Test minting additional tokens for existing file."""
        filename = "test_video.mp4"
        tag = "original_tag"
        
        # Create initial token
        initial_url = app.make_single_use_url(filename, tag)
        file_id = list(FILE_REGISTRY.keys())[0]
        
        # Mint additional tokens
        additional_count = 2
        additional_urls = app.mint_additional_tokens(file_id, additional_count)
        
        assert len(additional_urls) == additional_count
        assert len(ONCE_TOKENS) == 1 + additional_count  # Original + additional
        assert len(FILE_REGISTRY) == 1  # Still one file
        
        # File should now have 3 tokens total
        file_info = FILE_REGISTRY[file_id]
        assert len(file_info["tokens"]) == 3

    def test_mint_tokens_with_custom_ttl_and_tag(self):
        """Test minting tokens with custom TTL and tag."""
        filename = "test_video.mp4"
        
        # Create initial token
        initial_url = app.make_single_use_url(filename, "original")
        file_id = list(FILE_REGISTRY.keys())[0]
        
        # Mint with custom parameters
        custom_ttl = 7200  # 2 hours
        custom_tag = "minted_token"
        additional_urls = app.mint_additional_tokens(
            file_id, count=1, ttl_sec=custom_ttl, tag=custom_tag
        )
        
        # Find the new token
        new_token = None
        for token, meta in ONCE_TOKENS.items():
            if meta["tag"] == custom_tag:
                new_token = token
                break
        
        assert new_token is not None
        meta = ONCE_TOKENS[new_token]
        assert meta["tag"] == custom_tag
        
        # Check TTL
        expected_expiry = time.time() + custom_ttl
        assert abs(meta["expiry"] - expected_expiry) < 5

    def test_mint_nonexistent_file(self):
        """Test minting tokens for non-existent file."""
        with pytest.raises(FileNotFoundError):
            app.mint_additional_tokens("nonexistent_file_id")

    def test_file_cleanup_multi_token(self):
        """Test that file is only deleted when all tokens are consumed."""
        filename = "test_video.mp4"
        
        # Create multiple tokens
        urls = app.make_multiple_use_urls(filename, "test", count=3)
        tokens = [url.split("/")[-1] for url in urls]
        
        # Simulate consumption of first two tokens
        for i in range(2):
            meta = ONCE_TOKENS[tokens[i]]
            meta["consumed"] = True
            app._maybe_delete_and_purge(tokens[i])
        
        # File should still exist (one token remaining)
        assert os.path.exists(self.test_file)
        assert len(ONCE_TOKENS) == 1
        assert len(FILE_REGISTRY) == 1
        
        # Consume last token
        meta = ONCE_TOKENS[tokens[2]]
        meta["consumed"] = True
        app._maybe_delete_and_purge(tokens[2])
        
        # Now file should be deleted and registries cleaned
        assert not os.path.exists(self.test_file)
        assert len(ONCE_TOKENS) == 0
        assert len(FILE_REGISTRY) == 0


class TestMintEndpoint:
    """Test the /mint endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, client):
        """Set up for mint endpoint tests."""
        self.client = client
        # Clear registries
        ONCE_TOKENS.clear()
        FILE_REGISTRY.clear()
        
        # Create temp directory and test file
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_video.mp4")
        with open(self.test_file, "wb") as f:
            f.write(b"fake video content" * 1000)
        
        app.PUBLIC_FILES_DIR = self.temp_dir

    def teardown_method(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_mint_endpoint_success(self):
        """Test successful token minting via endpoint."""
        # Create initial file
        filename = "test_video.mp4"
        app.make_single_use_url(filename, "test")
        file_id = list(FILE_REGISTRY.keys())[0]
        
        # Test mint endpoint
        response = self.client.post("/mint", json={
            "file_id": file_id,
            "count": 2,
            "ttl_sec": 3600,
            "tag": "api_minted"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["file_id"] == file_id
        assert data["tokens_created"] == 2
        assert len(data["urls"]) == 2
        assert data["expires_in_sec"] == 3600

    def test_mint_endpoint_validation(self):
        """Test mint endpoint input validation."""
        # Test missing file_id
        response = self.client.post("/mint", json={
            "count": 1
        })
        assert response.status_code == 422
        
        # Test invalid count
        response = self.client.post("/mint", json={
            "file_id": "test",
            "count": 0
        })
        assert response.status_code == 422
        
        # Test count too high
        response = self.client.post("/mint", json={
            "file_id": "test",
            "count": 20
        })
        assert response.status_code == 422

    def test_mint_endpoint_nonexistent_file(self):
        """Test minting tokens for non-existent file."""
        response = self.client.post("/mint", json={
            "file_id": "nonexistent",
            "count": 1
        })
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestListFilesEndpoint:
    """Test the /files endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, client):
        """Set up for files endpoint tests."""
        self.client = client
        ONCE_TOKENS.clear()
        FILE_REGISTRY.clear()
        
        # Create temp directory and test files
        self.temp_dir = tempfile.mkdtemp()
        app.PUBLIC_FILES_DIR = self.temp_dir

    def teardown_method(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_files_empty(self):
        """Test listing files when none exist."""
        response = self.client.get("/files")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_files"] == 0
        assert data["files"] == []

    def test_list_files_with_content(self):
        """Test listing files with content."""
        # Create test files
        filenames = ["video1.mp4", "video2.mp4"]
        for filename in filenames:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, "wb") as f:
                f.write(b"content" * 100)
            
            app.make_single_use_url(filename, f"tag_{filename}")
        
        response = self.client.get("/files")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_files"] == 2
        assert len(data["files"]) == 2
        
        # Check file info structure
        file_info = data["files"][0]
        assert "file_id" in file_info
        assert "filename" in file_info
        assert "size" in file_info
        assert "active_tokens" in file_info
        assert "created_at" in file_info
        
        # Should have 1 active token each
        for file_info in data["files"]:
            assert file_info["active_tokens"] == 1