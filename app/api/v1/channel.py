"""
Channel endpoints for the Ultimate Media Downloader API.

Provides endpoints for browsing channel videos with filters and
downloading entire channels or filtered subsets.
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
from app.models.requests import ChannelDownloadRequest, DownloadRequest
from app.models.responses import (
    BatchDownloadResponse,
    ChannelInfoResponse,
    JobInfo,
)
from app.services.channel_service import ChannelService, get_channel_service
from app.services.queue_manager import QueueManager, get_queue_manager
from app.services.ytdlp_wrapper import YtdlpWrapper

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/channel", tags=["channels"])


# =========================
# Route Handlers
# =========================

@router.get(
    "/info",
    response_model=ChannelInfoResponse,
    summary="Get channel information",
    description="Retrieve channel metadata and video list with filtering and pagination support.",
    responses={
        200: {
            "description": "Channel information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "url": "https://youtube.com/@example",
                        "channel_id": "UC123456",
                        "channel_name": "Example Channel",
                        "description": "An example channel",
                        "subscriber_count": 1000000,
                        "video_count": 500,
                        "filtered_video_count": 50,
                        "videos": [
                            {
                                "id": "video1",
                                "title": "Example Video",
                                "url": "https://youtube.com/watch?v=video1",
                                "duration": 600,
                                "view_count": 50000,
                                "uploader": "Example Channel",
                                "upload_date": "20251105",
                                "thumbnail": "https://example.com/thumb.jpg",
                                "playlist_index": 1
                            }
                        ],
                        "page": 1,
                        "page_size": 20,
                        "total_pages": 3,
                        "has_next": True,
                        "has_previous": False,
                        "filters_applied": {
                            "date_after": "20250101",
                            "min_duration": 300
                        },
                        "extractor": "youtube"
                    }
                }
            }
        },
        400: {"description": "Invalid URL or parameters"},
        401: {"description": "Unauthorized - Invalid or missing API key"},
        422: {"description": "Failed to extract channel information"},
        500: {"description": "Internal server error"}
    }
)
async def get_channel_info(
    url: Annotated[str, Query(description="Channel URL")],
    auth: RequireAuth,
    date_after: Annotated[
        Optional[str],
        Query(description="Filter videos after this date (YYYYMMDD)")
    ] = None,
    date_before: Annotated[
        Optional[str],
        Query(description="Filter videos before this date (YYYYMMDD)")
    ] = None,
    min_duration: Annotated[
        Optional[int],
        Query(ge=0, description="Minimum video duration in seconds")
    ] = None,
    max_duration: Annotated[
        Optional[int],
        Query(ge=0, description="Maximum video duration in seconds")
    ] = None,
    min_views: Annotated[
        Optional[int],
        Query(ge=0, description="Minimum view count")
    ] = None,
    max_views: Annotated[
        Optional[int],
        Query(ge=0, description="Maximum view count")
    ] = None,
    sort_by: Annotated[
        str,
        Query(description="Sort field (upload_date, view_count, duration, title)")
    ] = "upload_date",
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Items per page")
    ] = 20,
    channel_service: Annotated[ChannelService, Depends(get_channel_service)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None
):
    """
    Get channel information with filtering.

    Retrieves channel metadata and a filtered, paginated list of videos.
    This endpoint does NOT download anything - it's for browsing channel
    contents before downloading.

    Filters:
    - Date range: date_after and date_before (YYYYMMDD format)
    - Duration: min_duration and max_duration (seconds)
    - Views: min_views and max_views
    - Sort: upload_date (default), view_count, duration, or title

    Example:
        GET /api/v1/channel/info?url=https://youtube.com/@example&date_after=20250101&min_duration=300&sort_by=view_count
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

    # Validate sort_by
    valid_sorts = ['upload_date', 'view_count', 'duration', 'title']
    if sort_by not in valid_sorts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"sort_by must be one of: {', '.join(valid_sorts)}"
        )

    # Validate date range
    if date_after and date_before and date_after > date_before:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_after must be before or equal to date_before"
        )

    # Validate duration range
    if (min_duration is not None and max_duration is not None and
            min_duration > max_duration):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_duration must be less than or equal to max_duration"
        )

    # Validate views range
    if (min_views is not None and max_views is not None and
            min_views > max_views):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_views must be less than or equal to max_views"
        )

    try:
        logger.info(f"Getting channel info for: {url} (page {page})")

        channel_info = await channel_service.get_channel_info(
            url=url,
            date_after=date_after,
            date_before=date_before,
            min_duration=min_duration,
            max_duration=max_duration,
            min_views=min_views,
            max_views=max_views,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
            cookies_path=None,  # TODO: Add cookie support via cookies_id
            timeout_sec=120
        )

        logger.info(
            f"Channel info retrieved: {channel_info.filtered_video_count} videos, "
            f"page {page}/{channel_info.total_pages}"
        )

        return channel_info

    except MetadataExtractionError as e:
        logger.error(f"Failed to extract channel info: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract channel information: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting channel info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get channel information: {str(e)}"
        )


@router.post(
    "/download",
    response_model=BatchDownloadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Download channel videos",
    description="Download channel videos with filtering as a batch job.",
    responses={
        201: {
            "description": "Channel download job created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "batch_id": "batch_abc123",
                        "status": "queued",
                        "total_jobs": 50,
                        "completed_jobs": 0,
                        "failed_jobs": 0,
                        "running_jobs": 0,
                        "queued_jobs": 50,
                        "jobs": [],
                        "created_at": "2025-11-06T10:00:00Z",
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
        422: {"description": "Failed to extract channel information"},
        429: {"description": "Too many requests - Rate limit exceeded"},
        500: {"description": "Internal server error"}
    }
)
async def download_channel(
    payload: ChannelDownloadRequest,
    auth: RequireAuth,
    queue_manager: Annotated[QueueManager, Depends(get_queue_manager)],
    channel_service: Annotated[ChannelService, Depends(get_channel_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    job_state_manager: Annotated[JobStateManager, Depends(get_job_state_manager)]
):
    """
    Download filtered channel videos.

    Creates a batch download job for channel videos matching the specified
    filters. This allows downloading specific videos from a channel based on:
    - Upload date range
    - Duration range
    - View count range
    - Maximum number of videos

    The videos are sorted according to sort_by parameter and then limited
    by max_downloads if specified.

    Example:
        POST /api/v1/channel/download
        {
            "url": "https://youtube.com/@example",
            "date_after": "20250101",
            "min_duration": 300,
            "max_downloads": 50,
            "sort_by": "view_count",
            "quality": "1080p"
        }
    """
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"

    try:
        logger.info(f"Creating channel download job for: {payload.url}")

        # Prepare channel download (extract and filter videos)
        channel_data = await channel_service.prepare_channel_download(
            request=payload,
            cookies_path=None  # TODO: Add cookie support via cookies_id
        )

        filtered_entries = channel_data['entries']
        channel_name = channel_data['channel_name']

        if not filtered_entries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No videos match the specified filters"
            )

        logger.info(
            f"Channel '{channel_name}': {len(filtered_entries)} videos selected "
            f"from {channel_data['total_videos']} total"
        )

        # Create batch job state
        batch_job = job_state_manager.create_job(
            request_id=batch_id,
            url=payload.url,
            payload=payload.model_dump(),
            status=JobStatus.QUEUED
        )
        batch_job.add_log(
            f"Created batch job for channel: {channel_name} "
            f"({len(filtered_entries)} videos)"
        )

        # Create individual job states for each video
        jobs: List[JobInfo] = []
        ytdlp = YtdlpWrapper(storage_dir=settings.STORAGE_DIR)

        for idx, entry in enumerate(filtered_entries):
            if not entry:
                continue

            job_id = f"job_{batch_id}_{idx}"
            video_url = entry.get('url') or entry.get('webpage_url', '')

            if not video_url:
                logger.warning(f"Skipping entry {idx}: no URL found")
                continue

            # Create job state
            item_job = job_state_manager.create_job(
                request_id=job_id,
                url=video_url,
                payload={
                    'parent_batch': batch_id,
                    'channel_index': idx,
                    'channel_name': channel_name
                },
                status=JobStatus.QUEUED
            )

            jobs.append(JobInfo(
                job_id=job_id,
                url=video_url,
                status=JobStatus.QUEUED,
                title=entry.get('title'),
                progress=None,
                file_info=None,
                error=None,
                created_at=item_job.created_at,
                completed_at=None
            ))

        logger.info(
            f"Created channel batch job {batch_id} with {len(jobs)} videos"
        )

        # Submit individual jobs to queue manager
        for job_info in jobs:
            try:
                # Create download request for this video
                item_payload = DownloadRequest(
                    url=job_info.url,
                    quality=payload.quality,
                    custom_format=payload.custom_format,
                    video_format=payload.video_format,
                    audio_only=payload.audio_only,
                    audio_format=payload.audio_format,
                    audio_quality=payload.audio_quality,
                    download_subtitles=payload.download_subtitles,
                    subtitle_languages=payload.subtitle_languages,
                    subtitle_format=payload.subtitle_format,
                    embed_subtitles=payload.embed_subtitles,
                    write_thumbnail=payload.write_thumbnail,
                    embed_thumbnail=payload.embed_thumbnail,
                    embed_metadata=payload.embed_metadata,
                    write_info_json=payload.write_info_json,
                    path_template=payload.path_template,
                    cookies_id=payload.cookies_id,
                    timeout_sec=payload.timeout_sec
                )

                # Create download coroutine
                from app.api.v1.download import process_download_job

                download_coroutine = process_download_job(
                    request_id=job_info.job_id,
                    payload=item_payload,
                    job_state_manager=job_state_manager,
                    settings=settings
                )

                # Submit to queue manager
                queue_manager.submit_job(
                    job_id=job_info.job_id,
                    coroutine=download_coroutine
                )

                logger.debug(f"Submitted channel video job {job_info.job_id} to queue")

            except Exception as e:
                logger.error(
                    f"Failed to submit job {job_info.job_id}: {e}",
                    exc_info=True
                )
                # Update job state to failed
                item_job = job_state_manager.get_job(job_info.job_id)
                if item_job:
                    item_job.set_failed(str(e))

        logger.info(
            f"Channel download batch {batch_id} created: {len(jobs)} jobs queued"
        )

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
    except MetadataExtractionError as e:
        logger.error(f"Failed to extract channel info: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract channel information: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to create channel download job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create channel download job: {str(e)}"
        )
