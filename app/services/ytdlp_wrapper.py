"""
yt-dlp wrapper service with async subprocess integration.

This module provides a high-level async wrapper around yt-dlp for metadata
extraction, format detection, and media downloads with real-time progress tracking.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yt_dlp

from app.config import get_settings
from app.core.exceptions import (
    DownloadError,
    DownloadTimeoutError,
    MetadataExtractionError,
)
from app.models.requests import (
    ChannelDownloadRequest,
    DownloadRequest,
    PlaylistDownloadRequest,
)
from app.services.ytdlp_options import YtdlpOptionsBuilder

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Track download progress with real-time callbacks.

    Integrates with yt-dlp progress hooks to provide detailed progress
    information including bytes downloaded, speed, and ETA.
    """

    def __init__(
        self,
        request_id: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize progress tracker.

        Args:
            request_id: Unique download request identifier
            callback: Optional callback function for progress updates
        """
        self.request_id = request_id
        self.callback = callback
        self.status = "idle"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed = 0.0
        self.eta = 0
        self.percent = 0.0
        self.current_file = ""
        self.callback_error_count = 0
        self.max_callback_errors = 3

    def __call__(self, d: Dict[str, Any]):
        """
        yt-dlp progress hook callback.

        Args:
            d: Progress dictionary from yt-dlp
        """
        self.status = d.get('status', 'downloading')

        if self.status == 'downloading':
            self.downloaded_bytes = d.get('downloaded_bytes', 0)
            self.total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            self.speed = d.get('speed', 0.0) or 0.0
            self.eta = d.get('eta', 0) or 0
            self.current_file = d.get('filename', '')

            # Calculate percentage
            if self.total_bytes > 0:
                self.percent = min((self.downloaded_bytes / self.total_bytes) * 100, 100.0)

            # Call user callback if provided
            if self.callback:
                try:
                    self.callback({
                        'request_id': self.request_id,
                        'status': self.status,
                        'downloaded_bytes': self.downloaded_bytes,
                        'total_bytes': self.total_bytes,
                        'speed': self.speed,
                        'eta': self.eta,
                        'percent': round(self.percent, 2),
                        'filename': self.current_file,
                    })
                    self.callback_error_count = 0  # Reset on success
                except Exception as e:
                    self.callback_error_count += 1
                    logger.error(
                        f"Progress callback error ({self.callback_error_count}/"
                        f"{self.max_callback_errors}): {e}"
                    )
                    if self.callback_error_count >= self.max_callback_errors:
                        raise DownloadError(
                            f"Progress callback failed {self.max_callback_errors} times"
                        )

        elif self.status == 'finished':
            self.percent = 100.0
            if self.callback:
                try:
                    self.callback({
                        'request_id': self.request_id,
                        'status': 'post_processing',
                        'percent': 100.0,
                        'message': 'Download complete, post-processing...',
                    })
                    self.callback_error_count = 0  # Reset on success
                except Exception as e:
                    self.callback_error_count += 1
                    logger.error(
                        f"Progress callback error ({self.callback_error_count}/"
                        f"{self.max_callback_errors}): {e}"
                    )
                    if self.callback_error_count >= self.max_callback_errors:
                        raise DownloadError(
                            f"Progress callback failed {self.max_callback_errors} times"
                        )

        elif self.status == 'error':
            if self.callback:
                try:
                    self.callback({
                        'request_id': self.request_id,
                        'status': 'error',
                        'error': d.get('error', 'Unknown error'),
                    })
                    self.callback_error_count = 0  # Reset on success
                except Exception as e:
                    self.callback_error_count += 1
                    logger.error(
                        f"Progress callback error ({self.callback_error_count}/"
                        f"{self.max_callback_errors}): {e}"
                    )
                    if self.callback_error_count >= self.max_callback_errors:
                        raise DownloadError(
                            f"Progress callback failed {self.max_callback_errors} times"
                        )


class YtdlpWrapper:
    """
    High-level async wrapper for yt-dlp operations.

    Provides methods for metadata extraction, format detection, and downloads
    with progress tracking and proper error handling.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize yt-dlp wrapper.

        Args:
            storage_dir: Optional storage directory override
        """
        settings = get_settings()
        self.storage_dir = storage_dir or settings.STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.options_builder = YtdlpOptionsBuilder(self.storage_dir)

    async def extract_info(
        self,
        url: str,
        download: bool = False,
        cookies_path: Optional[Path] = None,
        timeout_sec: int = 60
    ) -> Dict[str, Any]:
        """
        Extract video/playlist information without downloading.

        Args:
            url: Video or playlist URL
            download: Whether to download the video
            cookies_path: Path to cookies file for authentication
            timeout_sec: Timeout for metadata extraction

        Returns:
            Dictionary with video/playlist information

        Raises:
            MetadataExtractionError: If extraction fails
            DownloadTimeoutError: If extraction times out
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False if download else 'in_playlist',
            'skip_download': not download,
            'ignoreerrors': False,
        }

        if cookies_path and cookies_path.exists():
            ydl_opts['cookiefile'] = str(cookies_path)

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._extract_info_sync,
                    url,
                    ydl_opts
                ),
                timeout=timeout_sec
            )
            return result

        except asyncio.TimeoutError:
            logger.error(f"Metadata extraction timed out for {url}")
            raise DownloadTimeoutError(timeout_sec)

        except Exception as e:
            logger.error(f"Metadata extraction failed for {url}: {e}")
            raise MetadataExtractionError(str(e), url)

    def _extract_info_sync(self, url: str, opts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous metadata extraction (runs in executor).

        Args:
            url: URL to extract info from
            opts: yt-dlp options dictionary

        Returns:
            Sanitized info dictionary
        """
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return ydl.sanitize_info(info)

    async def get_formats(
        self,
        url: str,
        cookies_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Get available formats for a URL with recommendations.

        Args:
            url: Video URL
            cookies_path: Path to cookies file

        Returns:
            Dictionary with categorized formats and recommendations

        Raises:
            MetadataExtractionError: If format detection fails
        """
        info = await self.extract_info(url, download=False, cookies_path=cookies_path)

        formats = info.get('formats', [])

        # Categorize formats
        video_formats = []
        audio_formats = []
        combined_formats = []

        for fmt in formats:
            format_info = {
                'format_id': fmt.get('format_id'),
                'ext': fmt.get('ext'),
                'resolution': fmt.get('resolution'),
                'fps': fmt.get('fps'),
                'vcodec': fmt.get('vcodec'),
                'acodec': fmt.get('acodec'),
                'filesize': fmt.get('filesize') or fmt.get('filesize_approx'),
                'tbr': fmt.get('tbr'),
                'width': fmt.get('width'),
                'height': fmt.get('height'),
                'format_note': fmt.get('format_note'),
                'quality': fmt.get('quality'),
            }

            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')

            if vcodec != 'none' and acodec != 'none':
                combined_formats.append(format_info)
            elif vcodec != 'none':
                video_formats.append(format_info)
            elif acodec != 'none':
                audio_formats.append(format_info)

        return {
            'title': info.get('title'),
            'duration': info.get('duration'),
            'thumbnail': info.get('thumbnail'),
            'uploader': info.get('uploader'),
            'upload_date': info.get('upload_date'),
            'formats': {
                'combined': combined_formats,
                'video_only': video_formats,
                'audio_only': audio_formats,
            },
            'best_video_format': self._find_best_format(video_formats, 'video'),
            'best_audio_format': self._find_best_format(audio_formats, 'audio'),
            'recommended_format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        }

    def _find_best_format(
        self,
        formats: List[Dict],
        format_type: str = 'video'
    ) -> Optional[str]:
        """
        Find best format ID from a list of formats.

        Args:
            formats: List of format dictionaries
            format_type: Type of format ('video' or 'audio')

        Returns:
            Best format ID or None
        """
        if not formats:
            return None

        # Sort by quality indicators
        if format_type == 'video':
            sorted_formats = sorted(
                formats,
                key=lambda x: (
                    x.get('height', 0),
                    x.get('width', 0),
                    x.get('tbr', 0),
                    x.get('filesize', 0)
                ),
                reverse=True
            )
        else:  # audio
            sorted_formats = sorted(
                formats,
                key=lambda x: (
                    x.get('tbr', 0),
                    x.get('filesize', 0)
                ),
                reverse=True
            )

        return sorted_formats[0].get('format_id') if sorted_formats else None

    async def download(
        self,
        request_id: str,
        request: DownloadRequest,
        cookies_path: Optional[Path] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Download video with specified options.

        Args:
            request_id: Unique request identifier
            request: Download request with options
            cookies_path: Path to cookies file
            progress_callback: Callback for progress updates

        Returns:
            Dictionary with download results including file path

        Raises:
            DownloadError: If download fails
            DownloadTimeoutError: If download times out
        """
        # Build yt-dlp options
        ydl_opts = self.options_builder.build_from_request(request, request_id)

        # Add cookies if provided
        if cookies_path and cookies_path.exists():
            ydl_opts['cookiefile'] = str(cookies_path)

        # Add progress hook
        progress_tracker = ProgressTracker(request_id, progress_callback)
        ydl_opts['progress_hooks'] = [progress_tracker]

        # Add logging for debugging
        if logger.isEnabledFor(logging.DEBUG):
            ydl_opts['verbose'] = True

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._download_sync,
                    request.url,
                    ydl_opts
                ),
                timeout=request.timeout_sec
            )

            return {
                'success': True,
                'file_path': result.get('file_path'),
                'title': result.get('title'),
                'duration': result.get('duration'),
                'filesize': result.get('filesize'),
                'format': result.get('format'),
                'metadata': result.get('metadata', {}),
            }

        except asyncio.TimeoutError:
            logger.error(f"Download timed out for {request_id}")
            raise DownloadTimeoutError(request.timeout_sec)

        except Exception as e:
            logger.error(f"Download failed for {request_id}: {e}", exc_info=True)
            raise DownloadError(str(e))

    def _download_sync(self, url: str, opts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous download execution (runs in executor).

        Args:
            url: URL to download
            opts: yt-dlp options dictionary

        Returns:
            Download result dictionary
        """
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            sanitized = ydl.sanitize_info(info)

            # Get the actual file path
            file_path = None
            if 'requested_downloads' in sanitized and sanitized['requested_downloads']:
                file_path = sanitized['requested_downloads'][0].get('filepath')
            else:
                file_path = ydl.prepare_filename(sanitized)

            return {
                'file_path': file_path,
                'title': sanitized.get('title'),
                'duration': sanitized.get('duration'),
                'filesize': sanitized.get('filesize') or sanitized.get('filesize_approx'),
                'format': sanitized.get('format'),
                'metadata': sanitized,
            }

    async def download_playlist(
        self,
        request_id: str,
        request: PlaylistDownloadRequest,
        cookies_path: Optional[Path] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Download playlist with filtering and selection.

        Args:
            request_id: Unique request identifier
            request: Playlist download request
            cookies_path: Path to cookies file
            progress_callback: Callback for progress updates

        Returns:
            Dictionary with download results

        Raises:
            DownloadError: If download fails
        """
        # Build options for playlist
        ydl_opts = self.options_builder.build_playlist_options(request, request_id)

        if cookies_path and cookies_path.exists():
            ydl_opts['cookiefile'] = str(cookies_path)

        # Progress tracking
        progress_tracker = ProgressTracker(request_id, progress_callback)
        ydl_opts['progress_hooks'] = [progress_tracker]

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._download_playlist_sync,
                    request.url,
                    ydl_opts
                ),
                timeout=request.timeout_sec
            )

            return result

        except asyncio.TimeoutError:
            logger.error(f"Playlist download timed out for {request_id}")
            raise DownloadTimeoutError(request.timeout_sec)

        except Exception as e:
            logger.error(f"Playlist download failed for {request_id}: {e}", exc_info=True)
            raise DownloadError(f"Playlist download failed: {str(e)}")

    def _download_playlist_sync(
        self,
        url: str,
        opts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synchronous playlist download (runs in executor).

        Args:
            url: Playlist URL
            opts: yt-dlp options dictionary

        Returns:
            Playlist download results
        """
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            sanitized = ydl.sanitize_info(info)

            # Extract playlist information
            entries = sanitized.get('entries', [])
            downloaded_count = len([e for e in entries if e is not None])

            return {
                'success': True,
                'playlist_title': sanitized.get('title'),
                'total_entries': len(entries),
                'downloaded_count': downloaded_count,
                'entries': entries,
            }

    async def download_channel(
        self,
        request_id: str,
        request: ChannelDownloadRequest,
        cookies_path: Optional[Path] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Download channel videos with filters.

        Args:
            request_id: Unique request identifier
            request: Channel download request
            cookies_path: Path to cookies file
            progress_callback: Callback for progress updates

        Returns:
            Dictionary with download results

        Raises:
            DownloadError: If download fails
        """
        # Build options for channel
        ydl_opts = self.options_builder.build_channel_options(request, request_id)

        if cookies_path and cookies_path.exists():
            ydl_opts['cookiefile'] = str(cookies_path)

        # Progress tracking
        progress_tracker = ProgressTracker(request_id, progress_callback)
        ydl_opts['progress_hooks'] = [progress_tracker]

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._download_channel_sync,
                    request.url,
                    ydl_opts
                ),
                timeout=request.timeout_sec
            )

            return result

        except asyncio.TimeoutError:
            logger.error(f"Channel download timed out for {request_id}")
            raise DownloadTimeoutError(request.timeout_sec)

        except Exception as e:
            logger.error(f"Channel download failed for {request_id}: {e}", exc_info=True)
            raise DownloadError(f"Channel download failed: {str(e)}")

    def _download_channel_sync(
        self,
        url: str,
        opts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synchronous channel download (runs in executor).

        Args:
            url: Channel URL
            opts: yt-dlp options dictionary

        Returns:
            Channel download results
        """
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            sanitized = ydl.sanitize_info(info)

            # Extract channel information
            entries = sanitized.get('entries', [])
            downloaded_count = len([e for e in entries if e is not None])

            return {
                'success': True,
                'channel_title': sanitized.get('title') or sanitized.get('uploader'),
                'channel_id': sanitized.get('channel_id') or sanitized.get('uploader_id'),
                'total_entries': len(entries),
                'downloaded_count': downloaded_count,
                'entries': entries,
            }
