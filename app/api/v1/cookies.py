"""
Cookie management API endpoints for authentication.

Provides secure endpoints for uploading, listing, retrieving, and deleting
authentication cookies for downloading private/members-only content.
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.auth import RequireAuth
from app.core.exceptions import ValidationError
from app.models.requests import CookiesUploadRequest
from app.models.responses import (
    CookieListResponse,
    CookieResponse,
    DeleteResponse,
)
from app.services.cookie_manager import get_cookie_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cookies", tags=["Authentication"])


@router.post(
    "",
    response_model=CookieResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload or extract cookies",
    description="""
    Upload cookies in Netscape format or extract them from an installed browser.

    **Two modes:**
    1. **Upload mode**: Provide cookies in Netscape format
    2. **Browser extraction mode**: Specify browser name to auto-extract

    **Supported browsers:** chrome, firefox, edge, safari, brave, opera, chromium

    Cookies are encrypted at rest using AES-256-GCM and can be used for downloading
    private or members-only content.

    **Example (Upload):**
    ```json
    {
      "cookies": "# Netscape HTTP Cookie File\\n.example.com\\tTRUE\\t/\\tTRUE\\t1234567890\\tsession_id\\tabc123",
      "name": "my_auth_cookies"
    }
    ```

    **Example (Browser extraction):**
    ```json
    {
      "browser": "chrome",
      "name": "chrome_cookies",
      "profile": "Default"
    }
    ```
    """,
)
async def upload_cookies(
    request: CookiesUploadRequest,
    _auth: RequireAuth
) -> CookieResponse:
    """
    Upload cookies or extract from browser.

    Args:
        request: Cookie upload request (either cookies or browser must be provided)
        _auth: Authentication dependency

    Returns:
        CookieResponse with cookie_id and metadata

    Raises:
        HTTPException: 400 if validation fails, 500 if storage fails
    """
    try:
        cookie_manager = get_cookie_manager()

        # Determine mode: upload or browser extraction
        if request.browser:
            # Browser extraction mode
            logger.info(f"Extracting cookies from browser: {request.browser}")
            result = cookie_manager.extract_browser_cookies(
                browser=request.browser,
                name=request.name or "default",
                profile=request.profile
            )
        else:
            # Upload mode
            if not request.cookies:
                raise ValidationError("Either 'cookies' or 'browser' must be provided")

            logger.info(f"Uploading cookies with name: {request.name}")
            result = cookie_manager.save_cookies(
                cookies_content=request.cookies,
                name=request.name or "default",
                browser=None
            )

        # Convert to response model
        response = CookieResponse(
            cookie_id=result['cookie_id'],
            name=result['name'],
            created_at=datetime.fromisoformat(result['created_at']),
            browser=result.get('browser'),
            domains=result.get('domains', []),
            status=result.get('status', 'active')
        )

        logger.info(f"Successfully stored cookies: {response.cookie_id}")
        return response

    except ValidationError as e:
        logger.warning(f"Cookie validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to store cookies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store cookies: {str(e)}"
        )


@router.get(
    "",
    response_model=CookieListResponse,
    summary="List all stored cookies",
    description="""
    Retrieve a list of all stored cookie sets with metadata.

    Returns cookie_id, name, creation date, browser, and covered domains for each set.
    Does not return the actual cookie content for security.
    """,
)
async def list_cookies(
    _auth: RequireAuth
) -> CookieListResponse:
    """
    List all stored cookie sets.

    Args:
        _auth: Authentication dependency

    Returns:
        CookieListResponse with list of cookies
    """
    try:
        cookie_manager = get_cookie_manager()
        cookies_metadata = cookie_manager.list_cookies()

        # Convert to response models
        cookies = []
        for meta in cookies_metadata:
            cookies.append(CookieResponse(
                cookie_id=meta['cookie_id'],
                name=meta['name'],
                created_at=datetime.fromisoformat(meta['created_at']),
                browser=meta.get('browser'),
                domains=meta.get('domains', []),
                status=meta.get('status', 'active')
            ))

        return CookieListResponse(cookies=cookies, total=len(cookies))

    except Exception as e:
        logger.error(f"Failed to list cookies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cookies: {str(e)}"
        )


@router.get(
    "/{cookie_id}",
    response_model=CookieResponse,
    summary="Get cookie metadata",
    description="""
    Retrieve metadata for a specific cookie set.

    Returns cookie_id, name, creation date, browser, and covered domains.
    Does not return the actual cookie content for security.
    """,
)
async def get_cookie_metadata(
    cookie_id: str,
    _auth: RequireAuth
) -> CookieResponse:
    """
    Get metadata for a specific cookie set.

    Args:
        cookie_id: Unique cookie identifier
        _auth: Authentication dependency

    Returns:
        CookieResponse with metadata

    Raises:
        HTTPException: 404 if cookie not found
    """
    try:
        cookie_manager = get_cookie_manager()
        meta = cookie_manager.get_cookies_metadata(cookie_id)

        return CookieResponse(
            cookie_id=meta['cookie_id'],
            name=meta['name'],
            created_at=datetime.fromisoformat(meta['created_at']),
            browser=meta.get('browser'),
            domains=meta.get('domains', []),
            status=meta.get('status', 'active')
        )

    except ValidationError as e:
        logger.warning(f"Cookie not found: {cookie_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get cookie metadata: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cookie metadata: {str(e)}"
        )


@router.delete(
    "/{cookie_id}",
    response_model=DeleteResponse,
    summary="Delete cookies",
    description="""
    Delete a stored cookie set by ID.

    This permanently removes both the encrypted cookies and their metadata.
    This action cannot be undone.
    """,
)
async def delete_cookies(
    cookie_id: str,
    _auth: RequireAuth
) -> DeleteResponse:
    """
    Delete a stored cookie set.

    Args:
        cookie_id: Unique cookie identifier
        _auth: Authentication dependency

    Returns:
        DeleteResponse with deletion status

    Raises:
        HTTPException: 404 if cookie not found, 500 if deletion fails
    """
    try:
        cookie_manager = get_cookie_manager()
        cookie_manager.delete_cookies(cookie_id)

        logger.info(f"Successfully deleted cookies: {cookie_id}")
        return DeleteResponse(
            id=cookie_id,
            resource_type="cookies",
            status="deleted",
            message="Cookies successfully deleted",
            timestamp=datetime.utcnow()
        )

    except ValidationError as e:
        logger.warning(f"Cookie not found for deletion: {cookie_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete cookies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete cookies: {str(e)}"
        )
