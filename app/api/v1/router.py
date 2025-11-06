"""
Main API router for v1 endpoints.

Combines all API route modules into a single router with proper prefixing
and tags for OpenAPI documentation.
"""
from fastapi import APIRouter

from app.api.v1 import auth, download, health, metadata, playlist

# Create main v1 router
api_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
api_router.include_router(health.router)
api_router.include_router(download.router)
api_router.include_router(metadata.router)
api_router.include_router(playlist.router)


# Export router for use in main application
__all__ = ["api_router"]
