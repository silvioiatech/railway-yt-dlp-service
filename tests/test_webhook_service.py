"""
Unit tests for webhook notification service.

Tests webhook delivery, retry logic, signature generation, and error handling.
"""

import asyncio
import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.webhook_service import (
    WebhookDeliveryService,
    WebhookEvent,
    WebhookPayload,
)


class TestWebhookPayload:
    """Test webhook payload model."""

    def test_payload_creation(self):
        """Test creating webhook payload."""
        payload = WebhookPayload(
            event=WebhookEvent.DOWNLOAD_STARTED,
            timestamp="2025-11-06T10:00:00Z",
            request_id="req_123",
            data={"url": "https://example.com/video"}
        )

        assert payload.event == WebhookEvent.DOWNLOAD_STARTED
        assert payload.request_id == "req_123"
        assert payload.data["url"] == "https://example.com/video"

    def test_payload_serialization(self):
        """Test payload JSON serialization."""
        payload = WebhookPayload(
            event=WebhookEvent.DOWNLOAD_COMPLETED,
            timestamp="2025-11-06T10:00:00Z",
            request_id="req_123",
            data={"status": "completed"}
        )

        json_str = payload.model_dump_json()
        data = json.loads(json_str)

        assert data["event"] == "download.completed"
        assert data["request_id"] == "req_123"


class TestWebhookDeliveryService:
    """Test webhook delivery service."""

    @pytest.fixture
    def webhook_service(self):
        """Create webhook service instance."""
        return WebhookDeliveryService(
            timeout_sec=5,
            max_retries=3,
            enabled=True
        )

    @pytest.fixture
    def sample_payload(self):
        """Create sample webhook payload."""
        return {
            "request_id": "req_123",
            "url": "https://example.com/video",
            "status": "completed"
        }

    def test_service_initialization(self, webhook_service):
        """Test service initialization with custom parameters."""
        assert webhook_service.timeout_sec == 5
        assert webhook_service.max_retries == 3
        assert webhook_service.enabled is True

    def test_signature_generation(self, webhook_service):
        """Test HMAC-SHA256 signature generation."""
        payload = WebhookPayload(
            event=WebhookEvent.DOWNLOAD_COMPLETED,
            timestamp="2025-11-06T10:00:00Z",
            request_id="req_123",
            data={"status": "completed"}
        )
        secret_key = "test_secret_key"

        signature = webhook_service._generate_signature(payload, secret_key)

        assert signature.startswith("sha256=")
        assert len(signature) == 71  # "sha256=" + 64 hex characters

    def test_signature_verification(self, webhook_service):
        """Test signature verification."""
        payload_json = '{"test": "data"}'
        secret_key = "test_secret_key"

        # Generate valid signature
        expected_sig = hmac.new(
            secret_key.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        signature = f"sha256={expected_sig}"

        # Verify signature
        is_valid = webhook_service.verify_signature(
            payload_json,
            signature,
            secret_key
        )

        assert is_valid is True

    def test_signature_verification_invalid(self, webhook_service):
        """Test signature verification with invalid signature."""
        payload_json = '{"test": "data"}'
        secret_key = "test_secret_key"
        invalid_signature = "sha256=invalid_signature_here"

        is_valid = webhook_service.verify_signature(
            payload_json,
            invalid_signature,
            secret_key
        )

        assert is_valid is False

    def test_url_sanitization(self, webhook_service):
        """Test URL sanitization for logging."""
        # URL with credentials
        url = "https://user:password@example.com/webhook?api_key=secret"
        sanitized = webhook_service._sanitize_url(url)

        assert "password" not in sanitized
        assert "secret" not in sanitized
        assert "example.com" in sanitized

    @pytest.mark.asyncio
    async def test_send_webhook_success(self, webhook_service, sample_payload):
        """Test successful webhook delivery."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            success = await webhook_service.send_webhook(
                url="https://example.com/webhook",
                event_type=WebhookEvent.DOWNLOAD_COMPLETED,
                payload=sample_payload
            )

            assert success is True

    @pytest.mark.asyncio
    async def test_send_webhook_disabled(self, sample_payload):
        """Test webhook delivery when disabled."""
        service = WebhookDeliveryService(enabled=False)

        success = await service.send_webhook(
            url="https://example.com/webhook",
            event_type=WebhookEvent.DOWNLOAD_COMPLETED,
            payload=sample_payload
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_send_webhook_retry_on_500(self, webhook_service, sample_payload):
        """Test webhook retry on 5xx server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            success = await webhook_service.send_webhook(
                url="https://example.com/webhook",
                event_type=WebhookEvent.DOWNLOAD_COMPLETED,
                payload=sample_payload
            )

            # Should fail after 3 retries
            assert success is False
            # Verify it was called 3 times
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 3

    @pytest.mark.asyncio
    async def test_send_webhook_no_retry_on_400(self, webhook_service, sample_payload):
        """Test no retry on 4xx client error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            success = await webhook_service.send_webhook(
                url="https://example.com/webhook",
                event_type=WebhookEvent.DOWNLOAD_COMPLETED,
                payload=sample_payload
            )

            # Should fail immediately without retries
            assert success is False
            # Verify it was only called once
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 1

    @pytest.mark.asyncio
    async def test_send_webhook_timeout(self, webhook_service, sample_payload):
        """Test webhook timeout handling."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            success = await webhook_service.send_webhook(
                url="https://example.com/webhook",
                event_type=WebhookEvent.DOWNLOAD_COMPLETED,
                payload=sample_payload
            )

            # Should fail after retries
            assert success is False
            # Verify retry attempts
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 3

    @pytest.mark.asyncio
    async def test_send_webhook_with_signature(self, sample_payload):
        """Test webhook delivery with signature."""
        service = WebhookDeliveryService(enabled=True)
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await service.send_webhook(
                url="https://example.com/webhook",
                event_type=WebhookEvent.DOWNLOAD_COMPLETED,
                payload=sample_payload,
                signature_key="test_secret"
            )

            # Verify signature header was included
            call_args = mock_post.call_args
            headers = call_args.kwargs.get('headers', {})
            assert 'X-Webhook-Signature' in headers
            assert headers['X-Webhook-Signature'].startswith('sha256=')

    @pytest.mark.asyncio
    async def test_progress_throttling(self, webhook_service, sample_payload):
        """Test progress event throttling."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            # Send multiple progress events rapidly
            results = []
            for _ in range(5):
                success = await webhook_service.send_webhook(
                    url="https://example.com/webhook",
                    event_type=WebhookEvent.DOWNLOAD_PROGRESS,
                    payload=sample_payload
                )
                results.append(success)
                await asyncio.sleep(0.1)  # Small delay

            # First should succeed, others may be throttled
            assert results[0] is True
            # Not all should succeed due to throttling
            assert results.count(True) < 5

    @pytest.mark.asyncio
    async def test_cleanup_throttle_cache(self, webhook_service):
        """Test throttle cache cleanup."""
        request_id = "req_123"

        # Add entry to throttle cache
        webhook_service._last_progress_events[request_id] = 12345.0

        # Clean up
        await webhook_service.cleanup_throttle_cache(request_id)

        # Verify cleanup
        assert request_id not in webhook_service._last_progress_events


class TestWebhookIntegration:
    """Integration tests for webhook system."""

    @pytest.mark.asyncio
    async def test_complete_webhook_flow(self):
        """Test complete webhook delivery flow."""
        service = WebhookDeliveryService(enabled=True, max_retries=2)

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            # Send started event
            success = await service.send_webhook(
                url="https://example.com/webhook",
                event_type=WebhookEvent.DOWNLOAD_STARTED,
                payload={
                    "request_id": "req_123",
                    "url": "https://example.com/video",
                    "status": "started"
                },
                signature_key="secret_key"
            )
            assert success is True

            # Send progress event
            success = await service.send_webhook(
                url="https://example.com/webhook",
                event_type=WebhookEvent.DOWNLOAD_PROGRESS,
                payload={
                    "request_id": "req_123",
                    "progress": {"percent": 50.0}
                }
            )
            assert success is True

            # Send completed event
            success = await service.send_webhook(
                url="https://example.com/webhook",
                event_type=WebhookEvent.DOWNLOAD_COMPLETED,
                payload={
                    "request_id": "req_123",
                    "file_url": "https://example.com/file.mp4",
                    "status": "completed"
                }
            )
            assert success is True

            # Clean up
            await service.cleanup_throttle_cache("req_123")

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff timing between retries."""
        service = WebhookDeliveryService(enabled=True, max_retries=3)

        with patch('httpx.AsyncClient') as mock_client:
            # First two attempts fail, third succeeds
            call_count = 0

            async def mock_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    response = MagicMock()
                    response.status_code = 500
                    return response
                else:
                    response = MagicMock()
                    response.status_code = 200
                    return response

            mock_client.return_value.__aenter__.return_value.post = mock_post

            start_time = asyncio.get_event_loop().time()

            success = await service.send_webhook(
                url="https://example.com/webhook",
                event_type=WebhookEvent.DOWNLOAD_COMPLETED,
                payload={"request_id": "req_123"}
            )

            end_time = asyncio.get_event_loop().time()
            elapsed = end_time - start_time

            # Should succeed after retries
            assert success is True
            # Should have taken at least 3 seconds (1s + 2s delays)
            assert elapsed >= 3.0
            # Should have been called 3 times
            assert call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
