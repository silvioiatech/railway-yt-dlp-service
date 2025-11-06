"""
Metadata and format detection endpoints for the Ultimate Media Downloader API.

Provides endpoints for extracting video metadata and discovering available formats
without downloading the content.
"""
import logging
from datetime import datetime, timezone
from typing import Annotated, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth import RequireAuth
from app.config import get_settings, Settings
from app.core.exceptions import MetadataExtractionError
from app.models.responses import (
    FormatInfo,
    FormatsResponse,
    MetadataResponse,
    VideoMetadata,
)
from app.services.ytdlp_wrapper import YtdlpWrapper

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/metadata", tags=["metadata"])


# =========================
# Route Handlers
# =========================

@router.get(
    "/formats",
    response_model=FormatsResponse,
    summary="Get available formats",
    description="Get all available download formats for a video URL without downloading.",
    responses={
        200: {
            "description": "Available formats retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "url": "https://example.com/video",
                        "title": "Example Video",
                        "duration": 300,
                        "thumbnail": "https://example.com/thumb.jpg",
                        "formats": {
                            "combined": [
                                {
                                    "format_id": "22",
                                    "ext": "mp4",
                                    "resolution": "1280x720",
                                    "fps": 30.0,
                                    "vcodec": "avc1.64001F",
                                    "acodec": "mp4a.40.2",
                                    "filesize": 52428800,
                                    "quality": 1
                                }
                            ],
                            "video_only": [],
                            "audio_only": []
                        },
                        "best_video_format": "137",
                        "best_audio_format": "140",
                        "recommended_format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
                        "extractor": "generic"
                    }
                }
            }
        },
        400: {"description": "Invalid URL"},
        422: {"description": "Failed to extract formats"},
        500: {"description": "Internal server error"}
    }
)
async def get_formats(
    url: Annotated[str, Query(description="Video URL to analyze")],
    auth: RequireAuth,
    cookies: Annotated[Optional[str], Query(description="Cookies file ID for authentication")] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None
):
    """
    Get available formats for a URL.

    Extracts all available video and audio formats without downloading the content.
    Useful for determining quality options before initiating a download.
    """
    if not url or not url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL parameter is required"
        )

    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://"
        )

    try:
        # Initialize yt-dlp wrapper
        ytdlp = YtdlpWrapper(storage_dir=settings.STORAGE_DIR)

        # Resolve cookies path if provided
        cookies_path = None
        if cookies:
            cookies_path = settings.STORAGE_DIR / "cookies" / f"{cookies}.txt"
            if not cookies_path.exists():
                logger.warning(f"Cookies file not found: {cookies_path}")
                cookies_path = None

        # Extract info without downloading
        logger.info(f"Extracting formats for URL: {url}")
        info = await ytdlp.extract_info(
            url=url,
            download=False,
            cookies_path=cookies_path,
            timeout_sec=60
        )

        # Categorize formats
        formats_by_type: Dict[str, List[FormatInfo]] = {
            "combined": [],
            "video_only": [],
            "audio_only": []
        }

        formats = info.get('formats', [])
        for fmt in formats:
            format_info = FormatInfo(
                format_id=fmt.get('format_id', 'unknown'),
                ext=fmt.get('ext', 'unknown'),
                resolution=fmt.get('resolution'),
                fps=fmt.get('fps'),
                vcodec=fmt.get('vcodec'),
                acodec=fmt.get('acodec'),
                filesize=fmt.get('filesize'),
                tbr=fmt.get('tbr'),
                vbr=fmt.get('vbr'),
                abr=fmt.get('abr'),
                width=fmt.get('width'),
                height=fmt.get('height'),
                format_note=fmt.get('format_note'),
                quality=fmt.get('quality')
            )

            # Categorize format
            has_video = fmt.get('vcodec') and fmt.get('vcodec') != 'none'
            has_audio = fmt.get('acodec') and fmt.get('acodec') != 'none'

            if has_video and has_audio:
                formats_by_type["combined"].append(format_info)
            elif has_video:
                formats_by_type["video_only"].append(format_info)
            elif has_audio:
                formats_by_type["audio_only"].append(format_info)

        # Determine best formats
        best_video = None
        best_audio = None

        # Find best video format (highest resolution)
        video_formats = formats_by_type["video_only"] + formats_by_type["combined"]
        if video_formats:
            best_video_fmt = max(
                video_formats,
                key=lambda f: (f.height or 0, f.width or 0),
                default=None
            )
            if best_video_fmt:
                best_video = best_video_fmt.format_id

        # Find best audio format (highest bitrate)
        audio_formats = formats_by_type["audio_only"] + formats_by_type["combined"]
        if audio_formats:
            best_audio_fmt = max(
                audio_formats,
                key=lambda f: f.abr or 0,
                default=None
            )
            if best_audio_fmt:
                best_audio = best_audio_fmt.format_id

        # Build recommended format string
        recommended = "bestvideo+bestaudio/best"
        if best_video and best_audio:
            recommended = f"{best_video}+{best_audio}/best"

        logger.info(f"Found {len(formats)} formats for URL: {url}")

        return FormatsResponse(
            url=url,
            title=info.get('title'),
            duration=info.get('duration'),
            thumbnail=info.get('thumbnail'),
            formats=formats_by_type,
            best_video_format=best_video,
            best_audio_format=best_audio,
            recommended_format=recommended,
            extractor=info.get('extractor')
        )

    except MetadataExtractionError as e:
        logger.error(f"Failed to extract formats: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract formats: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error extracting formats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract formats: {str(e)}"
        )


@router.get(
    "/metadata",
    response_model=MetadataResponse,
    summary="Extract metadata",
    description="Extract video metadata without downloading the content.",
    responses={
        200: {
            "description": "Metadata extracted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "url": "https://example.com/video",
                        "metadata": {
                            "title": "Example Video",
                            "description": "A sample video",
                            "uploader": "Example Channel",
                            "uploader_id": "UC123456",
                            "upload_date": "20251105",
                            "duration": 300,
                            "view_count": 1000000,
                            "like_count": 50000,
                            "width": 1920,
                            "height": 1080,
                            "fps": 30.0,
                            "vcodec": "avc1.640028",
                            "acodec": "mp4a.40.2",
                            "thumbnail": "https://example.com/thumb.jpg",
                            "webpage_url": "https://example.com/video"
                        },
                        "formats_available": 24,
                        "is_playlist": False,
                        "playlist_count": None,
                        "subtitles_available": ["en", "es", "fr"],
                        "extractor": "generic",
                        "extracted_at": "2025-11-05T10:00:00Z"
                    }
                }
            }
        },
        400: {"description": "Invalid URL"},
        422: {"description": "Failed to extract metadata"},
        500: {"description": "Internal server error"}
    }
)
async def get_metadata(
    url: Annotated[str, Query(description="Video URL to analyze")],
    auth: RequireAuth,
    cookies: Annotated[Optional[str], Query(description="Cookies file ID for authentication")] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None
):
    """
    Extract metadata without downloading.

    Retrieves comprehensive metadata about a video including title, description,
    duration, view count, available formats, and subtitles without downloading
    the actual content.
    """
    if not url or not url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL parameter is required"
        )

    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://"
        )

    try:
        # Initialize yt-dlp wrapper
        ytdlp = YtdlpWrapper(storage_dir=settings.STORAGE_DIR)

        # Resolve cookies path if provided
        cookies_path = None
        if cookies:
            cookies_path = settings.STORAGE_DIR / "cookies" / f"{cookies}.txt"
            if not cookies_path.exists():
                logger.warning(f"Cookies file not found: {cookies_path}")
                cookies_path = None

        # Extract info without downloading
        logger.info(f"Extracting metadata for URL: {url}")
        info = await ytdlp.extract_info(
            url=url,
            download=False,
            cookies_path=cookies_path,
            timeout_sec=60
        )

        # Check if it's a playlist
        is_playlist = info.get('_type') == 'playlist' or 'entries' in info
        playlist_count = len(info.get('entries', [])) if is_playlist else None

        # Extract metadata
        metadata = VideoMetadata(
            title=info.get('title'),
            description=info.get('description'),
            uploader=info.get('uploader'),
            uploader_id=info.get('uploader_id') or info.get('channel_id'),
            upload_date=info.get('upload_date'),
            duration=info.get('duration'),
            view_count=info.get('view_count'),
            like_count=info.get('like_count'),
            comment_count=info.get('comment_count'),
            width=info.get('width'),
            height=info.get('height'),
            fps=info.get('fps'),
            vcodec=info.get('vcodec'),
            acodec=info.get('acodec'),
            thumbnail=info.get('thumbnail'),
            webpage_url=info.get('webpage_url') or url,
            extractor=info.get('extractor'),
            playlist=info.get('playlist'),
            playlist_index=info.get('playlist_index'),
            categories=info.get('categories'),
            tags=info.get('tags')
        )

        # Get available subtitle languages
        subtitles = info.get('subtitles', {})
        auto_subs = info.get('automatic_captions', {})
        all_subs = set(subtitles.keys()) | set(auto_subs.keys())
        subtitles_available = sorted(all_subs)

        # Count formats
        formats_available = len(info.get('formats', []))

        logger.info(
            f"Extracted metadata for '{metadata.title}' - "
            f"{formats_available} formats, {len(subtitles_available)} subtitle languages"
        )

        return MetadataResponse(
            url=url,
            metadata=metadata,
            formats_available=formats_available,
            is_playlist=is_playlist,
            playlist_count=playlist_count,
            subtitles_available=subtitles_available,
            extractor=info.get('extractor'),
            extracted_at=datetime.now(timezone.utc)
        )

    except MetadataExtractionError as e:
        logger.error(f"Failed to extract metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract metadata: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error extracting metadata: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract metadata: {str(e)}"
        )
