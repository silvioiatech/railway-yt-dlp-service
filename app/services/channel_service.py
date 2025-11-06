"""
Channel service for extracting and filtering channel information.

Provides business logic for channel metadata extraction, video filtering,
and batch download job creation for channel videos.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.core.exceptions import MetadataExtractionError
from app.models.requests import ChannelDownloadRequest
from app.models.responses import ChannelInfoResponse, PlaylistItemInfo
from app.services.ytdlp_wrapper import YtdlpWrapper

logger = logging.getLogger(__name__)


class ChannelService:
    """
    Service for channel operations.

    Handles channel metadata extraction, video filtering by date/duration/views,
    and preparation of channel videos for batch downloading.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize channel service.

        Args:
            storage_dir: Optional storage directory override
        """
        settings = get_settings()
        self.storage_dir = storage_dir or settings.STORAGE_DIR
        self.ytdlp = YtdlpWrapper(storage_dir=self.storage_dir)

    async def get_channel_info(
        self,
        url: str,
        date_after: Optional[str] = None,
        date_before: Optional[str] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
        min_views: Optional[int] = None,
        max_views: Optional[int] = None,
        sort_by: str = "upload_date",
        page: int = 1,
        page_size: int = 20,
        cookies_path: Optional[Path] = None,
        timeout_sec: int = 120
    ) -> ChannelInfoResponse:
        """
        Extract channel information with filtering and pagination.

        Args:
            url: Channel URL
            date_after: Filter videos after this date (YYYYMMDD)
            date_before: Filter videos before this date (YYYYMMDD)
            min_duration: Minimum video duration in seconds
            max_duration: Maximum video duration in seconds
            min_views: Minimum view count
            max_views: Maximum view count
            sort_by: Sort field (upload_date, view_count, duration, title)
            page: Page number (1-indexed)
            page_size: Items per page
            cookies_path: Path to cookies file for authentication
            timeout_sec: Timeout for extraction

        Returns:
            ChannelInfoResponse with filtered and paginated videos

        Raises:
            MetadataExtractionError: If channel extraction fails
        """
        logger.info(f"Extracting channel info for: {url}")

        try:
            # Extract channel metadata
            info = await self.ytdlp.extract_info(
                url=url,
                download=False,
                cookies_path=cookies_path,
                timeout_sec=timeout_sec
            )

            # Verify it's a channel
            is_channel = (
                info.get('_type') in ['playlist', 'channel'] or
                'entries' in info
            )
            if not is_channel:
                raise MetadataExtractionError(
                    "URL does not appear to be a channel",
                    url
                )

            # Get all entries
            all_entries = info.get('entries', [])
            total_videos = len(all_entries)

            logger.info(f"Found {total_videos} videos in channel")

            # Apply filters
            filtered_entries = self._apply_filters(
                entries=all_entries,
                date_after=date_after,
                date_before=date_before,
                min_duration=min_duration,
                max_duration=max_duration,
                min_views=min_views,
                max_views=max_views
            )

            logger.info(
                f"After filtering: {len(filtered_entries)} videos "
                f"(filtered out {total_videos - len(filtered_entries)})"
            )

            # Apply sorting
            sorted_entries = self._sort_videos(filtered_entries, sort_by)

            # Calculate pagination
            filtered_count = len(sorted_entries)
            total_pages = max(1, (filtered_count + page_size - 1) // page_size)
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, filtered_count)

            # Get page entries
            page_entries = sorted_entries[start_idx:end_idx]

            # Build video items
            videos: List[PlaylistItemInfo] = []
            for idx, entry in enumerate(page_entries, start=start_idx + 1):
                if not entry:
                    continue

                videos.append(PlaylistItemInfo(
                    id=entry.get('id', f'unknown_{idx}'),
                    title=entry.get('title', 'Unknown Title'),
                    url=entry.get('url') or entry.get('webpage_url', ''),
                    duration=entry.get('duration'),
                    view_count=entry.get('view_count'),
                    uploader=entry.get('uploader'),
                    upload_date=entry.get('upload_date'),
                    thumbnail=entry.get('thumbnail'),
                    playlist_index=idx
                ))

            # Build filters summary
            filters_applied = {}
            if date_after:
                filters_applied['date_after'] = date_after
            if date_before:
                filters_applied['date_before'] = date_before
            if min_duration is not None:
                filters_applied['min_duration'] = min_duration
            if max_duration is not None:
                filters_applied['max_duration'] = max_duration
            if min_views is not None:
                filters_applied['min_views'] = min_views
            if max_views is not None:
                filters_applied['max_views'] = max_views
            if sort_by:
                filters_applied['sort_by'] = sort_by

            logger.info(
                f"Channel info extracted: {filtered_count} filtered videos, "
                f"page {page}/{total_pages}"
            )

            return ChannelInfoResponse(
                url=url,
                channel_id=info.get('channel_id') or info.get('uploader_id'),
                channel_name=(
                    info.get('channel') or
                    info.get('uploader') or
                    info.get('title')
                ),
                description=info.get('description'),
                subscriber_count=info.get('subscriber_count'),
                video_count=total_videos,
                filtered_video_count=filtered_count,
                videos=videos,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
                filters_applied=filters_applied,
                extractor=info.get('extractor')
            )

        except MetadataExtractionError:
            raise
        except Exception as e:
            logger.error(f"Failed to extract channel info: {e}", exc_info=True)
            raise MetadataExtractionError(str(e), url)

    def _apply_filters(
        self,
        entries: List[Dict[str, Any]],
        date_after: Optional[str] = None,
        date_before: Optional[str] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
        min_views: Optional[int] = None,
        max_views: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Apply filters to channel video entries.

        Args:
            entries: List of video entry dictionaries
            date_after: Filter videos after this date (YYYYMMDD)
            date_before: Filter videos before this date (YYYYMMDD)
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            min_views: Minimum view count
            max_views: Maximum view count

        Returns:
            Filtered list of entries
        """
        filtered = []

        for entry in entries:
            if not entry:
                continue

            # Date filtering
            upload_date = entry.get('upload_date')
            if upload_date:
                if date_after and upload_date < date_after:
                    continue
                if date_before and upload_date > date_before:
                    continue

            # Duration filtering
            duration = entry.get('duration')
            if duration is not None:
                if min_duration is not None and duration < min_duration:
                    continue
                if max_duration is not None and duration > max_duration:
                    continue

            # View count filtering
            view_count = entry.get('view_count')
            if view_count is not None:
                if min_views is not None and view_count < min_views:
                    continue
                if max_views is not None and view_count > max_views:
                    continue

            filtered.append(entry)

        return filtered

    def _sort_videos(
        self,
        entries: List[Dict[str, Any]],
        sort_by: str = "upload_date"
    ) -> List[Dict[str, Any]]:
        """
        Sort video entries by specified field.

        Args:
            entries: List of video entry dictionaries
            sort_by: Field to sort by (upload_date, view_count, duration, title)

        Returns:
            Sorted list of entries
        """
        # Map sort field to entry key
        sort_key_map = {
            'upload_date': 'upload_date',
            'view_count': 'view_count',
            'duration': 'duration',
            'title': 'title'
        }

        sort_key = sort_key_map.get(sort_by, 'upload_date')

        # Sort with None handling
        def get_sort_value(entry):
            value = entry.get(sort_key)
            # Handle None values - put them at the end
            if value is None:
                if sort_key == 'title':
                    return ''  # Empty string for titles
                return -1 if sort_key == 'upload_date' else 0
            return value

        # Sort in descending order (most recent, most views, longest first)
        # except for title which is ascending
        reverse = sort_key != 'title'

        try:
            sorted_entries = sorted(entries, key=get_sort_value, reverse=reverse)
        except Exception as e:
            logger.warning(f"Error sorting by {sort_key}: {e}, returning unsorted")
            sorted_entries = entries

        return sorted_entries

    async def prepare_channel_download(
        self,
        request: ChannelDownloadRequest,
        cookies_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Prepare channel download by extracting and filtering videos.

        This method extracts channel info and returns the filtered video list
        for batch job creation. It does not actually download anything.

        Args:
            request: Channel download request
            cookies_path: Path to cookies file

        Returns:
            Dictionary with channel info and filtered video entries

        Raises:
            MetadataExtractionError: If channel extraction fails
        """
        logger.info(f"Preparing channel download for: {request.url}")

        try:
            # Extract channel metadata
            info = await self.ytdlp.extract_info(
                url=request.url,
                download=False,
                cookies_path=cookies_path,
                timeout_sec=request.timeout_sec
            )

            # Verify it's a channel
            is_channel = (
                info.get('_type') in ['playlist', 'channel'] or
                'entries' in info
            )
            if not is_channel:
                raise MetadataExtractionError(
                    "URL does not appear to be a channel",
                    request.url
                )

            # Get all entries
            all_entries = info.get('entries', [])

            # Apply filters
            filtered_entries = self._apply_filters(
                entries=all_entries,
                date_after=request.date_after,
                date_before=request.date_before,
                min_duration=request.min_duration,
                max_duration=request.max_duration,
                min_views=request.min_views,
                max_views=request.max_views
            )

            # Apply sorting
            sorted_entries = self._sort_videos(filtered_entries, request.sort_by)

            # Apply max downloads limit
            if request.max_downloads:
                sorted_entries = sorted_entries[:request.max_downloads]

            logger.info(
                f"Channel download prepared: {len(sorted_entries)} videos selected "
                f"from {len(all_entries)} total"
            )

            return {
                'channel_id': info.get('channel_id') or info.get('uploader_id'),
                'channel_name': (
                    info.get('channel') or
                    info.get('uploader') or
                    info.get('title')
                ),
                'total_videos': len(all_entries),
                'filtered_videos': len(sorted_entries),
                'entries': sorted_entries,
                'metadata': info
            }

        except MetadataExtractionError:
            raise
        except Exception as e:
            logger.error(f"Failed to prepare channel download: {e}", exc_info=True)
            raise MetadataExtractionError(str(e), request.url)


def get_channel_service() -> ChannelService:
    """
    Get ChannelService instance.

    Returns:
        ChannelService: Configured service instance
    """
    return ChannelService()
