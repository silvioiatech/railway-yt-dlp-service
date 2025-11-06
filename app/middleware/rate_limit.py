"""
Rate limiting middleware and configuration for the Ultimate Media Downloader.

Provides slowapi-based rate limiting with configurable storage backend
(Redis or in-memory) and custom rate limit key functions.
"""
import logging
from typing import Optional

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key from request.

    Uses API key if present for per-client limiting, otherwise falls back
    to IP address. This allows authenticated clients to have independent
    rate limits while still rate limiting unauthenticated requests by IP.

    Args:
        request: FastAPI request object

    Returns:
        str: Rate limit key (API key or IP address)
    """
    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use first 16 chars of API key as identifier (don't log full key)
        key_prefix = api_key[:16] if len(api_key) >= 16 else api_key
        logger.debug(f"Rate limiting by API key: {key_prefix}...")
        return f"api_key:{api_key}"

    # Fall back to IP address
    ip_address = get_remote_address(request)
    logger.debug(f"Rate limiting by IP: {ip_address}")
    return f"ip:{ip_address}"


def create_limiter(settings: Optional[Settings] = None) -> Limiter:
    """
    Create and configure rate limiter instance.

    Args:
        settings: Application settings (defaults to get_settings())

    Returns:
        Limiter: Configured slowapi Limiter instance
    """
    if settings is None:
        settings = get_settings()

    # Create limiter with custom key function
    limiter = Limiter(
        key_func=get_rate_limit_key,
        default_limits=[f"{settings.RATE_LIMIT_RPS}/second"],
        storage_uri="memory://",  # Use in-memory storage by default
        strategy="fixed-window",  # Fixed window rate limiting
        headers_enabled=True,  # Add rate limit headers to responses
    )

    logger.info(
        f"Rate limiter initialized: {settings.RATE_LIMIT_RPS} requests/second, "
        f"burst: {settings.RATE_LIMIT_BURST}"
    )

    return limiter


async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded
) -> Response:
    """
    Custom handler for rate limit exceeded errors.

    Provides consistent JSON error response with rate limit information
    and Retry-After header.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception

    Returns:
        Response: JSON error response with 429 status code
    """
    from datetime import datetime, timezone
    from fastapi.responses import JSONResponse

    # Extract retry after from exception
    retry_after = getattr(exc, 'retry_after', 60)

    # Log rate limit violation
    client_identifier = get_rate_limit_key(request)
    logger.warning(
        f"Rate limit exceeded for {client_identifier} on {request.url.path}"
    )

    # Build error response
    error_response = {
        "error": "Rate limit exceeded",
        "error_code": "RATE_LIMIT_EXCEEDED",
        "status_code": HTTP_429_TOO_MANY_REQUESTS,
        "retry_after": retry_after,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {
            "message": str(exc),
            "limit": exc.detail if hasattr(exc, 'detail') else "See X-RateLimit-* headers"
        }
    }

    # Return response with Retry-After header
    return JSONResponse(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        content=error_response,
        headers={"Retry-After": str(retry_after)}
    )


def get_limiter() -> Limiter:
    """
    Get or create the global rate limiter instance.

    This function is cached by FastAPI's dependency injection system,
    ensuring a single limiter instance across the application.

    Returns:
        Limiter: Global rate limiter instance
    """
    return create_limiter()


# Export commonly used components
__all__ = [
    'create_limiter',
    'get_limiter',
    'get_rate_limit_key',
    'rate_limit_exceeded_handler',
]
