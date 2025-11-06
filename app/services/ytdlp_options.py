"""
yt-dlp options builder for converting request models to yt-dlp configurations.

This module provides a clean builder pattern for constructing yt-dlp option
dictionaries from Pydantic request models with proper format selection,
post-processors, and filters.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.enums import AudioFormat, QualityPreset, SubtitleFormat, VideoFormat
from app.models.requests import (
    ChannelDownloadRequest,
    DownloadRequest,
    PlaylistDownloadRequest,
)

logger = logging.getLogger(__name__)


class YtdlpOptionsBuilder:
    """
    Build yt-dlp options dictionaries from request models.

    Handles format selection, post-processors, subtitle options, metadata
    embedding, and various filters for downloads, playlists, and channels.
    """

    def __init__(self, storage_dir: Path):
        """
        Initialize options builder.

        Args:
            storage_dir: Root storage directory for downloads
        """
        self.storage_dir = storage_dir

    def build_from_request(
        self,
        request: DownloadRequest,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Build complete yt-dlp options from DownloadRequest.

        Args:
            request: Download request model
            request_id: Unique request identifier

        Returns:
            Dictionary of yt-dlp options
        """
        # Base options
        opts = {
            'quiet': False,
            'no_warnings': False,
            'verbose': False,
            'outtmpl': str(self.storage_dir / request.path_template),
            'restrictfilenames': False,
            'windowsfilenames': True,  # Safe filenames for all platforms
            'no_overwrites': True,
            'continue': True,
            'no_part': False,
            'ignoreerrors': False,
            'no_color': True,
            'extract_flat': False,
        }

        # Format selection
        opts['format'] = self._build_format_string(request)

        # Video format preferences
        if request.video_format and not request.audio_only:
            opts['merge_output_format'] = request.video_format.value

        # Subtitle options
        if request.download_subtitles:
            opts.update(self._build_subtitle_options(request))

        # Thumbnail options
        if request.write_thumbnail or request.embed_thumbnail:
            opts.update(self._build_thumbnail_options(request))

        # Metadata options
        if request.embed_metadata or request.write_info_json:
            opts.update(self._build_metadata_options(request))

        # Post-processors
        postprocessors = self._build_postprocessors(request)
        if postprocessors:
            opts['postprocessors'] = postprocessors

        return opts

    def _build_format_string(self, request: DownloadRequest) -> str:
        """
        Build yt-dlp format selection string.

        Args:
            request: Download request with format preferences

        Returns:
            Format selection string for yt-dlp
        """
        # Custom format takes precedence
        if request.custom_format:
            return request.custom_format

        # Audio-only extraction
        if request.audio_only:
            return 'bestaudio/best'

        # Map quality preset to format string
        if request.quality:
            quality_map = {
                QualityPreset.BEST: 'bestvideo+bestaudio/best',
                QualityPreset.UHD_4K: 'bestvideo[height<=2160]+bestaudio/best',
                QualityPreset.FHD_1080P: 'bestvideo[height<=1080]+bestaudio/best',
                QualityPreset.HD_720P: 'bestvideo[height<=720]+bestaudio/best',
                QualityPreset.SD_480P: 'bestvideo[height<=480]+bestaudio/best',
                QualityPreset.LD_360P: 'bestvideo[height<=360]+bestaudio/best',
                QualityPreset.AUDIO_ONLY: 'bestaudio/best',
            }
            return quality_map.get(request.quality, 'bestvideo+bestaudio/best')

        return 'bestvideo+bestaudio/best'

    def _build_subtitle_options(self, request: DownloadRequest) -> Dict[str, Any]:
        """
        Build subtitle-related options.

        Args:
            request: Download request with subtitle preferences

        Returns:
            Dictionary of subtitle options
        """
        opts = {
            'writesubtitles': True,
            'subtitleslangs': request.subtitle_languages or ['en'],
        }

        if request.auto_subtitles:
            opts['writeautomaticsub'] = True

        if request.subtitle_format:
            opts['subtitlesformat'] = request.subtitle_format.value

        if request.embed_subtitles:
            opts['embedsubtitles'] = True

        return opts

    def _build_thumbnail_options(self, request: DownloadRequest) -> Dict[str, Any]:
        """
        Build thumbnail-related options.

        Args:
            request: Download request with thumbnail preferences

        Returns:
            Dictionary of thumbnail options
        """
        opts = {}

        if request.write_thumbnail:
            opts['writethumbnail'] = True

        if request.embed_thumbnail:
            opts['writethumbnail'] = True
            opts['embedthumbnail'] = True

        return opts

    def _build_metadata_options(self, request: DownloadRequest) -> Dict[str, Any]:
        """
        Build metadata-related options.

        Args:
            request: Download request with metadata preferences

        Returns:
            Dictionary of metadata options
        """
        opts = {}

        if request.write_info_json:
            opts['writeinfojson'] = True

        if request.embed_metadata:
            opts['add_metadata'] = True

        return opts

    def _build_postprocessors(self, request: DownloadRequest) -> List[Dict[str, Any]]:
        """
        Build list of post-processors.

        Args:
            request: Download request with post-processing options

        Returns:
            List of post-processor configurations
        """
        postprocessors = []

        # Audio extraction and conversion
        if request.audio_only and request.audio_format:
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': request.audio_format.value,
                'preferredquality': request.audio_quality or '192',
            })

        # Thumbnail embedding (must come before metadata)
        if request.embed_thumbnail:
            # Convert thumbnail to compatible format first
            postprocessors.append({
                'key': 'FFmpegThumbnailsConvertor',
                'format': 'jpg',
            })
            postprocessors.append({
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            })

        # Subtitle conversion
        if request.download_subtitles and request.subtitle_format:
            postprocessors.append({
                'key': 'FFmpegSubtitlesConvertor',
                'format': request.subtitle_format.value,
            })

        # Subtitle embedding
        if request.embed_subtitles:
            postprocessors.append({
                'key': 'FFmpegEmbedSubtitle',
                'already_have_subtitle': False,
            })

        # Metadata embedding (should be last)
        if request.embed_metadata:
            postprocessors.append({
                'key': 'FFmpegMetadata',
                'add_chapters': True,
                'add_metadata': True,
            })

        return postprocessors

    def build_playlist_options(
        self,
        request: PlaylistDownloadRequest,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Build options for playlist downloads.

        Args:
            request: Playlist download request
            request_id: Unique request identifier

        Returns:
            Dictionary of yt-dlp options for playlist
        """
        # Create a base DownloadRequest to reuse common options
        base_request = DownloadRequest(
            url=request.url,
            quality=request.quality,
            custom_format=request.custom_format,
            video_format=request.video_format,
            audio_only=request.audio_only,
            audio_format=request.audio_format,
            audio_quality=request.audio_quality,
            download_subtitles=request.download_subtitles,
            subtitle_languages=request.subtitle_languages,
            subtitle_format=request.subtitle_format,
            embed_subtitles=request.embed_subtitles,
            auto_subtitles=request.auto_subtitles,
            write_thumbnail=request.write_thumbnail,
            embed_thumbnail=request.embed_thumbnail,
            embed_metadata=request.embed_metadata,
            write_info_json=request.write_info_json,
        )

        opts = self.build_from_request(base_request, request_id)

        # Playlist-specific options
        opts['outtmpl'] = str(self.storage_dir / request.path_template)
        opts['ignoreerrors'] = request.ignore_errors
        opts['noplaylist'] = False
        opts['extract_flat'] = False

        # Item selection
        if request.items:
            opts['playlist_items'] = request.items
        elif request.start or request.end:
            start = request.start or 1
            end = request.end or ''
            opts['playlist_items'] = f"{start}:{end}" if end else f"{start}:"

        # Skip downloaded videos
        if request.skip_downloaded:
            archive_file = self.storage_dir / f'.download-archive-{request_id}.txt'
            opts['download_archive'] = str(archive_file)

        # Reverse order
        if request.reverse_playlist:
            opts['playlistreverse'] = True

        return opts

    def build_channel_options(
        self,
        request: ChannelDownloadRequest,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Build options for channel downloads.

        Args:
            request: Channel download request
            request_id: Unique request identifier

        Returns:
            Dictionary of yt-dlp options for channel
        """
        # Create a base DownloadRequest
        base_request = DownloadRequest(
            url=request.url,
            quality=request.quality,
            custom_format=request.custom_format,
            video_format=request.video_format,
            audio_only=request.audio_only,
            audio_format=request.audio_format,
            audio_quality=request.audio_quality,
            download_subtitles=request.download_subtitles,
            subtitle_languages=request.subtitle_languages,
            subtitle_format=request.subtitle_format,
            embed_subtitles=request.embed_subtitles,
            write_thumbnail=request.write_thumbnail,
            embed_thumbnail=request.embed_thumbnail,
            embed_metadata=request.embed_metadata,
            write_info_json=request.write_info_json,
        )

        opts = self.build_from_request(base_request, request_id)

        # Channel-specific options
        opts['outtmpl'] = str(self.storage_dir / request.path_template)
        opts['ignoreerrors'] = request.ignore_errors
        opts['noplaylist'] = False
        opts['extract_flat'] = False

        # Date filters
        if request.date_after:
            opts['dateafter'] = request.date_after
        if request.date_before:
            opts['datebefore'] = request.date_before

        # Build match filter for duration and views
        match_filters = []

        if request.min_duration is not None:
            match_filters.append(f"duration >= {request.min_duration}")
        if request.max_duration is not None:
            match_filters.append(f"duration <= {request.max_duration}")

        if request.min_views is not None:
            match_filters.append(f"view_count >= {request.min_views}")
        if request.max_views is not None:
            match_filters.append(f"view_count <= {request.max_views}")

        if match_filters:
            opts['match_filter'] = ' & '.join(match_filters)

        # Max downloads
        if request.max_downloads:
            opts['max_downloads'] = request.max_downloads

        # Skip downloaded videos
        if request.skip_downloaded:
            archive_file = self.storage_dir / f'.download-archive-{request_id}.txt'
            opts['download_archive'] = str(archive_file)

        # Sort order (note: yt-dlp uses 'playlistsort' for channels too)
        if request.sort_by:
            # Map sort field names
            sort_map = {
                'upload_date': 'upload_date',
                'view_count': 'view_count',
                'duration': 'duration',
                'title': 'title',
            }
            sort_field = sort_map.get(request.sort_by, 'upload_date')
            opts['playlistsort'] = sort_field

        return opts

    def build_batch_options(
        self,
        request: DownloadRequest,
        request_id: str,
        batch_id: str
    ) -> Dict[str, Any]:
        """
        Build options for batch downloads.

        Args:
            request: Download request
            request_id: Unique request identifier
            batch_id: Batch identifier

        Returns:
            Dictionary of yt-dlp options for batch item
        """
        opts = self.build_from_request(request, request_id)

        # Add batch_id to path template if not present
        if '{batch_id}' not in opts['outtmpl']:
            # Inject batch_id into path
            original_template = opts['outtmpl']
            opts['outtmpl'] = str(
                Path(original_template).parent / f"batch-{batch_id}" / Path(original_template).name
            )

        return opts
