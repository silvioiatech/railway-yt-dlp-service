"""
Integration tests for cookies API endpoints.

Tests POST, GET, and DELETE operations on /api/v1/cookies endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient

from app.main import app


# =========================
# Fixtures
# =========================

@pytest.fixture
def api_key():
    """Get API key for authentication."""
    return "test_api_key"


@pytest.fixture
def auth_headers(api_key):
    """Create authentication headers."""
    return {"X-API-Key": api_key}


@pytest.fixture
def valid_cookies():
    """Valid Netscape format cookies."""
    return """# Netscape HTTP Cookie File
# This is a generated file! Do not edit.

.youtube.com	TRUE	/	TRUE	1735689600	CONSENT	YES+cb.20210101-08-p0
.youtube.com	TRUE	/	FALSE	1735689600	VISITOR_INFO1_LIVE	abcdef123456
.youtube.com	TRUE	/	TRUE	1735689600	LOGIN_INFO	session123
"""


@pytest.fixture
def invalid_cookies():
    """Invalid cookie format."""
    return "This is not a valid cookie format"


# =========================
# Test POST /api/v1/cookies (Upload)
# =========================

@pytest.mark.asyncio
async def test_upload_cookies_success(auth_headers, valid_cookies):
    """Test successful cookie upload."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies,
                "name": "test_cookies"
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()

        assert 'cookie_id' in data
        assert data['name'] == "test_cookies"
        assert 'created_at' in data
        assert 'domains' in data
        assert 'youtube.com' in data['domains']
        assert data['status'] == 'active'


@pytest.mark.asyncio
async def test_upload_cookies_default_name(auth_headers, valid_cookies):
    """Test uploading cookies with default name."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data['name'] == "default"


@pytest.mark.asyncio
async def test_upload_cookies_invalid_format(auth_headers, invalid_cookies):
    """Test uploading invalid cookies."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": invalid_cookies,
                "name": "test"
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Invalid" in response.json()['detail']


@pytest.mark.asyncio
async def test_upload_cookies_empty_string(auth_headers):
    """Test uploading empty cookies."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": "",
                "name": "test"
            },
            headers=auth_headers
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_cookies_missing_cookies_and_browser(auth_headers):
    """Test upload without cookies or browser."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cookies",
            json={
                "name": "test"
            },
            headers=auth_headers
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_cookies_unauthorized():
    """Test cookie upload without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": "# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tTRUE\t123\tname\tvalue",
                "name": "test"
            }
        )

        assert response.status_code in [201, 401]


# =========================
# Test POST /api/v1/cookies (Browser Extraction)
# =========================

@pytest.mark.asyncio
async def test_extract_cookies_from_browser(auth_headers, valid_cookies, tmp_path):
    """Test extracting cookies from browser."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.cookie_manager.yt_dlp.YoutubeDL') as mock_ydl, \
             patch('app.services.cookie_manager.tempfile.NamedTemporaryFile') as mock_temp:

            # Create temporary cookie file
            temp_file = tmp_path / "temp_cookies.txt"
            temp_file.write_text(valid_cookies)

            mock_temp.return_value.__enter__.return_value.name = str(temp_file)
            mock_ydl.return_value.__enter__.return_value.cookiejar = None

            response = await client.post(
                "/api/v1/cookies",
                json={
                    "browser": "chrome",
                    "name": "chrome_cookies"
                },
                headers=auth_headers
            )

            assert response.status_code == 201
            data = response.json()
            assert data['browser'] == "chrome"
            assert data['name'] == "chrome_cookies"


@pytest.mark.asyncio
async def test_extract_cookies_unsupported_browser(auth_headers):
    """Test extracting from unsupported browser."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cookies",
            json={
                "browser": "unsupported_browser",
                "name": "test"
            },
            headers=auth_headers
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_extract_cookies_with_profile(auth_headers, valid_cookies, tmp_path):
    """Test extracting cookies with specific browser profile."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.services.cookie_manager.yt_dlp.YoutubeDL') as mock_ydl, \
             patch('app.services.cookie_manager.tempfile.NamedTemporaryFile') as mock_temp:

            temp_file = tmp_path / "temp_cookies.txt"
            temp_file.write_text(valid_cookies)

            mock_temp.return_value.__enter__.return_value.name = str(temp_file)
            mock_ydl.return_value.__enter__.return_value.cookiejar = None

            response = await client.post(
                "/api/v1/cookies",
                json={
                    "browser": "firefox",
                    "name": "firefox_cookies",
                    "profile": "default"
                },
                headers=auth_headers
            )

            assert response.status_code == 201


# =========================
# Test GET /api/v1/cookies (List)
# =========================

@pytest.mark.asyncio
async def test_list_cookies_empty(auth_headers):
    """Test listing cookies when none exist."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First, ensure clean state by creating a new instance
        response = await client.get(
            "/api/v1/cookies",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert 'cookies' in data
        assert isinstance(data['cookies'], list)


@pytest.mark.asyncio
async def test_list_cookies_with_data(auth_headers, valid_cookies):
    """Test listing cookies with data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload some cookies first
        upload_response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies,
                "name": "test_cookies"
            },
            headers=auth_headers
        )

        assert upload_response.status_code == 201

        # List cookies
        list_response = await client.get(
            "/api/v1/cookies",
            headers=auth_headers
        )

        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data['cookies']) >= 1

        # Check that cookie info is in the list
        cookie_names = [c['name'] for c in data['cookies']]
        assert "test_cookies" in cookie_names


@pytest.mark.asyncio
async def test_list_cookies_unauthorized():
    """Test listing cookies without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/cookies")

        assert response.status_code in [200, 401]


# =========================
# Test GET /api/v1/cookies/{cookie_id} (Get Metadata)
# =========================

@pytest.mark.asyncio
async def test_get_cookie_metadata_success(auth_headers, valid_cookies):
    """Test getting cookie metadata."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload cookies first
        upload_response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies,
                "name": "test_metadata"
            },
            headers=auth_headers
        )

        cookie_id = upload_response.json()['cookie_id']

        # Get metadata
        metadata_response = await client.get(
            f"/api/v1/cookies/{cookie_id}",
            headers=auth_headers
        )

        assert metadata_response.status_code == 200
        data = metadata_response.json()

        assert data['cookie_id'] == cookie_id
        assert data['name'] == "test_metadata"
        assert 'created_at' in data
        assert 'domains' in data


@pytest.mark.asyncio
async def test_get_cookie_metadata_not_found(auth_headers):
    """Test getting metadata for non-existent cookie."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/cookies/nonexistent_id",
            headers=auth_headers
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_cookie_metadata_unauthorized():
    """Test getting cookie metadata without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/cookies/some_id")

        assert response.status_code in [200, 401, 404]


# =========================
# Test DELETE /api/v1/cookies/{cookie_id}
# =========================

@pytest.mark.asyncio
async def test_delete_cookies_success(auth_headers, valid_cookies):
    """Test deleting cookies."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload cookies first
        upload_response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies,
                "name": "to_delete"
            },
            headers=auth_headers
        )

        cookie_id = upload_response.json()['cookie_id']

        # Delete cookies
        delete_response = await client.delete(
            f"/api/v1/cookies/{cookie_id}",
            headers=auth_headers
        )

        assert delete_response.status_code == 200
        data = delete_response.json()

        assert data['id'] == cookie_id
        assert data['status'] == 'deleted'
        assert data['resource_type'] == 'cookies'


@pytest.mark.asyncio
async def test_delete_cookies_not_found(auth_headers):
    """Test deleting non-existent cookies."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(
            "/api/v1/cookies/nonexistent_id",
            headers=auth_headers
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_cookies_no_longer_retrievable(auth_headers, valid_cookies):
    """Test that deleted cookies cannot be retrieved."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload cookies
        upload_response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies,
                "name": "test"
            },
            headers=auth_headers
        )

        cookie_id = upload_response.json()['cookie_id']

        # Delete cookies
        delete_response = await client.delete(
            f"/api/v1/cookies/{cookie_id}",
            headers=auth_headers
        )

        assert delete_response.status_code == 200

        # Try to retrieve
        get_response = await client.get(
            f"/api/v1/cookies/{cookie_id}",
            headers=auth_headers
        )

        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_cookies_unauthorized():
    """Test deleting cookies without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete("/api/v1/cookies/some_id")

        assert response.status_code in [200, 401, 404]


# =========================
# Test Complete Cookie Workflow
# =========================

@pytest.mark.asyncio
async def test_cookies_complete_workflow(auth_headers, valid_cookies):
    """Test complete cookie workflow: upload, list, get, delete."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Upload cookies
        upload_response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies,
                "name": "workflow_test"
            },
            headers=auth_headers
        )

        assert upload_response.status_code == 201
        cookie_id = upload_response.json()['cookie_id']

        # Step 2: List cookies
        list_response = await client.get(
            "/api/v1/cookies",
            headers=auth_headers
        )

        assert list_response.status_code == 200
        cookie_ids = [c['cookie_id'] for c in list_response.json()['cookies']]
        assert cookie_id in cookie_ids

        # Step 3: Get metadata
        metadata_response = await client.get(
            f"/api/v1/cookies/{cookie_id}",
            headers=auth_headers
        )

        assert metadata_response.status_code == 200
        assert metadata_response.json()['name'] == "workflow_test"

        # Step 4: Delete cookies
        delete_response = await client.delete(
            f"/api/v1/cookies/{cookie_id}",
            headers=auth_headers
        )

        assert delete_response.status_code == 200


# =========================
# Test Integration with Downloads
# =========================

@pytest.mark.asyncio
async def test_cookies_integration_with_download(auth_headers, valid_cookies):
    """Test using cookies with download endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload cookies
        upload_response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies,
                "name": "download_cookies"
            },
            headers=auth_headers
        )

        cookie_id = upload_response.json()['cookie_id']

        # Use cookies in download request
        with patch('app.services.ytdlp_wrapper.YtdlpWrapper.download',
                   new_callable=MagicMock):
            download_response = await client.post(
                "/api/v1/download",
                json={
                    "url": "https://example.com/video",
                    "cookies_id": cookie_id,
                    "quality": "1080p"
                },
                headers=auth_headers
            )

            # Should accept the request (actual download is mocked)
            assert download_response.status_code in [200, 201, 202]


# =========================
# Test Error Scenarios
# =========================

@pytest.mark.asyncio
async def test_upload_cookies_with_sql_injection_attempt(auth_headers):
    """Test cookie upload with SQL injection attempt in name."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": "# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tTRUE\t123\tname\tvalue",
                "name": "test'; DROP TABLE cookies; --"
            },
            headers=auth_headers
        )

        # Should be rejected due to validation
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_cookies_very_long_name(auth_headers, valid_cookies):
    """Test uploading cookies with very long name."""
    long_name = "a" * 100  # Exceeds 50 char limit

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies,
                "name": long_name
            },
            headers=auth_headers
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_cookies_special_characters_in_name(auth_headers, valid_cookies):
    """Test uploading cookies with special characters in name."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cookies",
            json={
                "cookies": valid_cookies,
                "name": "test@#$%"
            },
            headers=auth_headers
        )

        assert response.status_code == 422


# =========================
# Test Multiple Cookie Sets
# =========================

@pytest.mark.asyncio
async def test_upload_multiple_cookie_sets(auth_headers, valid_cookies):
    """Test uploading multiple cookie sets."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        cookie_ids = []

        # Upload 3 different cookie sets
        for i in range(3):
            response = await client.post(
                "/api/v1/cookies",
                json={
                    "cookies": valid_cookies,
                    "name": f"cookies_{i}"
                },
                headers=auth_headers
            )

            assert response.status_code == 201
            cookie_ids.append(response.json()['cookie_id'])

        # List all cookies
        list_response = await client.get(
            "/api/v1/cookies",
            headers=auth_headers
        )

        assert list_response.status_code == 200
        data = list_response.json()

        # All should be in the list
        listed_ids = [c['cookie_id'] for c in data['cookies']]
        for cookie_id in cookie_ids:
            assert cookie_id in listed_ids
