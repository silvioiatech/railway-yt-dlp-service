"""
Playlist endpoints for the Ultimate Media Downloader API.

Provides endpoints for previewing and downloading playlists with item selection
and filtering capabilities.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth import RequireAuth
from app.config import get_settings, Settings
from app.core.exceptions import MetadataExtractionError
from app.core.state import get_job_state_manager, JobStateManager
from app.models.enums import JobStatus
from app.models.requests import PlaylistDownloadRequest
from app.models.responses import (
    BatchDownloadResponse,
    JobInfo,
    PlaylistItemInfo,
    PlaylistPreviewResponse,
    ProgressInfo,
)
from app.services.queue_manager import QueueManager, get_queue_manager
from app.services.ytdlp_wrapper import YtdlpWrapper

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/playlist", tags=["playlists"])


# =========================
# Route Handlers
# =========================

@router.get(
    "/preview",
    response_model=PlaylistPreviewResponse,
    summary="Preview playlist",
    description="Preview playlist contents without downloading, with pagination support.",
    responses={
        200: {
            "description": "Playlist preview retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "url": "https://example.com/playlist",
                        "title": "Example Playlist",
                        "uploader": "Example Channel",
                        "uploader_id": "UC123456",
                        "description": "A sample playlist",
                        "total_items": 50,
                        "items": [
                            {
                                "id": "video1",
                                "title": "Video 1",
                                "url": "https://example.com/video1",
                                "duration": 300,
                                "view_count": 10000,
                                "uploader": "Example Channel",
                                "upload_date": "20251105",
                                "thumbnail": "https://example.com/thumb1.jpg",
                                "playlist_index": 1
                            }
                        ],
                        "page": 1,
                        "page_size": 20,
                        "total_pages": 3,
                        "has_next": True,
                        "has_previous": False,
                        "extractor": "generic"
                    }
                }
            }
        },
        400: {"description": "Invalid URL or parameters"},
        422: {"description": "Failed to extract playlist information"},
        500: {"description": "Internal server error"}
    }
)
async def preview_playlist(
    url: Annotated[str, Query(description="Playlist URL")],
    auth: RequireAuth,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    settings: Annotated[Settings, Depends(get_settings)] = None
):
    """
    Preview playlist without downloading.

    Retrieves playlist metadata and item list with pagination support.
    Useful for browsing playlist contents before downloading.
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

        # Extract playlist info
        logger.info(f"Extracting playlist preview for: {url}")
        info = await ytdlp.extract_info(
            url=url,
            download=False,
            timeout_sec=120
        )

        # Check if it's actually a playlist
        is_playlist = info.get('_type') == 'playlist' or 'entries' in info
        if not is_playlist:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL does not appear to be a playlist"
            )

        # Get playlist entries
        entries = info.get('entries', [])
        total_items = len(entries)

        # Calculate pagination
        total_pages = (total_items + limit - 1) // limit
        start_idx = (page - 1) * limit
        end_idx = min(start_idx + limit, total_items)

        # Get items for current page
        page_entries = entries[start_idx:end_idx]

        # Build playlist items
        items: List[PlaylistItemInfo] = []
        for idx, entry in enumerate(page_entries, start=start_idx + 1):
            if not entry:
                continue

            items.append(PlaylistItemInfo(
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

        logger.info(
            f"Playlist preview: {total_items} items, page {page}/{total_pages}"
        )

        return PlaylistPreviewResponse(
            url=url,
            title=info.get('title'),
            uploader=info.get('uploader') or info.get('channel'),
            uploader_id=info.get('uploader_id') or info.get('channel_id'),
            description=info.get('description'),
            total_items=total_items,
            items=items,
            page=page,
            page_size=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
            extractor=info.get('extractor')
        )

    except MetadataExtractionError as e:
        logger.error(f"Failed to extract playlist info: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract playlist information: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error previewing playlist: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview playlist: {str(e)}"
        )


@router.post(
    "/download",
    response_model=BatchDownloadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Download playlist",
    description="Download entire playlist or selected items as a batch job.",
    responses={
        201: {
            "description": "Playlist download job created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "batch_id": "batch_abc123",
                        "status": "queued",
                        "total_jobs": 25,
                        "completed_jobs": 0,
                        "failed_jobs": 0,
                        "running_jobs": 0,
                        "queued_jobs": 25,
                        "jobs": [],
                        "created_at": "2025-11-05T10:00:00Z",
                        "started_at": None,
                        "completed_at": None,
                        "duration_sec": None,
                        "error": None
                    }
                }
            }
        },
        400: {"description": "Invalid request parameters"},
        401: {"description": "Unauthorized - Invalid or missing API key"},
        429: {"description": "Too many requests - Rate limit exceeded"},
        500: {"description": "Internal server error"}
    }
)
async def download_playlist(
    payload: PlaylistDownloadRequest,
    auth: RequireAuth,
    queue_manager: Annotated[QueueManager, Depends(get_queue_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
    job_state_manager: Annotated[JobStateManager, Depends(get_job_state_manager)]
):
    """
    Download entire or partial playlist.

    Creates a batch download job for all items in a playlist or a
    selected subset. Returns batch job ID for tracking progress.
    """
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"

    try:
        # Initialize yt-dlp wrapper
        ytdlp = YtdlpWrapper(storage_dir=settings.STORAGE_DIR)

        # Extract playlist info to get item count
        logger.info(f"Creating playlist download job for: {payload.url}")
        info = await ytdlp.extract_info(
            url=payload.url,
            download=False,
            timeout_sec=120
        )

        # Check if it's a playlist
        is_playlist = info.get('_type') == 'playlist' or 'entries' in info
        if not is_playlist:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL does not appear to be a playlist"
            )

        # Get entries
        entries = info.get('entries', [])
        total_items = len(entries)

        # Apply item selection if specified
        selected_entries = entries
        if payload.items:
            # Parse items selection (e.g., "1-10,15,20-25")
            selected_indices = set()
            for part in payload.items.split(','):
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    selected_indices.update(range(start - 1, end))
                else:
                    selected_indices.add(int(part) - 1)

            selected_entries = [
                entries[i] for i in sorted(selected_indices)
                if 0 <= i < len(entries)
            ]
        elif payload.start or payload.end:
            # Apply start/end range
            start_idx = (payload.start - 1) if payload.start else 0
            end_idx = payload.end if payload.end else len(entries)
            selected_entries = entries[start_idx:end_idx]

        # Create batch job state
        batch_job = job_state_manager.create_job(
            request_id=batch_id,
            url=payload.url,
            payload=payload.model_dump(),
            status=JobStatus.QUEUED
        )
        batch_job.add_log(
            f"Created batch job for playlist: {info.get('title')} "
            f"({len(selected_entries)} items)"
        )

        # Create individual job states for each item
        jobs: List[JobInfo] = []
        for idx, entry in enumerate(selected_entries):
            if not entry:
                continue

            job_id = f"job_{batch_id}_{idx}"
            item_url = entry.get('url') or entry.get('webpage_url', '')

            # Create job state
            item_job = job_state_manager.create_job(
                request_id=job_id,
                url=item_url,
                payload={'parent_batch': batch_id, 'playlist_index': idx},
                status=JobStatus.QUEUED
            )

            jobs.append(JobInfo(
                job_id=job_id,
                url=item_url,
                status=JobStatus.QUEUED,
                title=entry.get('title'),
                progress=None,
                file_info=None,
                error=None,
                created_at=item_job.created_at,
                completed_at=None
            ))

        logger.info(
            f"Created playlist batch job {batch_id} with {len(jobs)} items"
        )

        # Submit individual jobs to queue manager
        for job_info in jobs:
            try:
                # Create download coroutine for this item
                from app.models.requests import DownloadRequest
                item_payload = DownloadRequest(
                    url=job_info.url,
                    format=payload.format,
                    audio_only=payload.audio_only,
                    output_template=payload.output_template
                )

                # Create download coroutine using correct signature
                download_coroutine = ytdlp.download(
                    request_id=job_info.job_id,
                    request=item_payload,
                    cookies_path=None,
                    progress_callback=None
                )

                # Submit to queue manager
                queue_manager.submit_job(
                    job_id=job_info.job_id,
                    coroutine=download_coroutine
                )

                logger.info(f"Submitted playlist item job {job_info.job_id} to queue")
            except Exception as e:
                logger.error(f"Failed to submit job {job_info.job_id}: {e}", exc_info=True)
                # Update job state to failed
                item_job = job_state_manager.get_job(job_info.job_id)
                if item_job:
                    item_job.set_failed(str(e))

        return BatchDownloadResponse(
            batch_id=batch_id,
            status=JobStatus.QUEUED,
            total_jobs=len(jobs),
            completed_jobs=0,
            failed_jobs=0,
            running_jobs=0,
            queued_jobs=len(jobs),
            jobs=jobs,
            created_at=batch_job.created_at,
            started_at=None,
            completed_at=None,
            duration_sec=None,
            error=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create playlist download job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create playlist download job: {str(e)}"
        )
