import json
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestDiscoverEndpoint:
    """Test the /discover endpoint functionality."""

    def test_discover_missing_sources(self, client: TestClient):
        """Test 422 when sources parameter is missing."""
        response = client.get("/discover")
        assert response.status_code == 422  # Validation error for missing required param

    def test_discover_empty_sources(self, client: TestClient):
        """Test 400 when sources parameter is empty."""
        response = client.get("/discover?sources=")
        assert response.status_code == 400
        assert "No valid sources provided" in response.json()["detail"]

    def test_discover_invalid_sources(self, client: TestClient):
        """Test 400 when sources parameter contains only whitespace."""
        response = client.get("/discover?sources=   ,  , ")
        assert response.status_code == 400
        assert "No valid sources provided" in response.json()["detail"]

    @patch("app.run")
    def test_discover_csv_default_output(self, mock_run, client: TestClient):
        """Test CSV default output with default columns."""
        # Mock yt-dlp output
        mock_videos = [
            {
                "id": "video1",
                "title": "Test Video 1",
                "webpage_url": "https://example.com/video1",
                "duration": 120,
                "view_count": 1000,
                "like_count": 50,
                "uploader": "TestChannel",
                "upload_date": "20231201",
            },
            {
                "id": "video2",
                "title": "Test Video 2",
                "url": "https://example.com/video2",
                "duration": 240,
                "view_count": 2000,
                "like_count": 100,
                "uploader": "TestChannel2",
                "upload_date": "20231202",
            },
        ]

        stdout = "\n".join(json.dumps(video) for video in mock_videos)

        # Mock async function properly
        async def mock_async_run(*args, **kwargs):
            return (0, stdout, "")

        mock_run.side_effect = mock_async_run

        response = client.get("/discover?sources=https://example.com/playlist")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")

        # Check CSV header - should only include fields that exist in the data
        header = lines[0]
        assert "id" in header
        assert "title" in header
        assert "url" in header

        # Check data rows
        assert len(lines) >= 3  # header + 2 data rows
        assert "video1" in content
        assert "video2" in content

    @patch("app.run")
    def test_discover_json_output(self, mock_run, client: TestClient):
        """Test JSON output format."""
        mock_videos = [
            {
                "id": "video1",
                "title": "Test Video 1",
                "webpage_url": "https://example.com/video1",
                "upload_date": "20231201",
            }
        ]

        stdout = json.dumps(mock_videos[0])

        # Mock async function properly
        async def mock_async_run(*args, **kwargs):
            return (0, stdout, "")

        mock_run.side_effect = mock_async_run

        response = client.get("/discover?sources=https://example.com/playlist&format=json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "video1"
        assert data[0]["url"] == "https://example.com/video1"  # normalized

    @patch("app.run")
    def test_discover_ndjson_output(self, mock_run, client: TestClient):
        """Test NDJSON output format."""
        mock_videos = [
            {"id": "video1", "title": "Test Video 1"},
            {"id": "video2", "title": "Test Video 2"},
        ]

        stdout = "\n".join(json.dumps(video) for video in mock_videos)

        async def mock_async_run(*args, **kwargs):
            return (0, stdout, "")

        mock_run.side_effect = mock_async_run

        response = client.get("/discover?sources=https://example.com/playlist&format=ndjson")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"

        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")

        assert len(lines) == 2

        # Each line should be valid JSON
        obj1 = json.loads(lines[0])
        obj2 = json.loads(lines[1])

        assert obj1["id"] == "video1"
        assert obj2["id"] == "video2"

    @patch("app.run")
    def test_discover_deduplication(self, mock_run, client: TestClient):
        """Test deduplication when same ID appears across sources."""
        # Simulate two sources returning the same video
        duplicate_video = {"id": "duplicate", "title": "Duplicate Video"}
        unique_video = {"id": "unique", "title": "Unique Video"}

        # Mock will be called twice (once per source)
        stdout1 = json.dumps(duplicate_video) + "\n" + json.dumps(unique_video)
        stdout2 = json.dumps(duplicate_video)  # Same video from second source

        call_count = 0

        async def mock_async_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (0, stdout1, "")
            else:
                return (0, stdout2, "")

        mock_run.side_effect = mock_async_run

        response = client.get(
            "/discover?sources=https://example.com/source1,https://example.com/source2&format=json"
        )

        assert response.status_code == 200
        data = response.json()

        # Should only have 2 unique videos despite duplicate
        assert len(data) == 2
        ids = [video["id"] for video in data]
        assert "duplicate" in ids
        assert "unique" in ids

    def test_discover_dateafter_parsing_valid_yyyymmdd(self, client: TestClient):
        """Test dateafter parsing with valid YYYYMMDD format."""
        from app import _parse_dateafter

        result = _parse_dateafter("20231201")
        assert result == "20231201"

    def test_discover_dateafter_parsing_now_days(self, client: TestClient):
        """Test dateafter parsing with now-<days>days format."""
        from datetime import datetime, timedelta

        from app import _parse_dateafter

        # Test "now-7days"
        result = _parse_dateafter("now-7days")
        expected = (datetime.utcnow() - timedelta(days=7)).strftime("%Y%m%d")
        assert result == expected

        # Test "now-30days"
        result = _parse_dateafter("now-30days")
        expected = (datetime.utcnow() - timedelta(days=30)).strftime("%Y%m%d")
        assert result == expected

    def test_discover_dateafter_parsing_invalid_ignored(self, client: TestClient):
        """Test that invalid dateafter patterns are gracefully ignored."""
        from app import _parse_dateafter

        # Invalid formats should return None
        assert _parse_dateafter("invalid-date") is None
        assert _parse_dateafter("202312") is None  # Too short
        assert _parse_dateafter("now-abc-days") is None
        assert _parse_dateafter("") is None
        assert _parse_dateafter(None) is None

        # Edge case: malformed YYYYMMDD that might be invalid dates
        # Our function doesn't validate date correctness, just format
        # This is acceptable as yt-dlp will handle invalid dates gracefully
        result = _parse_dateafter("20231301")  # Invalid month
        assert result == "20231301"  # Passes format check, yt-dlp handles validity

    def test_discover_match_filter_synthesis(self, client: TestClient):
        """Test match filter synthesis with duration constraints."""
        from app import _synthesize_match_filter

        # Test with no filters
        result = _synthesize_match_filter(None, None, None)
        assert result is None

        # Test with only user filter
        result = _synthesize_match_filter("view_count > 1000", None, None)
        assert result == "(view_count > 1000)"

        # Test with only duration filters
        result = _synthesize_match_filter(None, 60, 300)
        assert result == "(duration >= 60) & (duration <= 300)"

        # Test combining user filter with duration constraints
        result = _synthesize_match_filter("view_count > 1000", 60, 300)
        assert result == "(view_count > 1000) & (duration >= 60) & (duration <= 300)"

        # Test with only min duration
        result = _synthesize_match_filter("original_filter", 120, None)
        assert result == "(original_filter) & (duration >= 120)"

    @patch("app.run")
    def test_discover_limit_param(self, mock_run, client: TestClient):
        """Test limit parameter ensures only up to N entries per source."""

        # Mock run to verify --playlist-end parameter is passed correctly
        async def mock_async_run(*args, **kwargs):
            return (0, '{"id":"test"}', "")

        mock_run.side_effect = mock_async_run

        response = client.get("/discover?sources=https://example.com/playlist&limit=50")

        assert response.status_code == 200

        # Verify yt-dlp was called with correct limit
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]  # First positional argument (cmd list)

        assert "--playlist-end" in call_args
        limit_index = call_args.index("--playlist-end")
        assert call_args[limit_index + 1] == "50"

    @patch("app.run")
    def test_discover_skips_playlist_objects(self, mock_run, client: TestClient):
        """Test that playlist objects are skipped, only video entries retained."""
        stdout = "\n".join(
            [
                json.dumps({"_type": "playlist", "id": "playlist1", "title": "Playlist"}),
                json.dumps({"id": "video1", "title": "Video 1"}),
                json.dumps({"_type": "multi_video", "id": "multi1", "title": "Multi Video"}),
                json.dumps({"id": "video2", "title": "Video 2"}),
            ]
        )

        async def mock_async_run(*args, **kwargs):
            return (0, stdout, "")

        mock_run.side_effect = mock_async_run

        response = client.get("/discover?sources=https://example.com/playlist&format=json")

        assert response.status_code == 200
        data = response.json()

        # Should only have 2 videos, playlists skipped
        assert len(data) == 2
        ids = [video["id"] for video in data]
        assert "video1" in ids
        assert "video2" in ids
        assert "playlist1" not in ids
        assert "multi1" not in ids

    @patch("app.run")
    def test_discover_url_normalization(self, mock_run, client: TestClient):
        """Test URL normalization prefers webpage_url over url."""
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "id": "video1",
                        "url": "https://example.com/raw1",
                        "webpage_url": "https://example.com/webpage1",
                    }
                ),
                json.dumps(
                    {
                        "id": "video2",
                        "url": "https://example.com/raw2",
                        # No webpage_url
                    }
                ),
                json.dumps(
                    {
                        "id": "video3"
                        # No url or webpage_url
                    }
                ),
            ]
        )

        async def mock_async_run(*args, **kwargs):
            return (0, stdout, "")

        mock_run.side_effect = mock_async_run

        response = client.get("/discover?sources=https://example.com/playlist&format=json")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3

        # Check URL normalization
        video1 = next(v for v in data if v["id"] == "video1")
        assert video1["url"] == "https://example.com/webpage1"  # webpage_url preferred

        video2 = next(v for v in data if v["id"] == "video2")
        assert video2["url"] == "https://example.com/raw2"  # fallback to url

        video3 = next(v for v in data if v["id"] == "video3")
        assert video3["url"] == ""  # empty fallback

    @patch("app.run")
    def test_discover_sorts_newest_first(self, mock_run, client: TestClient):
        """Test results are sorted newest-first by upload_date."""
        stdout = "\n".join(
            [
                json.dumps({"id": "old", "title": "Old Video", "upload_date": "20230101"}),
                json.dumps({"id": "new", "title": "New Video", "upload_date": "20231201"}),
                json.dumps({"id": "mid", "title": "Mid Video", "upload_date": "20230601"}),
                json.dumps({"id": "nodate", "title": "No Date Video"}),  # No upload_date
            ]
        )

        async def mock_async_run(*args, **kwargs):
            return (0, stdout, "")

        mock_run.side_effect = mock_async_run

        response = client.get("/discover?sources=https://example.com/playlist&format=json")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 4

        # Check sorting - newest first, videos without dates go to end
        assert data[0]["id"] == "new"  # 2023-12-01
        assert data[1]["id"] == "mid"  # 2023-06-01
        assert data[2]["id"] == "old"  # 2023-01-01
        assert data[3]["id"] == "nodate"  # No date (datetime.min)

    @patch("app.run")
    def test_discover_handles_yt_dlp_errors(self, mock_run, client: TestClient):
        """Test graceful handling of yt-dlp errors and warnings."""
        # Mock yt-dlp returning error code but some valid output
        stdout = json.dumps({"id": "video1", "title": "Working Video"})

        async def mock_async_run(*args, **kwargs):
            return (2, stdout, "Some error occurred")

        mock_run.side_effect = mock_async_run

        response = client.get("/discover?sources=https://example.com/playlist&format=json")

        assert response.status_code == 200
        data = response.json()

        # Should still process the valid output despite error code
        assert len(data) == 1
        assert data[0]["id"] == "video1"

    def test_discover_custom_fields(self, client: TestClient):
        """Test custom fields parameter in CSV output."""
        from app import _rows_to_csv

        test_data = [
            {"id": "1", "title": "Video 1", "duration": 120, "extra": "data"},
            {"id": "2", "title": "Video 2", "duration": 240, "other": "info"},
        ]

        # Test custom field selection
        csv_bytes = _rows_to_csv(test_data, "id,title,duration")
        csv_content = csv_bytes.decode("utf-8")

        lines = csv_content.strip().split("\n")
        assert "id,title,duration" in lines[0]
        assert "extra" not in csv_content  # Should be excluded
        assert "other" not in csv_content  # Should be excluded

        # Test empty fields (should use defaults)
        csv_bytes = _rows_to_csv(test_data, "")
        csv_content = csv_bytes.decode("utf-8")

        # Should include default fields that exist in data
        assert "id" in csv_content
        assert "title" in csv_content
        assert "duration" in csv_content
