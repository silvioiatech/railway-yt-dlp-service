"""Data models and schemas."""

from app.models.enums import (
    AudioFormat,
    JobStatus,
    QualityPreset,
    SubtitleFormat,
    VideoFormat,
)
from app.models.requests import (
    BatchDownloadRequest,
    ChannelDownloadRequest,
    CookiesUploadRequest,
    DownloadRequest,
    PlaylistDownloadRequest,
)
from app.models.responses import (
    BatchDownloadResponse,
    BatchStatusResponse,
    CancelResponse,
    ChannelInfoResponse,
    CookiesResponse,
    DeleteResponse,
    DownloadResponse,
    ErrorResponse,
    FileInfo,
    FormatInfo,
    FormatsResponse,
    HealthResponse,
    JobInfo,
    LogsResponse,
    MetadataResponse,
    PlaylistItemInfo,
    PlaylistPreviewResponse,
    ProgressInfo,
    StatsResponse,
    VideoMetadata,
)

__all__ = [
    # Enums
    "AudioFormat",
    "JobStatus",
    "QualityPreset",
    "SubtitleFormat",
    "VideoFormat",
    # Request Models
    "BatchDownloadRequest",
    "ChannelDownloadRequest",
    "CookiesUploadRequest",
    "DownloadRequest",
    "PlaylistDownloadRequest",
    # Response Models
    "BatchDownloadResponse",
    "BatchStatusResponse",
    "CancelResponse",
    "ChannelInfoResponse",
    "CookiesResponse",
    "DeleteResponse",
    "DownloadResponse",
    "ErrorResponse",
    "FileInfo",
    "FormatInfo",
    "FormatsResponse",
    "HealthResponse",
    "JobInfo",
    "LogsResponse",
    "MetadataResponse",
    "PlaylistItemInfo",
    "PlaylistPreviewResponse",
    "ProgressInfo",
    "StatsResponse",
    "VideoMetadata",
]
