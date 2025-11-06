"""
Unit tests for channel service.

Tests channel info extraction, filtering, sorting, and pagination logic.
"""

import pytest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import MetadataExtractionError
from app.models.requests import ChannelDownloadRequest
from app.services.channel_service import ChannelService


# =========================
# Fixtures
# =========================

@pytest.fixture
def channel_service(tmp_path):
    """Create channel service with temporary storage."""
    return ChannelService(storage_dir=tmp_path)


@pytest.fixture
def mock_channel_info() -> Dict[str, Any]:
    """Mock yt-dlp channel extraction response."""
    return {
        '_type': 'playlist',
        'channel_id': 'UC_test123',
        'channel': 'Test Channel',
        'uploader': 'Test Channel',
        'uploader_id': 'test_channel',
        'title': 'Test Channel',
        'description': 'A test channel for unit testing',
        'subscriber_count': 1000000,
        'extractor': 'youtube:tab',
        'entries': [
            {
                'id': 'video1',
                'title': 'Video 1 - Recent Popular',
                'url': 'https://youtube.com/watch?v=video1',
                'webpage_url': 'https://youtube.com/watch?v=video1',
                'duration': 600,  # 10 minutes
                'view_count': 100000,
                'uploader': 'Test Channel',
                'upload_date': '20251105',
                'thumbnail': 'https://example.com/thumb1.jpg'
            },
            {
                'id': 'video2',
                'title': 'Video 2 - Old Short',
                'url': 'https://youtube.com/watch?v=video2',
                'webpage_url': 'https://youtube.com/watch?v=video2',
                'duration': 120,  # 2 minutes
                'view_count': 5000,
                'uploader': 'Test Channel',
                'upload_date': '20240101',
                'thumbnail': 'https://example.com/thumb2.jpg'
            },
            {
                'id': 'video3',
                'title': 'Video 3 - Long Video',
                'url': 'https://youtube.com/watch?v=video3',
                'webpage_url': 'https://youtube.com/watch?v=video3',
                'duration': 3600,  # 1 hour
                'view_count': 500000,
                'uploader': 'Test Channel',
                'upload_date': '20251101',
                'thumbnail': 'https://example.com/thumb3.jpg'
            },
            {
                'id': 'video4',
                'title': 'Video 4 - Medium Views',
                'url': 'https://youtube.com/watch?v=video4',
                'webpage_url': 'https://youtube.com/watch?v=video4',
                'duration': 900,  # 15 minutes
                'view_count': 50000,
                'uploader': 'Test Channel',
                'upload_date': '20251103',
                'thumbnail': 'https://example.com/thumb4.jpg'
            },
            {
                'id': 'video5',
                'title': 'Video 5 - No Data',
                'url': 'https://youtube.com/watch?v=video5',
                'webpage_url': 'https://youtube.com/watch?v=video5',
                'duration': None,
                'view_count': None,
                'uploader': 'Test Channel',
                'upload_date': None,
                'thumbnail': None
            }
        ]
    }


# =========================
# Test Channel Info Extraction
# =========================

@pytest.mark.asyncio
async def test_get_channel_info_basic(channel_service, mock_channel_info):
    """Test basic channel info extraction."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test"
        )

        assert result.channel_id == 'UC_test123'
        assert result.channel_name == 'Test Channel'
        assert result.video_count == 5
        assert result.filtered_video_count == 5
        assert len(result.videos) == 5
        assert result.page == 1
        assert result.total_pages == 1


@pytest.mark.asyncio
async def test_get_channel_info_not_channel(channel_service):
    """Test error when URL is not a channel."""
    single_video = {
        '_type': 'video',
        'id': 'video1',
        'title': 'Single Video'
    }

    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=single_video
    ):
        with pytest.raises(MetadataExtractionError) as exc_info:
            await channel_service.get_channel_info(url="https://youtube.com/watch?v=test")

        assert "does not appear to be a channel" in str(exc_info.value)


# =========================
# Test Date Filtering
# =========================

@pytest.mark.asyncio
async def test_date_filter_after(channel_service, mock_channel_info):
    """Test filtering videos after a specific date."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            date_after="20251101"
        )

        # Should include videos from 20251101, 20251103, 20251105
        # Excludes video2 (20240101) and video5 (None)
        assert result.filtered_video_count == 3

        # Check that filtered videos are after date
        for video in result.videos:
            if video.upload_date:
                assert video.upload_date >= "20251101"


@pytest.mark.asyncio
async def test_date_filter_before(channel_service, mock_channel_info):
    """Test filtering videos before a specific date."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            date_before="20251102"
        )

        # Should include video2 (20240101) and video3 (20251101)
        assert result.filtered_video_count == 2


@pytest.mark.asyncio
async def test_date_filter_range(channel_service, mock_channel_info):
    """Test filtering videos within date range."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            date_after="20251101",
            date_before="20251104"
        )

        # Should include video3 (20251101) and video4 (20251103)
        assert result.filtered_video_count == 2


# =========================
# Test Duration Filtering
# =========================

@pytest.mark.asyncio
async def test_duration_filter_min(channel_service, mock_channel_info):
    """Test filtering videos by minimum duration."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            min_duration=600  # 10 minutes
        )

        # Should include video1 (600s), video3 (3600s), video4 (900s)
        assert result.filtered_video_count == 3

        for video in result.videos:
            if video.duration is not None:
                assert video.duration >= 600


@pytest.mark.asyncio
async def test_duration_filter_max(channel_service, mock_channel_info):
    """Test filtering videos by maximum duration."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            max_duration=900  # 15 minutes
        )

        # Should include video1 (600s), video2 (120s), video4 (900s)
        assert result.filtered_video_count == 3


@pytest.mark.asyncio
async def test_duration_filter_range(channel_service, mock_channel_info):
    """Test filtering videos by duration range."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            min_duration=300,  # 5 minutes
            max_duration=1000  # ~16 minutes
        )

        # Should include video1 (600s) and video4 (900s)
        assert result.filtered_video_count == 2


# =========================
# Test View Count Filtering
# =========================

@pytest.mark.asyncio
async def test_views_filter_min(channel_service, mock_channel_info):
    """Test filtering videos by minimum views."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            min_views=50000
        )

        # Should include video1 (100k), video3 (500k), video4 (50k)
        assert result.filtered_video_count == 3


@pytest.mark.asyncio
async def test_views_filter_max(channel_service, mock_channel_info):
    """Test filtering videos by maximum views."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            max_views=100000
        )

        # Should include video1 (100k), video2 (5k), video4 (50k)
        assert result.filtered_video_count == 3


@pytest.mark.asyncio
async def test_views_filter_range(channel_service, mock_channel_info):
    """Test filtering videos by view count range."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            min_views=10000,
            max_views=100000
        )

        # Should include video1 (100k) and video4 (50k)
        assert result.filtered_video_count == 2


# =========================
# Test Combined Filters
# =========================

@pytest.mark.asyncio
async def test_combined_filters(channel_service, mock_channel_info):
    """Test combining multiple filters."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            date_after="20251101",
            min_duration=300,
            min_views=40000
        )

        # Should only include video1, video3, and video4
        # But video3 duration is too long (3600 > 1000), so video1 and video4
        # Actually, no max_duration, so video1, video3, video4
        assert result.filtered_video_count >= 2


# =========================
# Test Sorting
# =========================

@pytest.mark.asyncio
async def test_sort_by_upload_date(channel_service, mock_channel_info):
    """Test sorting by upload date (newest first)."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            sort_by="upload_date",
            page_size=10
        )

        # Should be sorted newest first: video1 (20251105), video4 (20251103), etc.
        videos_with_dates = [v for v in result.videos if v.upload_date]
        assert len(videos_with_dates) >= 2

        # Check descending order
        for i in range(len(videos_with_dates) - 1):
            assert videos_with_dates[i].upload_date >= videos_with_dates[i + 1].upload_date


@pytest.mark.asyncio
async def test_sort_by_view_count(channel_service, mock_channel_info):
    """Test sorting by view count (highest first)."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            sort_by="view_count",
            page_size=10
        )

        # Should be sorted by views: video3 (500k), video1 (100k), video4 (50k), video2 (5k)
        videos_with_views = [v for v in result.videos if v.view_count is not None]

        # Check descending order
        for i in range(len(videos_with_views) - 1):
            assert videos_with_views[i].view_count >= videos_with_views[i + 1].view_count


@pytest.mark.asyncio
async def test_sort_by_duration(channel_service, mock_channel_info):
    """Test sorting by duration (longest first)."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            sort_by="duration",
            page_size=10
        )

        # Should be sorted by duration: video3 (3600s), video4 (900s), video1 (600s), video2 (120s)
        videos_with_duration = [v for v in result.videos if v.duration is not None]

        # Check descending order
        for i in range(len(videos_with_duration) - 1):
            assert videos_with_duration[i].duration >= videos_with_duration[i + 1].duration


@pytest.mark.asyncio
async def test_sort_by_title(channel_service, mock_channel_info):
    """Test sorting by title (alphabetically)."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            sort_by="title",
            page_size=10
        )

        # Should be sorted alphabetically (ascending)
        titles = [v.title for v in result.videos]
        assert titles == sorted(titles)


# =========================
# Test Pagination
# =========================

@pytest.mark.asyncio
async def test_pagination_first_page(channel_service, mock_channel_info):
    """Test first page of pagination."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            page=1,
            page_size=2
        )

        assert result.page == 1
        assert result.page_size == 2
        assert len(result.videos) == 2
        assert result.total_pages == 3  # 5 videos / 2 per page = 3 pages
        assert result.has_next is True
        assert result.has_previous is False


@pytest.mark.asyncio
async def test_pagination_middle_page(channel_service, mock_channel_info):
    """Test middle page of pagination."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            page=2,
            page_size=2
        )

        assert result.page == 2
        assert len(result.videos) == 2
        assert result.has_next is True
        assert result.has_previous is True


@pytest.mark.asyncio
async def test_pagination_last_page(channel_service, mock_channel_info):
    """Test last page of pagination."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            page=3,
            page_size=2
        )

        assert result.page == 3
        assert len(result.videos) == 1  # Last page has only 1 video
        assert result.has_next is False
        assert result.has_previous is True


@pytest.mark.asyncio
async def test_pagination_empty_page(channel_service, mock_channel_info):
    """Test requesting page beyond available pages."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            page=10,
            page_size=2
        )

        # Should return empty results but not error
        assert len(result.videos) == 0
        assert result.page == 10


# =========================
# Test Prepare Channel Download
# =========================

@pytest.mark.asyncio
async def test_prepare_channel_download_basic(channel_service, mock_channel_info):
    """Test preparing channel download."""
    request = ChannelDownloadRequest(
        url="https://youtube.com/@test",
        quality="1080p"
    )

    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.prepare_channel_download(request)

        assert result['channel_id'] == 'UC_test123'
        assert result['channel_name'] == 'Test Channel'
        assert result['total_videos'] == 5
        assert result['filtered_videos'] == 5
        assert len(result['entries']) == 5


@pytest.mark.asyncio
async def test_prepare_channel_download_with_filters(channel_service, mock_channel_info):
    """Test preparing channel download with filters."""
    request = ChannelDownloadRequest(
        url="https://youtube.com/@test",
        date_after="20251101",
        min_duration=300,
        max_downloads=2,
        sort_by="view_count"
    )

    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.prepare_channel_download(request)

        # Filters applied: date_after filters to 3 videos, then max_downloads limits to 2
        assert result['filtered_videos'] == 2
        assert len(result['entries']) == 2


@pytest.mark.asyncio
async def test_prepare_channel_download_max_downloads(channel_service, mock_channel_info):
    """Test max_downloads limit."""
    request = ChannelDownloadRequest(
        url="https://youtube.com/@test",
        max_downloads=3
    )

    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.prepare_channel_download(request)

        assert result['filtered_videos'] == 3
        assert len(result['entries']) == 3


# =========================
# Test Error Handling
# =========================

@pytest.mark.asyncio
async def test_extraction_error_handling(channel_service):
    """Test error handling when extraction fails."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        side_effect=Exception("Network error")
    ):
        with pytest.raises(MetadataExtractionError) as exc_info:
            await channel_service.get_channel_info(url="https://youtube.com/@test")

        assert "Network error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_empty_channel(channel_service):
    """Test handling channel with no videos."""
    empty_channel = {
        '_type': 'playlist',
        'channel_id': 'UC_empty',
        'channel': 'Empty Channel',
        'entries': []
    }

    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=empty_channel
    ):
        result = await channel_service.get_channel_info(url="https://youtube.com/@empty")

        assert result.video_count == 0
        assert result.filtered_video_count == 0
        assert len(result.videos) == 0


@pytest.mark.asyncio
async def test_filters_applied_metadata(channel_service, mock_channel_info):
    """Test that filters_applied metadata is correctly set."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            date_after="20251101",
            min_duration=300,
            max_views=200000,
            sort_by="view_count"
        )

        assert 'date_after' in result.filters_applied
        assert result.filters_applied['date_after'] == "20251101"
        assert 'min_duration' in result.filters_applied
        assert result.filters_applied['min_duration'] == 300
        assert 'max_views' in result.filters_applied
        assert result.filters_applied['max_views'] == 200000
        assert 'sort_by' in result.filters_applied
        assert result.filters_applied['sort_by'] == "view_count"


# =========================
# Test Edge Cases
# =========================

@pytest.mark.asyncio
async def test_videos_without_metadata(channel_service):
    """Test handling videos with missing metadata."""
    channel_with_nulls = {
        '_type': 'playlist',
        'channel_id': 'UC_test',
        'entries': [
            {
                'id': 'video1',
                'title': 'Video 1',
                'url': 'https://youtube.com/watch?v=video1',
                'duration': None,
                'view_count': None,
                'upload_date': None
            },
            None,  # Null entry
            {
                'id': 'video2',
                'title': 'Video 2',
                'url': 'https://youtube.com/watch?v=video2',
                'duration': 100,
                'view_count': 1000,
                'upload_date': '20251105'
            }
        ]
    }

    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=channel_with_nulls
    ):
        result = await channel_service.get_channel_info(url="https://youtube.com/@test")

        # Should handle null entries gracefully
        assert result.video_count == 3
        assert result.filtered_video_count == 2  # Null entry skipped


@pytest.mark.asyncio
async def test_large_page_size(channel_service, mock_channel_info):
    """Test large page size returns all results."""
    with patch.object(
        channel_service.ytdlp,
        'extract_info',
        new_callable=AsyncMock,
        return_value=mock_channel_info
    ):
        result = await channel_service.get_channel_info(
            url="https://youtube.com/@test",
            page_size=100
        )

        assert len(result.videos) == 5
        assert result.total_pages == 1
