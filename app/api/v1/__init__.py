"""
API v1 package initialization.

Exports the main API router for integration with the FastAPI application.
"""
from app.api.v1.router import api_router

__all__ = ["api_router"]
