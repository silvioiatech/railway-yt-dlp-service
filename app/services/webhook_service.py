"""
Webhook notification service for Ultimate Media Downloader.

This module provides webhook delivery with retry logic, HMAC signature verification,
and event dispatching for download lifecycle events.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, HttpUrl

from app.config import get_settings

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """Webhook event types."""

    DOWNLOAD_STARTED = "download.started"
    DOWNLOAD_PROGRESS = "download.progress"
    DOWNLOAD_COMPLETED = "download.completed"
    DOWNLOAD_FAILED = "download.failed"


class WebhookPayload(BaseModel):
    """Webhook payload structure."""

    event: WebhookEvent
    timestamp: str  # ISO 8601 format
    request_id: str
    data: Dict[str, Any]

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class WebhookDeliveryService:
    """
    Service for delivering webhook notifications with retry logic.

    Features:
    - Async HTTP delivery using httpx
    - Exponential backoff retry (3 attempts with 1s, 2s, 4s delays)
    - HMAC-SHA256 signature generation
    - Timeout handling (10 seconds per request)
    - Comprehensive error logging
    """

    def __init__(
        self,
        timeout_sec: Optional[int] = None,
        max_retries: Optional[int] = None,
        enabled: Optional[bool] = None
    ):
        """
        Initialize webhook delivery service.

        Args:
            timeout_sec: Timeout for webhook requests (defaults to config)
            max_retries: Maximum retry attempts (defaults to config)
            enabled: Enable/disable webhook delivery (defaults to config)
        """
        settings = get_settings()
        self.timeout_sec = timeout_sec or settings.WEBHOOK_TIMEOUT_SEC
        self.max_retries = max_retries or settings.WEBHOOK_MAX_RETRIES
        self.enabled = enabled if enabled is not None else settings.WEBHOOK_ENABLE

        # Track last progress event time to throttle progress updates
        self._last_progress_events: Dict[str, float] = {}
        self._progress_throttle_sec = 1.0  # Minimum 1 second between progress events

        logger.info(
            f"Webhook service initialized - "
            f"enabled={self.enabled}, timeout={self.timeout_sec}s, "
            f"max_retries={self.max_retries}"
        )

    async def send_webhook(
        self,
        url: str,
        event_type: WebhookEvent,
        payload: Dict[str, Any],
        signature_key: Optional[str] = None
    ) -> bool:
        """
        Send webhook notification with retry logic.

        Args:
            url: Webhook URL to send to
            event_type: Type of event
            payload: Event payload data
            signature_key: Secret key for HMAC signature (uses API_KEY if None)

        Returns:
            True if webhook was delivered successfully, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Webhook delivery disabled, skipping event {event_type}")
            return False

        # Throttle progress events to avoid flooding
        if event_type == WebhookEvent.DOWNLOAD_PROGRESS:
            request_id = payload.get("request_id", "")
            now = asyncio.get_event_loop().time()
            last_time = self._last_progress_events.get(request_id, 0.0)

            if now - last_time < self._progress_throttle_sec:
                logger.debug(f"Throttling progress webhook for {request_id}")
                return False

            self._last_progress_events[request_id] = now

        # Construct webhook payload
        webhook_payload = WebhookPayload(
            event=event_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            request_id=payload.get("request_id", "unknown"),
            data=payload
        )

        # Generate signature
        signature = None
        if signature_key or get_settings().API_KEY:
            key = signature_key or get_settings().API_KEY
            signature = self._generate_signature(webhook_payload, key)

        # Send with retry logic
        success = await self._send_with_retry(url, webhook_payload, signature)

        return success

    async def _send_with_retry(
        self,
        url: str,
        payload: WebhookPayload,
        signature: Optional[str]
    ) -> bool:
        """
        Send webhook with exponential backoff retry.

        Args:
            url: Webhook URL
            payload: Webhook payload
            signature: HMAC signature

        Returns:
            True if delivered successfully, False otherwise
        """
        payload_json = payload.model_dump_json()
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"Ultimate-Media-Downloader-Webhook/{get_settings().VERSION}"
        }

        if signature:
            headers["X-Webhook-Signature"] = signature

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    logger.debug(
                        f"Sending webhook to {self._sanitize_url(url)} "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )

                    response = await client.post(
                        url,
                        content=payload_json,
                        headers=headers,
                        timeout=self.timeout_sec
                    )

                    # Log response
                    logger.info(
                        f"Webhook delivered - "
                        f"url={self._sanitize_url(url)}, "
                        f"event={payload.event}, "
                        f"status={response.status_code}, "
                        f"attempt={attempt + 1}"
                    )

                    # Success on 2xx status codes
                    if 200 <= response.status_code < 300:
                        return True

                    # Don't retry on 4xx client errors (permanent failure)
                    if 400 <= response.status_code < 500:
                        logger.warning(
                            f"Webhook permanent failure (4xx) - "
                            f"url={self._sanitize_url(url)}, "
                            f"status={response.status_code}, "
                            f"response={response.text[:200]}"
                        )
                        return False

                    # Retry on 5xx server errors
                    if response.status_code >= 500:
                        logger.warning(
                            f"Webhook temporary failure (5xx) - "
                            f"url={self._sanitize_url(url)}, "
                            f"status={response.status_code}, "
                            f"will_retry={attempt < self.max_retries - 1}"
                        )

            except httpx.TimeoutException:
                logger.warning(
                    f"Webhook timeout - "
                    f"url={self._sanitize_url(url)}, "
                    f"timeout={self.timeout_sec}s, "
                    f"attempt={attempt + 1}, "
                    f"will_retry={attempt < self.max_retries - 1}"
                )

            except httpx.RequestError as e:
                logger.warning(
                    f"Webhook request error - "
                    f"url={self._sanitize_url(url)}, "
                    f"error={str(e)}, "
                    f"attempt={attempt + 1}, "
                    f"will_retry={attempt < self.max_retries - 1}"
                )

            except Exception as e:
                logger.error(
                    f"Webhook unexpected error - "
                    f"url={self._sanitize_url(url)}, "
                    f"error={str(e)}, "
                    f"attempt={attempt + 1}",
                    exc_info=True
                )

            # Exponential backoff: 1s, 2s, 4s
            if attempt < self.max_retries - 1:
                delay = 2 ** attempt
                logger.debug(f"Waiting {delay}s before retry...")
                await asyncio.sleep(delay)

        # All retries failed
        logger.error(
            f"Webhook delivery failed after {self.max_retries} attempts - "
            f"url={self._sanitize_url(url)}, "
            f"event={payload.event}"
        )
        return False

    def _generate_signature(self, payload: WebhookPayload, secret_key: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload.

        Args:
            payload: Webhook payload
            secret_key: Secret key for signing

        Returns:
            Signature in format "sha256={hex_digest}"
        """
        # Convert payload to JSON with sorted keys for consistent hashing
        payload_json = payload.model_dump_json(indent=None)

        # Generate HMAC signature
        signature = hmac.new(
            secret_key.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"

    def verify_signature(self, payload: str, signature: str, secret_key: str) -> bool:
        """
        Verify HMAC-SHA256 signature of webhook payload.

        Args:
            payload: Raw JSON payload string
            signature: Signature to verify (format: "sha256={hex_digest}")
            secret_key: Secret key for verification

        Returns:
            True if signature is valid, False otherwise
        """
        if not signature or not signature.startswith("sha256="):
            logger.warning("Invalid signature format")
            return False

        expected_sig = signature[7:]  # Remove "sha256=" prefix

        # Generate signature for comparison
        calculated_sig = hmac.new(
            secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_sig, calculated_sig)

        if not is_valid:
            logger.warning("Signature verification failed")

        return is_valid

    def _sanitize_url(self, url: str) -> str:
        """
        Sanitize URL for logging (hide query parameters and credentials).

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL safe for logging
        """
        try:
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(url)
            # Remove credentials and query parameters
            sanitized = urlunparse((
                parsed.scheme,
                parsed.netloc.split('@')[-1] if '@' in parsed.netloc else parsed.netloc,
                parsed.path,
                '',
                '',
                ''
            ))
            return sanitized
        except Exception:
            return url[:50] + "..." if len(url) > 50 else url

    async def cleanup_throttle_cache(self, request_id: str):
        """
        Clean up throttle cache for completed request.

        Args:
            request_id: Request ID to clean up
        """
        if request_id in self._last_progress_events:
            del self._last_progress_events[request_id]
            logger.debug(f"Cleaned up throttle cache for {request_id}")


# Global webhook service instance
_webhook_service: Optional[WebhookDeliveryService] = None


def get_webhook_service() -> WebhookDeliveryService:
    """
    Get the global WebhookDeliveryService instance.

    Returns:
        WebhookDeliveryService: Global webhook service
    """
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookDeliveryService()
    return _webhook_service
