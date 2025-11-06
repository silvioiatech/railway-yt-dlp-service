"""Request models for the Ultimate Media Downloader API."""

from typing import List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.enums import (
    AudioFormat,
    QualityPreset,
    SubtitleFormat,
    VideoFormat,
)


class DownloadRequest(BaseModel):
    """Request model for single video download."""

    url: str = Field(..., description="Video URL to download")

    # Quality options
    quality: Optional[QualityPreset] = Field(
        QualityPreset.BEST,
        description="Quality preset"
    )
    custom_format: Optional[str] = Field(
        None,
        description="Custom yt-dlp format string (overrides quality)"
    )

    # Format options
    video_format: Optional[VideoFormat] = Field(
        VideoFormat.MP4,
        description="Preferred video container format"
    )
    audio_only: bool = Field(False, description="Extract audio only")
    audio_format: Optional[AudioFormat] = Field(
        AudioFormat.MP3,
        description="Audio format for extraction"
    )
    audio_quality: Optional[str] = Field(
        "192",
        description="Audio bitrate (96, 128, 192, 256, 320)"
    )

    # Subtitle options
    download_subtitles: bool = Field(False, description="Download subtitles")
    subtitle_languages: Optional[List[str]] = Field(
        ["en"],
        description="Subtitle language codes (e.g., ['en', 'es', 'fr'])"
    )
    subtitle_format: Optional[SubtitleFormat] = Field(
        SubtitleFormat.SRT,
        description="Subtitle format"
    )
    embed_subtitles: bool = Field(False, description="Embed subtitles in video")
    auto_subtitles: bool = Field(False, description="Download auto-generated subs")

    # Thumbnail options
    write_thumbnail: bool = Field(False, description="Download thumbnail")
    embed_thumbnail: bool = Field(False, description="Embed thumbnail in file")

    # Metadata options
    embed_metadata: bool = Field(True, description="Embed metadata in file")
    write_info_json: bool = Field(False, description="Save metadata as JSON")

    # Advanced options
    path_template: Optional[str] = Field(
        "videos/{safe_title}-{id}.{ext}",
        description="Output path template"
    )
    cookies_id: Optional[str] = Field(None, description="Stored cookies ID")
    timeout_sec: int = Field(1800, ge=60, le=7200, description="Timeout in seconds")

    # Webhook
    webhook_url: Optional[HttpUrl] = Field(None, description="Webhook notification URL")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        parsed = urlparse(v)
        if not parsed.netloc:
            raise ValueError("Invalid URL format")

        return v

    @field_validator('subtitle_languages')
    @classmethod
    def validate_languages(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate language codes."""
        if v:
            # Ensure all are 2-3 letter codes
            for lang in v:
                if not (2 <= len(lang) <= 3 and lang.isalpha()):
                    raise ValueError(f"Invalid language code: {lang}")
        return v

    @field_validator('audio_quality')
    @classmethod
    def validate_audio_quality(cls, v: Optional[str]) -> Optional[str]:
        """Validate audio quality bitrate."""
        if v:
            valid_bitrates = ['96', '128', '192', '256', '320']
            if v not in valid_bitrates:
                raise ValueError(f"Audio quality must be one of: {', '.join(valid_bitrates)}")
        return v

    @field_validator('custom_format')
    @classmethod
    def validate_custom_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate custom format string."""
        if v:
            # Basic validation for yt-dlp format strings
            v = v.strip()
            if not v:
                raise ValueError("Custom format cannot be empty")
            # Check for dangerous characters
            dangerous = [';', '&', '|', '`', '$', '(', ')', '<', '>']
            if any(char in v for char in dangerous):
                raise ValueError("Custom format contains invalid characters")
        return v


class PlaylistDownloadRequest(BaseModel):
    """Request model for playlist download."""

    url: str = Field(..., description="Playlist URL")

    # Selection options
    items: Optional[str] = Field(
        None,
        description="Item selection (e.g., '1-10,15,20-25')"
    )
    start: Optional[int] = Field(None, ge=1, description="Start index")
    end: Optional[int] = Field(None, ge=1, description="End index")

    # Download options (inherits from DownloadRequest)
    quality: Optional[QualityPreset] = Field(QualityPreset.BEST)
    custom_format: Optional[str] = Field(None)
    video_format: Optional[VideoFormat] = Field(VideoFormat.MP4)
    audio_only: bool = Field(False)
    audio_format: Optional[AudioFormat] = Field(AudioFormat.MP3)
    audio_quality: Optional[str] = Field("192")

    # Subtitle options
    download_subtitles: bool = Field(False)
    subtitle_languages: Optional[List[str]] = Field(["en"])
    subtitle_format: Optional[SubtitleFormat] = Field(SubtitleFormat.SRT)
    embed_subtitles: bool = Field(False)
    auto_subtitles: bool = Field(False)

    # Thumbnail options
    write_thumbnail: bool = Field(False)
    embed_thumbnail: bool = Field(False)

    # Metadata options
    embed_metadata: bool = Field(True)
    write_info_json: bool = Field(False)

    # Playlist-specific options
    skip_downloaded: bool = Field(True, description="Skip already downloaded videos")
    ignore_errors: bool = Field(True, description="Continue on errors")
    reverse_playlist: bool = Field(False, description="Download in reverse order")

    # Path template
    path_template: Optional[str] = Field(
        "playlists/{playlist}/{playlist_index:03d}-{title}.{ext}",
        description="Output path template"
    )

    # Authentication
    cookies_id: Optional[str] = Field(None)
    timeout_sec: int = Field(3600, ge=60, le=7200)

    # Webhook
    webhook_url: Optional[HttpUrl] = Field(None)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        parsed = urlparse(v)
        if not parsed.netloc:
            raise ValueError("Invalid URL format")

        return v

    @field_validator('items')
    @classmethod
    def validate_items(cls, v: Optional[str]) -> Optional[str]:
        """Validate items selection format."""
        if v:
            # Valid format: "1-10,15,20-25" or "1,2,3" or "1-5"
            v = v.strip()
            parts = v.split(',')
            for part in parts:
                if '-' in part:
                    # Range format
                    range_parts = part.split('-')
                    if len(range_parts) != 2:
                        raise ValueError(f"Invalid range format: {part}")
                    try:
                        start, end = int(range_parts[0]), int(range_parts[1])
                        if start <= 0 or end <= 0 or start > end:
                            raise ValueError(f"Invalid range: {part}")
                    except ValueError:
                        raise ValueError(f"Invalid range values: {part}")
                else:
                    # Single item
                    try:
                        item = int(part)
                        if item <= 0:
                            raise ValueError(f"Item index must be positive: {part}")
                    except ValueError:
                        raise ValueError(f"Invalid item index: {part}")
        return v

    @field_validator('end')
    @classmethod
    def validate_end_after_start(cls, v: Optional[int], info) -> Optional[int]:
        """Validate end is after start."""
        if v is not None and 'start' in info.data:
            start = info.data.get('start')
            if start is not None and v < start:
                raise ValueError("End index must be greater than or equal to start index")
        return v


class ChannelDownloadRequest(BaseModel):
    """Request model for channel download."""

    url: str = Field(..., description="Channel URL")

    # Filter options
    date_after: Optional[str] = Field(
        None,
        description="Download videos after this date (YYYYMMDD)"
    )
    date_before: Optional[str] = Field(
        None,
        description="Download videos before this date (YYYYMMDD)"
    )
    min_duration: Optional[int] = Field(None, ge=0, description="Minimum duration (seconds)")
    max_duration: Optional[int] = Field(None, ge=0, description="Maximum duration (seconds)")
    min_views: Optional[int] = Field(None, ge=0, description="Minimum view count")
    max_views: Optional[int] = Field(None, ge=0, description="Maximum view count")

    # Sort options
    sort_by: Optional[str] = Field(
        "upload_date",
        description="Sort field (upload_date, view_count, duration)"
    )

    # Download options
    quality: Optional[QualityPreset] = Field(QualityPreset.BEST)
    custom_format: Optional[str] = Field(None)
    video_format: Optional[VideoFormat] = Field(VideoFormat.MP4)
    audio_only: bool = Field(False)
    audio_format: Optional[AudioFormat] = Field(AudioFormat.MP3)
    audio_quality: Optional[str] = Field("192")

    # Subtitle options
    download_subtitles: bool = Field(False)
    subtitle_languages: Optional[List[str]] = Field(["en"])
    subtitle_format: Optional[SubtitleFormat] = Field(SubtitleFormat.SRT)
    embed_subtitles: bool = Field(False)

    # Thumbnail options
    write_thumbnail: bool = Field(False)
    embed_thumbnail: bool = Field(False)

    # Metadata options
    embed_metadata: bool = Field(True)
    write_info_json: bool = Field(False)

    # Limits
    max_downloads: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Max videos to download"
    )

    # Playlist-specific options
    skip_downloaded: bool = Field(True)
    ignore_errors: bool = Field(True)

    # Path template
    path_template: Optional[str] = Field(
        "channels/{uploader}/{upload_date}-{title}.{ext}",
        description="Output path template"
    )

    # Authentication
    cookies_id: Optional[str] = Field(None)
    timeout_sec: int = Field(3600, ge=60, le=7200)

    # Webhook
    webhook_url: Optional[HttpUrl] = Field(None)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        parsed = urlparse(v)
        if not parsed.netloc:
            raise ValueError("Invalid URL format")

        return v

    @field_validator('date_after', 'date_before')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format (YYYYMMDD)."""
        if v:
            v = v.strip()
            if len(v) != 8 or not v.isdigit():
                raise ValueError("Date must be in YYYYMMDD format")
            # Basic date validation
            year = int(v[:4])
            month = int(v[4:6])
            day = int(v[6:8])
            if year < 1900 or year > 2100:
                raise ValueError("Year must be between 1900 and 2100")
            if month < 1 or month > 12:
                raise ValueError("Month must be between 01 and 12")
            if day < 1 or day > 31:
                raise ValueError("Day must be between 01 and 31")
        return v

    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort_by field."""
        if v:
            valid_sorts = ['upload_date', 'view_count', 'duration', 'title']
            if v not in valid_sorts:
                raise ValueError(f"sort_by must be one of: {', '.join(valid_sorts)}")
        return v

    @field_validator('max_duration')
    @classmethod
    def validate_max_duration(cls, v: Optional[int], info) -> Optional[int]:
        """Validate max_duration is greater than min_duration."""
        if v is not None and 'min_duration' in info.data:
            min_duration = info.data.get('min_duration')
            if min_duration is not None and v < min_duration:
                raise ValueError("max_duration must be greater than or equal to min_duration")
        return v

    @field_validator('max_views')
    @classmethod
    def validate_max_views(cls, v: Optional[int], info) -> Optional[int]:
        """Validate max_views is greater than min_views."""
        if v is not None and 'min_views' in info.data:
            min_views = info.data.get('min_views')
            if min_views is not None and v < min_views:
                raise ValueError("max_views must be greater than or equal to min_views")
        return v


class BatchDownloadRequest(BaseModel):
    """Request model for batch downloads."""

    urls: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of URLs"
    )

    # Download options
    quality: Optional[QualityPreset] = Field(QualityPreset.BEST)
    custom_format: Optional[str] = Field(None)
    video_format: Optional[VideoFormat] = Field(VideoFormat.MP4)
    audio_only: bool = Field(False)
    audio_format: Optional[AudioFormat] = Field(AudioFormat.MP3)
    audio_quality: Optional[str] = Field("192")

    # Subtitle options
    download_subtitles: bool = Field(False)
    subtitle_languages: Optional[List[str]] = Field(["en"])
    subtitle_format: Optional[SubtitleFormat] = Field(SubtitleFormat.SRT)
    embed_subtitles: bool = Field(False)

    # Thumbnail options
    write_thumbnail: bool = Field(False)
    embed_thumbnail: bool = Field(False)

    # Metadata options
    embed_metadata: bool = Field(True)
    write_info_json: bool = Field(False)

    # Concurrency
    concurrent_limit: int = Field(
        3,
        ge=1,
        le=10,
        description="Max concurrent downloads"
    )

    # Error handling
    stop_on_error: bool = Field(False, description="Stop batch on first error")
    ignore_errors: bool = Field(True, description="Continue on individual errors")

    # Path template
    path_template: Optional[str] = Field(
        "batch/{batch_id}/{safe_title}-{id}.{ext}",
        description="Output path template"
    )

    # Authentication
    cookies_id: Optional[str] = Field(None)
    timeout_sec: int = Field(1800, ge=60, le=7200)

    # Webhook
    webhook_url: Optional[HttpUrl] = Field(None)

    @field_validator('urls')
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        """Validate all URLs."""
        if not v:
            raise ValueError("At least one URL is required")

        validated = []
        for idx, url in enumerate(v):
            url = url.strip()
            if not url:
                raise ValueError(f"URL at index {idx} is empty")
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"URL at index {idx} must start with http:// or https://")

            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValueError(f"Invalid URL format at index {idx}")

            validated.append(url)

        # Check for duplicates
        if len(validated) != len(set(validated)):
            raise ValueError("Duplicate URLs found in batch")

        return validated


class CookiesUploadRequest(BaseModel):
    """Request model for cookies upload."""

    cookies: Optional[str] = Field(
        None,
        description="Cookies in Netscape format"
    )
    name: Optional[str] = Field(
        "default",
        description="Cookie set name"
    )
    browser: Optional[str] = Field(
        None,
        description="Auto-extract from browser (chrome, firefox, edge, safari, brave, opera)"
    )
    profile: Optional[str] = Field(
        None,
        description="Browser profile name (for browsers with multiple profiles)"
    )

    @field_validator('cookies')
    @classmethod
    def validate_cookies(cls, v: Optional[str], info) -> Optional[str]:
        """Validate cookies format."""
        # Either cookies or browser must be provided
        browser = info.data.get('browser')
        if not v and not browser:
            raise ValueError("Either 'cookies' or 'browser' must be provided")

        if v:
            v = v.strip()
            if not v:
                raise ValueError("Cookies cannot be empty")
            # Basic Netscape format check
            lines = v.split('\n')
            has_header = False
            has_data = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    has_header = True
                    continue
                if '\t' in line:
                    has_data = True
                    parts = line.split('\t')
                    if len(parts) < 7:
                        raise ValueError("Invalid Netscape cookies format - insufficient columns")

            if not (has_header or has_data):
                raise ValueError("Invalid Netscape cookies format")

        return v

    @field_validator('browser')
    @classmethod
    def validate_browser(cls, v: Optional[str]) -> Optional[str]:
        """Validate browser name."""
        if v:
            valid_browsers = [
                'chrome', 'firefox', 'edge', 'safari',
                'brave', 'opera', 'chromium'
            ]
            v = v.lower().strip()
            if v not in valid_browsers:
                raise ValueError(
                    f"Browser must be one of: {', '.join(valid_browsers)}"
                )
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate cookie set name."""
        if v:
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty")
            # Only allow alphanumeric, underscore, hyphen
            if not all(c.isalnum() or c in ['_', '-'] for c in v):
                raise ValueError(
                    "Name can only contain letters, numbers, underscores, and hyphens"
                )
            if len(v) > 50:
                raise ValueError("Name cannot be longer than 50 characters")
        return v
