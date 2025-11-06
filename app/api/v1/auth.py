"""
Authentication dependencies for the Ultimate Media Downloader API.

Provides FastAPI dependency functions for API key authentication with
constant-time comparison to prevent timing attacks.
"""
import hmac
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def require_api_key(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)]
) -> None:
    """
    Dependency to enforce API key authentication.

    Uses constant-time comparison (hmac.compare_digest) to prevent timing attacks.
    Checks the X-API-Key header against the configured API_KEY.

    Args:
        request: FastAPI request object
        settings: Application settings injected via dependency

    Raises:
        HTTPException: 401 if API key is required but missing or invalid

    Example:
        ```python
        @router.get("/protected")
        async def protected_route(
            auth: Annotated[None, Depends(require_api_key)]
        ):
            return {"message": "Access granted"}
        ```
    """
    # Skip authentication if not required
    if not settings.REQUIRE_API_KEY:
        logger.debug("API key authentication disabled")
        return

    # Get API key from header
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        logger.warning(
            f"Missing API key from {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(api_key, settings.API_KEY):
        logger.warning(
            f"Invalid API key from {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.debug("API key authentication successful")


def optional_api_key(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)]
) -> bool:
    """
    Optional API key authentication that returns authentication status.

    Unlike require_api_key, this does not raise an exception on missing/invalid keys,
    but returns whether authentication was successful. Useful for endpoints that
    provide different behavior based on authentication status.

    Args:
        request: FastAPI request object
        settings: Application settings injected via dependency

    Returns:
        bool: True if authenticated, False otherwise

    Example:
        ```python
        @router.get("/data")
        async def get_data(
            authenticated: Annotated[bool, Depends(optional_api_key)]
        ):
            if authenticated:
                return {"data": "full_data"}
            return {"data": "limited_data"}
        ```
    """
    # If authentication is not required, consider everyone authenticated
    if not settings.REQUIRE_API_KEY:
        return True

    # Get API key from header
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return False

    # Constant-time comparison
    return hmac.compare_digest(api_key, settings.API_KEY)


# Type aliases for cleaner dependency injection
RequireAuth = Annotated[None, Depends(require_api_key)]
OptionalAuth = Annotated[bool, Depends(optional_api_key)]
