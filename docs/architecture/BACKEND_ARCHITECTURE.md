# Ultimate Media Downloader - Complete Backend Architecture

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [API Endpoints Specification](#api-endpoints-specification)
5. [Pydantic Models](#pydantic-models)
6. [yt-dlp Integration](#yt-dlp-integration)
7. [Background Job System](#background-job-system)
8. [File Management](#file-management)
9. [Security & Authentication](#security--authentication)
10. [Error Handling Strategy](#error-handling-strategy)
11. [Configuration Management](#configuration-management)
12. [Database Schema (Optional)](#database-schema-optional)
13. [Deployment Guide](#deployment-guide)

---

## Architecture Overview

### Design Principles
1. **Separation of Concerns**: Clean separation between routes, services, and utilities
2. **Async-First**: Full async/await support for I/O operations
3. **Type Safety**: Strong typing with Pydantic models throughout
4. **Scalability**: Stateless design with horizontal scaling support
5. **Observability**: Comprehensive logging, metrics, and health checks
6. **Security**: Defense in depth with multiple security layers

### Technology Stack
- **Framework**: FastAPI 0.115+
- **Runtime**: Python 3.11+
- **Media Processing**: yt-dlp (latest)
- **Validation**: Pydantic v2
- **HTTP Client**: httpx (async)
- **Metrics**: Prometheus Client
- **Rate Limiting**: slowapi
- **Storage**: Railway Volumes
- **Queue**: asyncio Queue + ThreadPoolExecutor

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                            │
│  (Web UI, Mobile App, API Clients, Webhooks)                │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/JSON
┌────────────────────────▼────────────────────────────────────┐
│                  API Gateway Layer                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Application                                 │  │
│  │  - CORS Middleware                                   │  │
│  │  - Rate Limiting Middleware                          │  │
│  │  - Authentication Middleware                         │  │
│  │  - Request Logging                                   │  │
│  └────────────────────┬─────────────────────────────────┘  │
└────────────────────────┼────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Route Layer                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Download │ │ Playlist │ │ Channel  │ │  Batch   │      │
│  │  Routes  │ │  Routes  │ │  Routes  │ │  Routes  │      │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │
└───────┼────────────┼────────────┼────────────┼─────────────┘
        │            │            │            │
┌───────▼────────────▼────────────▼────────────▼─────────────┐
│                  Service Layer                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  DownloadManager - Orchestrates download operations  │  │
│  └────────────────────┬─────────────────────────────────┘  │
│  ┌────────────────────▼─────────────────────────────────┐  │
│  │  QueueManager - Background job processing            │  │
│  └────────────────────┬─────────────────────────────────┘  │
│  ┌────────────────────▼─────────────────────────────────┐  │
│  │  YtdlpWrapper - yt-dlp Python API integration        │  │
│  └────────────────────┬─────────────────────────────────┘  │
│  ┌────────────────────▼─────────────────────────────────┐  │
│  │  FileManager - Storage and cleanup operations        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Storage Layer                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Railway Volume Storage                              │  │
│  │  - /app/data/videos/                                 │  │
│  │  - /app/data/playlists/                              │  │
│  │  - /app/data/temp/                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
railway-yt-dlp-service/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry point
│   ├── config.py                    # Configuration management
│   ├── dependencies.py              # FastAPI dependencies
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py            # Main v1 router
│   │   │   ├── download.py          # Download endpoints
│   │   │   ├── playlist.py          # Playlist endpoints
│   │   │   ├── channel.py           # Channel endpoints
│   │   │   ├── batch.py             # Batch download endpoints
│   │   │   ├── metadata.py          # Metadata endpoints
│   │   │   ├── formats.py           # Format detection
│   │   │   ├── auth.py              # Authentication/cookies
│   │   │   └── health.py            # Health/metrics
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py              # Request models
│   │   ├── responses.py             # Response models
│   │   ├── download.py              # Download-specific models
│   │   ├── playlist.py              # Playlist models
│   │   ├── channel.py               # Channel models
│   │   ├── batch.py                 # Batch models
│   │   └── metadata.py              # Metadata models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── download_manager.py      # Download orchestration
│   │   ├── ytdlp_wrapper.py         # yt-dlp integration
│   │   ├── ytdlp_options.py         # yt-dlp option builders
│   │   ├── queue_manager.py         # Job queue management
│   │   ├── file_manager.py          # File operations
│   │   ├── auth_manager.py          # Cookie/auth management
│   │   ├── webhook_service.py       # Webhook notifications
│   │   ├── progress_tracker.py      # Progress tracking
│   │   └── scheduler.py             # Auto-cleanup scheduler
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                  # API key authentication
│   │   ├── rate_limit.py            # Rate limiting
│   │   ├── error_handler.py         # Global error handling
│   │   ├── request_logger.py        # Request/response logging
│   │   └── security.py              # Security headers
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py            # Input validation
│   │   ├── formatters.py            # Output formatting
│   │   ├── path_template.py         # Path templating
│   │   ├── logger.py                # Logging configuration
│   │   └── metrics.py               # Prometheus metrics
│   │
│   └── core/
│       ├── __init__.py
│       ├── exceptions.py            # Custom exceptions
│       ├── constants.py             # Application constants
│       └── state.py                 # Application state
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest configuration
│   ├── unit/
│   │   ├── test_ytdlp_wrapper.py
│   │   ├── test_download_manager.py
│   │   └── test_validators.py
│   ├── integration/
│   │   ├── test_download_flow.py
│   │   ├── test_playlist_flow.py
│   │   └── test_batch_flow.py
│   └── e2e/
│       └── test_api.py
│
├── static/                          # Frontend files (separate)
├── logs/                            # Application logs
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── railway.toml
├── README.md
└── PRD.md
```

---

## Core Components

### 1. Main Application Entry Point

**File: `app/main.py`**

```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import CollectorRegistry

from app.api.v1.router import api_router
from app.config import get_settings
from app.core.state import AppState
from app.middleware.auth import APIKeyMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limit import setup_rate_limiting
from app.middleware.request_logger import RequestLoggingMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.services.queue_manager import QueueManager
from app.services.scheduler import FileCleanupScheduler
from app.utils.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    logger = logging.getLogger(__name__)

    # Startup
    logger.info("Starting Ultimate Media Downloader Service...")

    # Initialize application state
    app.state.app_state = AppState()

    # Initialize queue manager
    app.state.queue_manager = QueueManager(
        max_workers=settings.WORKERS,
        max_concurrent_downloads=settings.MAX_CONCURRENT_DOWNLOADS
    )
    await app.state.queue_manager.start()

    # Initialize cleanup scheduler
    app.state.cleanup_scheduler = FileCleanupScheduler(
        storage_dir=settings.STORAGE_DIR,
        default_retention_hours=settings.FILE_RETENTION_HOURS
    )
    await app.state.cleanup_scheduler.start()

    logger.info(f"Service started with {settings.WORKERS} workers")

    yield

    # Shutdown
    logger.info("Shutting down service...")

    await app.state.queue_manager.shutdown()
    await app.state.cleanup_scheduler.shutdown()

    logger.info("Service shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title="Ultimate Media Downloader API",
        description="Production-ready yt-dlp service with comprehensive features",
        version="3.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if not settings.DISABLE_DOCS else None,
        redoc_url="/api/redoc" if not settings.DISABLE_DOCS else None,
        openapi_url="/api/openapi.json" if not settings.DISABLE_DOCS else None,
    )

    # Add middleware (order matters - first added is outermost)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # CORS
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Rate limiting
    setup_rate_limiting(app)

    # Include routers
    app.include_router(api_router, prefix="/api/v1")

    # Mount static files if available
    if settings.STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(settings.STATIC_DIR), html=True), name="static")

    return app


app = create_app()
```

---

## API Endpoints Specification

### Complete Endpoint List

#### Download Endpoints

**1. POST /api/v1/download**
- Create single video download job
- Request: `DownloadRequest`
- Response: `DownloadResponse`
- Rate Limit: 2/sec per IP, 10/sec per API key

**2. GET /api/v1/download/{request_id}**
- Get download job status
- Response: `DownloadResponse`

**3. GET /api/v1/download/{request_id}/logs**
- Get download job logs
- Response: `LogsResponse`

**4. DELETE /api/v1/download/{request_id}**
- Cancel active download
- Response: `CancelResponse`

#### Format Detection

**5. GET /api/v1/formats**
- Get available formats for URL
- Query params: `url`, `cookies` (optional)
- Response: `FormatsResponse`

#### Playlist Endpoints

**6. GET /api/v1/playlist/preview**
- Preview playlist without downloading
- Query params: `url`, `page`, `limit`
- Response: `PlaylistPreviewResponse`

**7. POST /api/v1/playlist/download**
- Download entire or partial playlist
- Request: `PlaylistDownloadRequest`
- Response: `BatchDownloadResponse`

#### Channel Endpoints

**8. GET /api/v1/channel/info**
- Get channel information
- Query params: `url`, `date_after`, `date_before`, `min_duration`, `max_duration`
- Response: `ChannelInfoResponse`

**9. POST /api/v1/channel/download**
- Download channel videos with filters
- Request: `ChannelDownloadRequest`
- Response: `BatchDownloadResponse`

#### Batch Operations

**10. POST /api/v1/batch/download**
- Batch download multiple URLs
- Request: `BatchDownloadRequest`
- Response: `BatchDownloadResponse`

**11. GET /api/v1/batch/{batch_id}**
- Get batch download status
- Response: `BatchStatusResponse`

**12. DELETE /api/v1/batch/{batch_id}**
- Cancel batch download
- Response: `CancelResponse`

#### Metadata

**13. GET /api/v1/metadata**
- Extract metadata without downloading
- Query params: `url`, `cookies` (optional)
- Response: `MetadataResponse`

#### Authentication

**14. POST /api/v1/auth/cookies**
- Upload cookies for authentication
- Request: `CookiesUploadRequest`
- Response: `CookiesResponse`

**15. DELETE /api/v1/auth/cookies/{cookie_id}**
- Delete stored cookies
- Response: `DeleteResponse`

#### Health & Metrics

**16. GET /api/v1/health**
- Health check endpoint
- Response: `HealthResponse`

**17. GET /api/v1/metrics**
- Prometheus metrics
- Response: Prometheus format

**18. GET /api/v1/stats**
- Service statistics
- Response: `StatsResponse`

---

## Pydantic Models

### Request Models

**File: `app/models/requests.py`**

```python
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, HttpUrl
from urllib.parse import urlparse


class QualityPreset(str, Enum):
    """Quality preset options."""
    BEST = "best"
    BEST_VIDEO = "bestvideo+bestaudio"
    QUALITY_4K = "bestvideo[height<=2160]+bestaudio/best"
    QUALITY_1080P = "bestvideo[height<=1080]+bestaudio/best"
    QUALITY_720P = "bestvideo[height<=720]+bestaudio/best"
    QUALITY_480P = "bestvideo[height<=480]+bestaudio/best"
    QUALITY_360P = "bestvideo[height<=360]+bestaudio/best"
    AUDIO_ONLY = "bestaudio/best"


class AudioFormat(str, Enum):
    """Audio format options."""
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"
    WAV = "wav"
    OPUS = "opus"
    AAC = "aac"


class VideoFormat(str, Enum):
    """Video format options."""
    MP4 = "mp4"
    MKV = "mkv"
    WEBM = "webm"
    AVI = "avi"
    MOV = "mov"


class SubtitleFormat(str, Enum):
    """Subtitle format options."""
    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"


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
    video_format: Optional[VideoFormat] = Field(VideoFormat.MP4)
    audio_only: bool = Field(False)
    audio_format: Optional[AudioFormat] = Field(AudioFormat.MP3)

    # Subtitle options
    download_subtitles: bool = Field(False)
    subtitle_languages: Optional[List[str]] = Field(["en"])

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

    # Webhook
    webhook_url: Optional[HttpUrl] = Field(None)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
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
    video_format: Optional[VideoFormat] = Field(VideoFormat.MP4)

    # Limits
    max_downloads: Optional[int] = Field(None, ge=1, le=1000, description="Max videos to download")

    # Path template
    path_template: Optional[str] = Field(
        "channels/{uploader}/{upload_date}-{title}.{ext}"
    )

    # Authentication
    cookies_id: Optional[str] = Field(None)

    # Webhook
    webhook_url: Optional[HttpUrl] = Field(None)


class BatchDownloadRequest(BaseModel):
    """Request model for batch downloads."""

    urls: List[str] = Field(..., min_length=1, max_length=100, description="List of URLs")

    # Download options
    quality: Optional[QualityPreset] = Field(QualityPreset.BEST)
    video_format: Optional[VideoFormat] = Field(VideoFormat.MP4)
    audio_only: bool = Field(False)

    # Concurrency
    concurrent_limit: int = Field(3, ge=1, le=10, description="Max concurrent downloads")

    # Error handling
    stop_on_error: bool = Field(False, description="Stop batch on first error")

    # Authentication
    cookies_id: Optional[str] = Field(None)

    # Webhook
    webhook_url: Optional[HttpUrl] = Field(None)

    @field_validator('urls')
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        """Validate all URLs."""
        validated = []
        for url in v:
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid URL: {url}")
            validated.append(url)
        return validated


class CookiesUploadRequest(BaseModel):
    """Request model for cookies upload."""

    cookies: str = Field(..., description="Cookies in Netscape format")
    name: Optional[str] = Field("default", description="Cookie set name")
    browser: Optional[str] = Field(
        None,
        description="Auto-extract from browser (chrome, firefox, edge, safari)"
    )

    @field_validator('cookies')
    @classmethod
    def validate_cookies(cls, v: str) -> str:
        """Validate cookies format."""
        if not v.strip():
            raise ValueError("Cookies cannot be empty")
        # Basic Netscape format check
        if not any(line.startswith('#') or '\t' in line for line in v.split('\n')):
            raise ValueError("Invalid Netscape cookies format")
        return v
```

---

## yt-dlp Integration

### YoutubeDL Wrapper Service

**File: `app/services/ytdlp_wrapper.py`**

```python
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import yt_dlp

from app.core.exceptions import DownloadError, MetadataExtractionError
from app.models.requests import (
    DownloadRequest,
    QualityPreset,
    AudioFormat,
    VideoFormat,
    SubtitleFormat
)
from app.services.ytdlp_options import YtdlpOptionsBuilder
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ProgressTracker:
    """Track download progress with callbacks."""

    def __init__(self, request_id: str, callback: Optional[Callable] = None):
        self.request_id = request_id
        self.callback = callback
        self.status = "idle"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed = 0
        self.eta = 0
        self.percent = 0.0

    def __call__(self, d: Dict[str, Any]):
        """yt-dlp progress hook."""
        self.status = d.get('status', 'downloading')

        if self.status == 'downloading':
            self.downloaded_bytes = d.get('downloaded_bytes', 0)
            self.total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            self.speed = d.get('speed', 0)
            self.eta = d.get('eta', 0)

            if self.total_bytes > 0:
                self.percent = (self.downloaded_bytes / self.total_bytes) * 100

            # Call callback if provided
            if self.callback:
                self.callback({
                    'request_id': self.request_id,
                    'status': self.status,
                    'downloaded_bytes': self.downloaded_bytes,
                    'total_bytes': self.total_bytes,
                    'speed': self.speed,
                    'eta': self.eta,
                    'percent': self.percent
                })

        elif self.status == 'finished':
            self.percent = 100.0
            if self.callback:
                self.callback({
                    'request_id': self.request_id,
                    'status': 'finished',
                    'percent': 100.0
                })


class YtdlpWrapper:
    """Wrapper for yt-dlp with async support and progress tracking."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def extract_info(
        self,
        url: str,
        download: bool = False,
        cookies_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Extract video/playlist information without downloading.

        Args:
            url: Video or playlist URL
            download: Whether to download the video
            cookies_path: Path to cookies file

        Returns:
            Dictionary with video/playlist information

        Raises:
            MetadataExtractionError: If extraction fails
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False if download else 'in_playlist',
            'skip_download': not download,
        }

        if cookies_path:
            ydl_opts['cookiefile'] = str(cookies_path)

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._extract_info_sync,
                url,
                ydl_opts
            )
            return result
        except Exception as e:
            logger.error(f"Metadata extraction failed for {url}: {e}")
            raise MetadataExtractionError(f"Failed to extract metadata: {str(e)}")

    def _extract_info_sync(self, url: str, opts: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous metadata extraction."""
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return ydl.sanitize_info(info)

    async def get_formats(
        self,
        url: str,
        cookies_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Get available formats for a URL.

        Args:
            url: Video URL
            cookies_path: Path to cookies file

        Returns:
            Dictionary with formats and recommendations
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
            }

            if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                combined_formats.append(format_info)
            elif fmt.get('vcodec') != 'none':
                video_formats.append(format_info)
            elif fmt.get('acodec') != 'none':
                audio_formats.append(format_info)

        return {
            'formats': {
                'combined': combined_formats,
                'video_only': video_formats,
                'audio_only': audio_formats,
            },
            'best_video_format': self._find_best_format(video_formats),
            'best_audio_format': self._find_best_format(audio_formats),
            'recommended': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'title': info.get('title'),
            'duration': info.get('duration'),
            'thumbnail': info.get('thumbnail'),
        }

    def _find_best_format(self, formats: List[Dict]) -> Optional[str]:
        """Find best format ID from a list of formats."""
        if not formats:
            return None

        # Sort by filesize (larger is better quality usually)
        sorted_formats = sorted(
            formats,
            key=lambda x: x.get('filesize') or 0,
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
            Dictionary with download results

        Raises:
            DownloadError: If download fails
        """
        # Build yt-dlp options
        options_builder = YtdlpOptionsBuilder(self.storage_dir)
        ydl_opts = options_builder.build_from_request(request, request_id)

        # Add cookies if provided
        if cookies_path:
            ydl_opts['cookiefile'] = str(cookies_path)

        # Add progress hook
        progress_tracker = ProgressTracker(request_id, progress_callback)
        ydl_opts['progress_hooks'] = [progress_tracker]

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._download_sync,
                request.url,
                ydl_opts
            )

            return {
                'success': True,
                'file_path': result.get('file_path'),
                'title': result.get('title'),
                'duration': result.get('duration'),
                'filesize': result.get('filesize'),
                'format': result.get('format'),
            }

        except Exception as e:
            logger.error(f"Download failed for {request_id}: {e}")
            raise DownloadError(f"Download failed: {str(e)}")

    def _download_sync(self, url: str, opts: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous download execution."""
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            sanitized = ydl.sanitize_info(info)

            # Get the actual file path
            if 'requested_downloads' in sanitized and sanitized['requested_downloads']:
                file_path = sanitized['requested_downloads'][0].get('filepath')
            else:
                file_path = ydl.prepare_filename(info)

            return {
                'file_path': file_path,
                'title': sanitized.get('title'),
                'duration': sanitized.get('duration'),
                'filesize': sanitized.get('filesize'),
                'format': sanitized.get('format'),
            }

    async def download_playlist(
        self,
        request_id: str,
        request: 'PlaylistDownloadRequest',
        cookies_path: Optional[Path] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Download playlist with filtering and selection."""
        # Build options for playlist
        options_builder = YtdlpOptionsBuilder(self.storage_dir)
        ydl_opts = options_builder.build_playlist_options(request, request_id)

        if cookies_path:
            ydl_opts['cookiefile'] = str(cookies_path)

        # Progress tracking
        progress_tracker = ProgressTracker(request_id, progress_callback)
        ydl_opts['progress_hooks'] = [progress_tracker]

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._download_sync,
                request.url,
                ydl_opts
            )

            return result

        except Exception as e:
            logger.error(f"Playlist download failed for {request_id}: {e}")
            raise DownloadError(f"Playlist download failed: {str(e)}")
```

### yt-dlp Options Builder

**File: `app/services/ytdlp_options.py`**

```python
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.requests import (
    DownloadRequest,
    PlaylistDownloadRequest,
    ChannelDownloadRequest,
    QualityPreset,
    AudioFormat,
    VideoFormat,
    SubtitleFormat
)
from app.utils.path_template import PathTemplateExpander


class YtdlpOptionsBuilder:
    """Build yt-dlp options dictionaries from request models."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.template_expander = PathTemplateExpander()

    def build_from_request(
        self,
        request: DownloadRequest,
        request_id: str
    ) -> Dict[str, Any]:
        """Build complete yt-dlp options from DownloadRequest."""

        # Base options
        opts = {
            'quiet': False,
            'no_warnings': False,
            'verbose': True,
            'outtmpl': str(self.storage_dir / request.path_template),
            'restrictfilenames': False,
            'windowsfilenames': True,  # Safe filenames for all platforms
            'no_overwrites': True,
            'continue': True,
            'no_part': False,
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
        opts['postprocessors'] = self._build_postprocessors(request)

        return opts

    def _build_format_string(self, request: DownloadRequest) -> str:
        """Build yt-dlp format selection string."""

        # Custom format takes precedence
        if request.custom_format:
            return request.custom_format

        # Audio-only extraction
        if request.audio_only:
            return 'bestaudio/best'

        # Use quality preset
        if request.quality:
            return request.quality.value

        return 'bestvideo+bestaudio/best'

    def _build_subtitle_options(self, request: DownloadRequest) -> Dict[str, Any]:
        """Build subtitle-related options."""
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
        """Build thumbnail-related options."""
        opts = {}

        if request.write_thumbnail:
            opts['writethumbnail'] = True

        if request.embed_thumbnail:
            opts['writethumbnail'] = True
            opts['embedthumbnail'] = True

        return opts

    def _build_metadata_options(self, request: DownloadRequest) -> Dict[str, Any]:
        """Build metadata-related options."""
        opts = {}

        if request.write_info_json:
            opts['writeinfojson'] = True

        if request.embed_metadata:
            opts['add_metadata'] = True

        return opts

    def _build_postprocessors(self, request: DownloadRequest) -> List[Dict[str, Any]]:
        """Build list of post-processors."""
        postprocessors = []

        # Audio extraction and conversion
        if request.audio_only:
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': request.audio_format.value if request.audio_format else 'mp3',
                'preferredquality': request.audio_quality or '192',
            })

        # Thumbnail embedding
        if request.embed_thumbnail:
            postprocessors.append({
                'key': 'EmbedThumbnail',
            })
            # Thumbnail format conversion for compatibility
            postprocessors.append({
                'key': 'FFmpegThumbnailsConvertor',
                'format': 'jpg',
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
            })

        # Metadata embedding
        if request.embed_metadata:
            postprocessors.append({
                'key': 'FFmpegMetadata',
            })

        return postprocessors

    def build_playlist_options(
        self,
        request: PlaylistDownloadRequest,
        request_id: str
    ) -> Dict[str, Any]:
        """Build options for playlist downloads."""

        # Start with base download options
        base_request = DownloadRequest(
            url=request.url,
            quality=request.quality,
            video_format=request.video_format,
            audio_only=request.audio_only,
            audio_format=request.audio_format,
            download_subtitles=request.download_subtitles,
            subtitle_languages=request.subtitle_languages,
        )

        opts = self.build_from_request(base_request, request_id)

        # Playlist-specific options
        opts['outtmpl'] = str(self.storage_dir / request.path_template)
        opts['ignoreerrors'] = request.ignore_errors
        opts['noplaylist'] = False

        # Item selection
        if request.items:
            opts['playlist_items'] = request.items
        elif request.start or request.end:
            start = request.start or 1
            end = request.end or 'end'
            opts['playlist_items'] = f"{start}:{end}"

        # Skip downloaded
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
        """Build options for channel downloads."""

        # Start with base options
        base_request = DownloadRequest(
            url=request.url,
            quality=request.quality,
            video_format=request.video_format,
        )

        opts = self.build_from_request(base_request, request_id)

        # Channel-specific options
        opts['outtmpl'] = str(self.storage_dir / request.path_template)

        # Date filters
        if request.date_after:
            opts['dateafter'] = request.date_after
        if request.date_before:
            opts['datebefore'] = request.date_before

        # Duration filters
        if request.min_duration:
            opts['match_filter'] = f"duration >= {request.min_duration}"
        if request.max_duration:
            if 'match_filter' in opts:
                opts['match_filter'] += f" & duration <= {request.max_duration}"
            else:
                opts['match_filter'] = f"duration <= {request.max_duration}"

        # View count filters
        if request.min_views:
            filter_expr = f"view_count >= {request.min_views}"
            if 'match_filter' in opts:
                opts['match_filter'] += f" & {filter_expr}"
            else:
                opts['match_filter'] = filter_expr

        if request.max_views:
            filter_expr = f"view_count <= {request.max_views}"
            if 'match_filter' in opts:
                opts['match_filter'] += f" & {filter_expr}"
            else:
                opts['match_filter'] = filter_expr

        # Max downloads
        if request.max_downloads:
            opts['max_downloads'] = request.max_downloads

        # Sort order
        if request.sort_by:
            opts['playlistsort'] = request.sort_by

        return opts
```

This architecture continues with many more components. Would you like me to continue with:

1. Background Job System (QueueManager, JobProcessor)
2. Complete Response Models
3. All Route Handlers
4. File Management & Cleanup
5. Security & Middleware
6. Configuration Management
7. Database Schema
8. Deployment Configuration

Let me know which sections you'd like me to detail next!
