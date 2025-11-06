"""Response models for the Ultimate Media Downloader API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl

from app.models.enums import JobStatus


class ProgressInfo(BaseModel):
    """Progress information for a download."""

    percent: float = Field(0.0, ge=0.0, le=100.0, description="Download progress percentage")
    downloaded_bytes: int = Field(0, ge=0, description="Bytes downloaded")
    total_bytes: Optional[int] = Field(None, ge=0, description="Total bytes to download")
    speed: Optional[float] = Field(None, ge=0, description="Download speed in bytes/sec")
    eta: Optional[int] = Field(None, ge=0, description="Estimated time remaining in seconds")
    status: str = Field("idle", description="Current status (idle, downloading, processing, finished)")


class FileInfo(BaseModel):
    """Information about a downloaded file."""

    filename: str = Field(..., description="File name")
    file_url: Optional[str] = Field(None, description="URL to access the file")
    file_path: Optional[str] = Field(None, description="Relative file path")
    size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")
    format: Optional[str] = Field(None, description="File format")
    mime_type: Optional[str] = Field(None, description="MIME type")


class VideoMetadata(BaseModel):
    """Video metadata information."""

    title: Optional[str] = Field(None, description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    uploader: Optional[str] = Field(None, description="Uploader/channel name")
    uploader_id: Optional[str] = Field(None, description="Uploader/channel ID")
    upload_date: Optional[str] = Field(None, description="Upload date (YYYYMMDD)")
    duration: Optional[int] = Field(None, ge=0, description="Duration in seconds")
    view_count: Optional[int] = Field(None, ge=0, description="View count")
    like_count: Optional[int] = Field(None, ge=0, description="Like count")
    comment_count: Optional[int] = Field(None, ge=0, description="Comment count")
    width: Optional[int] = Field(None, ge=0, description="Video width")
    height: Optional[int] = Field(None, ge=0, description="Video height")
    fps: Optional[float] = Field(None, ge=0, description="Frames per second")
    vcodec: Optional[str] = Field(None, description="Video codec")
    acodec: Optional[str] = Field(None, description="Audio codec")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL")
    webpage_url: Optional[str] = Field(None, description="Original webpage URL")
    extractor: Optional[str] = Field(None, description="Extractor used")
    playlist: Optional[str] = Field(None, description="Playlist name")
    playlist_index: Optional[int] = Field(None, description="Index in playlist")
    categories: Optional[List[str]] = Field(None, description="Video categories")
    tags: Optional[List[str]] = Field(None, description="Video tags")


class DownloadResponse(BaseModel):
    """Response model for download operations."""

    request_id: str = Field(..., description="Unique request identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: Optional[ProgressInfo] = Field(None, description="Progress information")
    file_info: Optional[FileInfo] = Field(None, description="Downloaded file information")
    metadata: Optional[VideoMetadata] = Field(None, description="Video metadata")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    duration_sec: Optional[float] = Field(None, ge=0, description="Processing duration in seconds")
    logs_url: Optional[str] = Field(None, description="URL to access job logs")
    webhook_sent: bool = Field(False, description="Whether webhook notification was sent")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "request_id": "req_abc123xyz",
                "status": "completed",
                "progress": {
                    "percent": 100.0,
                    "downloaded_bytes": 52428800,
                    "total_bytes": 52428800,
                    "speed": 1048576.0,
                    "eta": 0,
                    "status": "finished"
                },
                "file_info": {
                    "filename": "example-video.mp4",
                    "file_url": "https://api.example.com/files/example-video.mp4",
                    "size_bytes": 52428800,
                    "format": "mp4",
                    "mime_type": "video/mp4"
                },
                "metadata": {
                    "title": "Example Video",
                    "uploader": "Example Channel",
                    "duration": 300,
                    "view_count": 1000000
                },
                "error": None,
                "created_at": "2025-11-05T10:00:00Z",
                "completed_at": "2025-11-05T10:05:00Z",
                "duration_sec": 300.5
            }
        }


class FormatInfo(BaseModel):
    """Information about a single format."""

    format_id: str = Field(..., description="Format identifier")
    ext: str = Field(..., description="File extension")
    resolution: Optional[str] = Field(None, description="Resolution (e.g., '1920x1080')")
    fps: Optional[float] = Field(None, description="Frames per second")
    vcodec: Optional[str] = Field(None, description="Video codec")
    acodec: Optional[str] = Field(None, description="Audio codec")
    filesize: Optional[int] = Field(None, description="File size in bytes")
    tbr: Optional[float] = Field(None, description="Total bitrate")
    vbr: Optional[float] = Field(None, description="Video bitrate")
    abr: Optional[float] = Field(None, description="Audio bitrate")
    width: Optional[int] = Field(None, description="Video width")
    height: Optional[int] = Field(None, description="Video height")
    format_note: Optional[str] = Field(None, description="Format description")
    quality: Optional[int] = Field(None, description="Quality score")


class FormatsResponse(BaseModel):
    """Response model for available formats."""

    url: str = Field(..., description="Video URL")
    title: Optional[str] = Field(None, description="Video title")
    duration: Optional[int] = Field(None, description="Duration in seconds")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL")
    formats: Dict[str, List[FormatInfo]] = Field(
        ...,
        description="Available formats categorized by type"
    )
    best_video_format: Optional[str] = Field(None, description="Recommended best video format ID")
    best_audio_format: Optional[str] = Field(None, description="Recommended best audio format ID")
    recommended_format: str = Field(
        "bestvideo+bestaudio/best",
        description="Recommended format string"
    )
    extractor: Optional[str] = Field(None, description="Extractor used")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "url": "https://example.com/video",
                "title": "Example Video",
                "duration": 300,
                "formats": {
                    "combined": [],
                    "video_only": [
                        {
                            "format_id": "137",
                            "ext": "mp4",
                            "resolution": "1920x1080",
                            "vcodec": "avc1.640028",
                            "height": 1080
                        }
                    ],
                    "audio_only": [
                        {
                            "format_id": "140",
                            "ext": "m4a",
                            "acodec": "mp4a.40.2",
                            "abr": 128
                        }
                    ]
                },
                "recommended_format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"
            }
        }


class PlaylistItemInfo(BaseModel):
    """Information about a playlist item."""

    id: str = Field(..., description="Video ID")
    title: str = Field(..., description="Video title")
    url: str = Field(..., description="Video URL")
    duration: Optional[int] = Field(None, description="Duration in seconds")
    view_count: Optional[int] = Field(None, description="View count")
    uploader: Optional[str] = Field(None, description="Uploader name")
    upload_date: Optional[str] = Field(None, description="Upload date (YYYYMMDD)")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL")
    playlist_index: int = Field(..., description="Index in playlist")


class PlaylistPreviewResponse(BaseModel):
    """Response model for playlist preview."""

    url: str = Field(..., description="Playlist URL")
    title: Optional[str] = Field(None, description="Playlist title")
    uploader: Optional[str] = Field(None, description="Playlist uploader")
    uploader_id: Optional[str] = Field(None, description="Uploader ID")
    description: Optional[str] = Field(None, description="Playlist description")
    total_items: int = Field(..., ge=0, description="Total number of items in playlist")
    items: List[PlaylistItemInfo] = Field(..., description="Playlist items")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=1, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more items")
    has_previous: bool = Field(..., description="Whether there are previous items")
    extractor: Optional[str] = Field(None, description="Extractor used")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "url": "https://example.com/playlist",
                "title": "Example Playlist",
                "uploader": "Example Channel",
                "total_items": 50,
                "items": [
                    {
                        "id": "video1",
                        "title": "Video 1",
                        "url": "https://example.com/video1",
                        "duration": 300,
                        "playlist_index": 1
                    }
                ],
                "page": 1,
                "page_size": 20,
                "total_pages": 3,
                "has_next": True,
                "has_previous": False
            }
        }


class ChannelInfoResponse(BaseModel):
    """Response model for channel information."""

    url: str = Field(..., description="Channel URL")
    channel_id: Optional[str] = Field(None, description="Channel ID")
    channel_name: Optional[str] = Field(None, description="Channel name")
    description: Optional[str] = Field(None, description="Channel description")
    subscriber_count: Optional[int] = Field(None, description="Subscriber count")
    video_count: Optional[int] = Field(None, description="Total video count")
    filtered_video_count: int = Field(..., description="Videos matching filters")
    videos: List[PlaylistItemInfo] = Field(..., description="Channel videos")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=1, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more videos")
    has_previous: bool = Field(..., description="Whether there are previous videos")
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict,
        description="Applied filters"
    )
    extractor: Optional[str] = Field(None, description="Extractor used")


class JobInfo(BaseModel):
    """Information about a single job in a batch."""

    job_id: str = Field(..., description="Job identifier")
    url: str = Field(..., description="Video URL")
    status: JobStatus = Field(..., description="Job status")
    title: Optional[str] = Field(None, description="Video title")
    progress: Optional[ProgressInfo] = Field(None, description="Progress information")
    file_info: Optional[FileInfo] = Field(None, description="File information")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")


class BatchDownloadResponse(BaseModel):
    """Response model for batch download operations."""

    batch_id: str = Field(..., description="Unique batch identifier")
    status: JobStatus = Field(..., description="Overall batch status")
    total_jobs: int = Field(..., ge=1, description="Total number of jobs")
    completed_jobs: int = Field(0, ge=0, description="Number of completed jobs")
    failed_jobs: int = Field(0, ge=0, description="Number of failed jobs")
    running_jobs: int = Field(0, ge=0, description="Number of running jobs")
    queued_jobs: int = Field(0, ge=0, description="Number of queued jobs")
    jobs: List[JobInfo] = Field(..., description="Individual job details")
    created_at: datetime = Field(..., description="Batch creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Batch start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Batch completion timestamp")
    duration_sec: Optional[float] = Field(None, ge=0, description="Total duration in seconds")
    error: Optional[str] = Field(None, description="Overall error message if applicable")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "batch_id": "batch_xyz789",
                "status": "running",
                "total_jobs": 5,
                "completed_jobs": 2,
                "failed_jobs": 0,
                "running_jobs": 2,
                "queued_jobs": 1,
                "jobs": [
                    {
                        "job_id": "job_1",
                        "url": "https://example.com/video1",
                        "status": "completed",
                        "title": "Video 1",
                        "created_at": "2025-11-05T10:00:00Z"
                    }
                ],
                "created_at": "2025-11-05T10:00:00Z"
            }
        }


class MetadataResponse(BaseModel):
    """Response model for metadata extraction."""

    url: str = Field(..., description="Video URL")
    metadata: VideoMetadata = Field(..., description="Extracted metadata")
    formats_available: int = Field(0, ge=0, description="Number of available formats")
    is_playlist: bool = Field(False, description="Whether URL is a playlist")
    playlist_count: Optional[int] = Field(None, description="Number of items if playlist")
    subtitles_available: List[str] = Field(
        default_factory=list,
        description="Available subtitle languages"
    )
    extractor: Optional[str] = Field(None, description="Extractor used")
    extracted_at: datetime = Field(..., description="Extraction timestamp")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "url": "https://example.com/video",
                "metadata": {
                    "title": "Example Video",
                    "duration": 300,
                    "uploader": "Example Channel",
                    "view_count": 1000000
                },
                "formats_available": 24,
                "is_playlist": False,
                "subtitles_available": ["en", "es", "fr"],
                "extractor": "generic",
                "extracted_at": "2025-11-05T10:00:00Z"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Overall health status (healthy, degraded, unhealthy)")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., ge=0, description="Uptime in seconds")
    checks: Dict[str, Any] = Field(..., description="Individual health checks")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-11-05T10:00:00Z",
                "version": "1.0.0",
                "uptime_seconds": 3600.0,
                "checks": {
                    "storage": {"status": "healthy", "free_space_gb": 50.5},
                    "ytdlp": {"status": "healthy", "version": "2024.11.04"},
                    "queue": {"status": "healthy", "active_jobs": 3, "queued_jobs": 5}
                }
            }
        }


class StatsResponse(BaseModel):
    """Response model for service statistics."""

    total_downloads: int = Field(0, ge=0, description="Total downloads processed")
    total_bytes_downloaded: int = Field(0, ge=0, description="Total bytes downloaded")
    active_downloads: int = Field(0, ge=0, description="Currently active downloads")
    queued_downloads: int = Field(0, ge=0, description="Downloads in queue")
    failed_downloads: int = Field(0, ge=0, description="Failed downloads")
    success_rate: float = Field(0.0, ge=0.0, le=100.0, description="Success rate percentage")
    average_download_time: Optional[float] = Field(
        None,
        ge=0,
        description="Average download time in seconds"
    )
    storage_used_bytes: int = Field(0, ge=0, description="Storage space used")
    storage_available_bytes: int = Field(0, ge=0, description="Storage space available")
    uptime_seconds: float = Field(0, ge=0, description="Service uptime in seconds")
    requests_per_minute: float = Field(0.0, ge=0, description="Request rate per minute")
    ytdlp_version: Optional[str] = Field(None, description="yt-dlp version")
    python_version: Optional[str] = Field(None, description="Python version")
    timestamp: datetime = Field(..., description="Statistics timestamp")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "total_downloads": 1500,
                "total_bytes_downloaded": 107374182400,
                "active_downloads": 5,
                "queued_downloads": 12,
                "failed_downloads": 25,
                "success_rate": 98.3,
                "average_download_time": 45.7,
                "storage_used_bytes": 53687091200,
                "storage_available_bytes": 107374182400,
                "uptime_seconds": 86400.0,
                "requests_per_minute": 2.5,
                "ytdlp_version": "2024.11.04",
                "python_version": "3.11.6",
                "timestamp": "2025-11-05T10:00:00Z"
            }
        }


class LogsResponse(BaseModel):
    """Response model for job logs."""

    request_id: str = Field(..., description="Request identifier")
    logs: List[str] = Field(..., description="Log entries")
    log_level: str = Field("INFO", description="Log level filter applied")
    total_lines: int = Field(..., ge=0, description="Total number of log lines")
    truncated: bool = Field(False, description="Whether logs were truncated")


class CookieResponse(BaseModel):
    """Response model for a single cookie set."""

    cookie_id: str = Field(..., description="Unique cookie set identifier")
    name: str = Field(..., description="Cookie set name")
    created_at: datetime = Field(..., description="Creation timestamp")
    browser: Optional[str] = Field(None, description="Browser extracted from")
    domains: List[str] = Field(default_factory=list, description="Domains covered by cookies")
    status: str = Field("active", description="Cookie status (active, expired)")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "cookie_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "my_auth_cookies",
                "created_at": "2025-11-06T10:00:00Z",
                "browser": "chrome",
                "domains": ["example.com", "auth.example.com"],
                "status": "active"
            }
        }


class CookieListResponse(BaseModel):
    """Response model for list of cookies."""

    cookies: List[CookieResponse] = Field(..., description="List of stored cookie sets")
    total: int = Field(..., ge=0, description="Total number of cookie sets")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "cookies": [
                    {
                        "cookie_id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "my_auth_cookies",
                        "created_at": "2025-11-06T10:00:00Z",
                        "browser": "chrome",
                        "domains": ["example.com"],
                        "status": "active"
                    }
                ],
                "total": 1
            }
        }


class CancelResponse(BaseModel):
    """Response model for cancellation operations."""

    request_id: str = Field(..., description="Request/batch identifier")
    status: str = Field(..., description="Cancellation status")
    cancelled_jobs: int = Field(0, ge=0, description="Number of jobs cancelled")
    message: str = Field(..., description="Status message")
    timestamp: datetime = Field(..., description="Cancellation timestamp")


class DeleteResponse(BaseModel):
    """Response model for deletion operations."""

    id: str = Field(..., description="Deleted resource identifier")
    resource_type: str = Field(..., description="Type of resource deleted")
    status: str = Field(..., description="Deletion status")
    message: str = Field(..., description="Status message")
    timestamp: datetime = Field(..., description="Deletion timestamp")


class ErrorResponse(BaseModel):
    """Response model for API errors."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request identifier if available")
    timestamp: datetime = Field(..., description="Error timestamp")
    status_code: int = Field(..., description="HTTP status code")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid URL format",
                "details": {
                    "field": "url",
                    "constraint": "URL must start with http:// or https://"
                },
                "timestamp": "2025-11-05T10:00:00Z",
                "status_code": 422
            }
        }


class BatchStatusResponse(BaseModel):
    """Response model for batch status check."""

    batch_id: str = Field(..., description="Batch identifier")
    status: JobStatus = Field(..., description="Overall batch status")
    total_jobs: int = Field(..., ge=1, description="Total number of jobs")
    completed_jobs: int = Field(0, ge=0, description="Number of completed jobs")
    failed_jobs: int = Field(0, ge=0, description="Number of failed jobs")
    running_jobs: int = Field(0, ge=0, description="Number of running jobs")
    queued_jobs: int = Field(0, ge=0, description="Number of queued jobs")
    cancelled_jobs: int = Field(0, ge=0, description="Number of cancelled jobs")
    progress_percent: float = Field(0.0, ge=0.0, le=100.0, description="Overall progress")
    estimated_time_remaining: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated time remaining in seconds"
    )
    created_at: datetime = Field(..., description="Batch creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Batch start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Batch completion timestamp")
    last_updated: datetime = Field(..., description="Last update timestamp")
