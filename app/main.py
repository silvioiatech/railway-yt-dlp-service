"""
Main FastAPI application entry point for Ultimate Media Downloader.

This module creates and configures the FastAPI application with all middleware,
routers, error handlers, and lifecycle management.
"""
import logging
import logging.handlers
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import prometheus_client
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.config import Settings, get_settings, validate_settings
from app.core.exceptions import MediaDownloaderException
from app.core.scheduler import FileDeletionScheduler, get_scheduler
from app.middleware.rate_limit import (
    create_limiter,
    rate_limit_exceeded_handler as custom_rate_limit_handler
)
from app.services.queue_manager import (
    get_queue_manager,
    initialize_queue_manager,
    shutdown_queue_manager
)

# Configure logging
logger = logging.getLogger(__name__)


def setup_logging(settings: Settings) -> None:
    """
    Configure application logging with file rotation and console output.

    Args:
        settings: Application settings for log configuration
    """
    # Create log directory if it doesn't exist
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=settings.LOG_DIR / "app.log",
        maxBytes=settings.LOG_FILE_MAX_BYTES,
        backupCount=settings.LOG_FILE_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # File gets all debug info
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s '
        '[%(filename)s:%(lineno)d] [%(processName)s:%(threadName)s]'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    logger.info(f"Logging configured: level={settings.LOG_LEVEL}, dir={settings.LOG_DIR}")


# Prometheus metrics registry
custom_registry = prometheus_client.CollectorRegistry()
JOBS_TOTAL = prometheus_client.Counter(
    'jobs_total',
    'Total jobs processed',
    ['status'],
    registry=custom_registry
)
JOBS_DURATION = prometheus_client.Histogram(
    'jobs_duration_seconds',
    'Job duration in seconds',
    registry=custom_registry
)
BYTES_TRANSFERRED = prometheus_client.Counter(
    'bytes_transferred_total',
    'Total bytes transferred',
    registry=custom_registry
)
JOBS_IN_FLIGHT = prometheus_client.Gauge(
    'jobs_in_flight',
    'Jobs currently running',
    registry=custom_registry
)
QUEUE_SIZE = prometheus_client.Gauge(
    'queue_size',
    'Current queue size',
    registry=custom_registry
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown.

    Handles:
    - Settings validation
    - Logging setup
    - Queue manager initialization
    - File deletion scheduler startup
    - Graceful shutdown with cleanup

    Args:
        app: FastAPI application instance
    """
    settings = get_settings()

    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")

    try:
        # Validate settings
        validate_settings()

        # Setup logging
        setup_logging(settings)

        # Validate critical directories
        if not settings.STORAGE_DIR.exists():
            settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created storage directory: {settings.STORAGE_DIR}")

        # Initialize queue manager
        logger.info("Initializing queue manager...")
        queue_manager = await initialize_queue_manager()
        logger.info(
            f"Queue manager started: {queue_manager.max_workers} workers, "
            f"max {queue_manager.max_concurrent_downloads} concurrent downloads"
        )

        # Initialize file deletion scheduler
        logger.info("Initializing file deletion scheduler...")
        scheduler = get_scheduler()
        logger.info("File deletion scheduler started")

        # Store references in app state
        app.state.queue_manager = queue_manager
        app.state.scheduler = scheduler
        app.state.settings = settings

        logger.info(
            f"{settings.APP_NAME} startup complete - "
            f"listening on {settings.HOST}:{settings.PORT}"
        )

        yield

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    finally:
        # Shutdown
        logger.info(f"Shutting down {settings.APP_NAME}...")

        try:
            # Shutdown queue manager
            if hasattr(app.state, 'queue_manager'):
                logger.info("Shutting down queue manager...")
                await shutdown_queue_manager(wait=True, timeout=30.0)
                logger.info("Queue manager shutdown complete")

            # Shutdown file deletion scheduler
            if hasattr(app.state, 'scheduler'):
                logger.info("Shutting down file deletion scheduler...")
                app.state.scheduler.shutdown()
                logger.info("File deletion scheduler shutdown complete")

            logger.info(f"{settings.APP_NAME} shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()

    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Production-ready media downloader service with yt-dlp, "
            "Railway storage, and automatic file cleanup"
        ),
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs" if not settings.DISABLE_DOCS else None,
        redoc_url="/redoc" if not settings.DISABLE_DOCS else None,
        openapi_url="/openapi.json" if not settings.DISABLE_DOCS else None,
    )

    # Configure CORS
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
        )
        logger.info(f"CORS enabled for origins: {settings.CORS_ORIGINS}")

    # Add GZip compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Configure rate limiting
    limiter = create_limiter(settings)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Register exception handlers
    register_exception_handlers(app)

    # Include API router
    app.include_router(api_router)

    # Register additional endpoints
    register_core_endpoints(app)

    # Mount static files if directory exists
    if settings.STATIC_DIR.exists() and any(settings.STATIC_DIR.iterdir()):
        app.mount(
            "/static",
            StaticFiles(directory=str(settings.STATIC_DIR)),
            name="static"
        )
        logger.info(f"Static files mounted at /static from {settings.STATIC_DIR}")

        # Serve index.html at root
        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        async def serve_frontend():
            """Serve the frontend application."""
            index_file = settings.STATIC_DIR / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            # Fallback to API info if no frontend
            return JSONResponse(content=get_service_info())

    else:
        # No static files, serve API info at root
        @app.get("/", response_model=Dict[str, Any])
        async def root():
            """Root endpoint with service information."""
            return get_service_info()

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register custom exception handlers.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(MediaDownloaderException)
    async def media_downloader_exception_handler(
        request: Request,
        exc: MediaDownloaderException
    ):
        """Handle custom application exceptions."""
        logger.warning(
            f"Application exception on {request.url.path}: "
            f"{exc.error_code} - {exc.message}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                **exc.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions with consistent format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            f"Unhandled exception on {request.url.path}: {exc}",
            exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


def register_core_endpoints(app: FastAPI) -> None:
    """
    Register core endpoints (metrics, version, etc.).

    Args:
        app: FastAPI application instance
    """

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        # Update queue metrics
        if hasattr(app.state, 'queue_manager'):
            stats = app.state.queue_manager.get_stats()
            QUEUE_SIZE.set(stats.get('active_jobs', 0))

        return Response(
            content=generate_latest(custom_registry),
            media_type=CONTENT_TYPE_LATEST
        )

    @app.get("/version", tags=["System"])
    async def version():
        """Get service version information."""
        settings = get_settings()
        return {
            "version": settings.VERSION,
            "app_name": settings.APP_NAME,
            "build_date": "2025-11-05",
            "features": [
                "yt-dlp",
                "railway-storage",
                "auto-deletion",
                "playlist-support",
                "metadata-extraction"
            ]
        }

    @app.get("/files/{file_path:path}", include_in_schema=False)
    async def serve_file(file_path: str):
        """
        Serve downloaded files with security checks.

        Args:
            file_path: Relative path to file in storage directory

        Returns:
            FileResponse: The requested file

        Raises:
            HTTPException: 400 if path is invalid, 404 if file not found,
                          403 if access denied
        """
        from app.services.file_manager import get_file_manager
        from app.core.exceptions import StorageError

        settings = get_settings()
        file_manager = get_file_manager()

        # Security: Use FileManager.validate_path() for proper path validation
        try:
            full_path = file_manager.validate_path(Path(file_path))
        except StorageError as e:
            logger.warning(f"Invalid file path requested: {file_path} - {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path"
            )

        # Check if file exists
        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        # Determine content type based on file extension
        content_type = "application/octet-stream"
        suffix = full_path.suffix.lower()
        if suffix in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
            content_type = "video/mp4"
        elif suffix in ['.mp3', '.wav', '.flac', '.m4a', '.aac']:
            content_type = "audio/mpeg"
        elif suffix in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            content_type = f"image/{suffix[1:]}"

        return FileResponse(
            path=str(full_path),
            media_type=content_type,
            filename=full_path.name
        )


def get_service_info() -> Dict[str, Any]:
    """
    Get service information for root endpoint.

    Returns:
        dict: Service information
    """
    settings = get_settings()
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "features": {
            "youtube_downloads": settings.ALLOW_YT_DOWNLOADS,
            "storage_dir": str(settings.STORAGE_DIR),
            "auto_delete_hours": settings.FILE_RETENTION_HOURS,
            "workers": settings.WORKERS,
            "max_concurrent_downloads": settings.MAX_CONCURRENT_DOWNLOADS,
            "rate_limit_rps": settings.RATE_LIMIT_RPS,
            "authentication": "required" if settings.REQUIRE_API_KEY else "optional"
        },
        "endpoints": {
            "api": "/api/v1",
            "docs": "/docs" if not settings.DISABLE_DOCS else None,
            "health": "/api/v1/health",
            "metrics": "/metrics"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Create the application instance
app = create_app()


# Export for uvicorn
__all__ = ['app', 'create_app']
