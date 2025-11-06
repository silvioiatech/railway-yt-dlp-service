"""
Example: Using Webhooks with Ultimate Media Downloader

This script demonstrates how to:
1. Set up a simple webhook receiver
2. Submit a download with webhook notifications
3. Verify webhook signatures
4. Handle different webhook events

Requirements:
    pip install httpx fastapi uvicorn
"""

import asyncio
import hashlib
import hmac
import json
from datetime import datetime

import httpx
from fastapi import FastAPI, Request, Header
from typing import Optional
import uvicorn


# =========================
# Webhook Receiver
# =========================

app = FastAPI(title="Webhook Receiver")


@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
):
    """
    Webhook endpoint that receives notifications from the downloader.

    This endpoint will receive events for:
    - download.started: When download begins
    - download.progress: Progress updates (throttled)
    - download.completed: When download finishes successfully
    - download.failed: When download fails
    """
    # Get raw body for signature verification
    body = await request.body()
    body_text = body.decode('utf-8')

    # Parse JSON payload
    payload = json.loads(body_text)

    # Verify signature (if provided)
    if x_webhook_signature:
        api_key = "your-api-key-here"  # Same as API_KEY in downloader config
        is_valid = verify_webhook_signature(body_text, x_webhook_signature, api_key)

        if not is_valid:
            print("WARNING: Invalid webhook signature!")
            return {"error": "Invalid signature"}
        else:
            print("✓ Webhook signature verified")

    # Handle different event types
    event = payload.get("event")
    request_id = payload.get("request_id")
    timestamp = payload.get("timestamp")
    data = payload.get("data", {})

    print(f"\n{'='*60}")
    print(f"Webhook Received: {event}")
    print(f"{'='*60}")
    print(f"Request ID: {request_id}")
    print(f"Timestamp: {timestamp}")

    if event == "download.started":
        print(f"Download started for: {data.get('url')}")

    elif event == "download.progress":
        progress = data.get("progress", {})
        percent = progress.get("percent", 0.0)
        speed = progress.get("speed", 0)
        eta = progress.get("eta", 0)
        print(f"Progress: {percent:.1f}%")
        print(f"Speed: {speed / 1024 / 1024:.2f} MB/s" if speed else "Speed: Unknown")
        print(f"ETA: {eta}s" if eta else "ETA: Unknown")

    elif event == "download.completed":
        print(f"Download completed!")
        print(f"Title: {data.get('title')}")
        print(f"File URL: {data.get('file_url')}")
        print(f"File Size: {data.get('file_size', 0) / 1024 / 1024:.2f} MB")

    elif event == "download.failed":
        print(f"Download failed!")
        print(f"Error: {data.get('error')}")
        print(f"Error Type: {data.get('error_type')}")

    print(f"{'='*60}\n")

    return {"status": "received", "event": event}


def verify_webhook_signature(payload: str, signature: str, secret_key: str) -> bool:
    """
    Verify HMAC-SHA256 webhook signature.

    Args:
        payload: Raw JSON payload string
        signature: Signature from X-Webhook-Signature header
        secret_key: Secret key (API_KEY from downloader config)

    Returns:
        True if signature is valid
    """
    if not signature or not signature.startswith("sha256="):
        return False

    expected_sig = signature[7:]  # Remove "sha256=" prefix

    # Calculate signature
    calculated_sig = hmac.new(
        secret_key.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    return hmac.compare_digest(expected_sig, calculated_sig)


# =========================
# Downloader Client
# =========================

class DownloaderClient:
    """Client for interacting with Ultimate Media Downloader API."""

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize downloader client.

        Args:
            base_url: Base URL of downloader service (e.g., http://localhost:8080)
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    async def create_download(
        self,
        url: str,
        webhook_url: str,
        quality: str = "best",
        audio_only: bool = False
    ) -> dict:
        """
        Create a download with webhook notifications.

        Args:
            url: Video URL to download
            webhook_url: Webhook URL for notifications
            quality: Quality preset (best, 1080p, 720p, etc.)
            audio_only: Extract audio only

        Returns:
            dict: Download response with request_id
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/download",
                headers=self.headers,
                json={
                    "url": url,
                    "quality": quality,
                    "audio_only": audio_only,
                    "webhook_url": webhook_url
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def get_download_status(self, request_id: str) -> dict:
        """
        Get download status.

        Args:
            request_id: Request ID from create_download

        Returns:
            dict: Download status
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/download/{request_id}",
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def create_batch_download(
        self,
        urls: list,
        webhook_url: str,
        concurrent_limit: int = 3
    ) -> dict:
        """
        Create a batch download with webhook notifications.

        Args:
            urls: List of video URLs
            webhook_url: Webhook URL for notifications
            concurrent_limit: Max concurrent downloads

        Returns:
            dict: Batch response with batch_id
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/batch/download",
                headers=self.headers,
                json={
                    "urls": urls,
                    "webhook_url": webhook_url,
                    "concurrent_limit": concurrent_limit
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()


# =========================
# Example Usage
# =========================

async def run_webhook_example():
    """
    Example: Download with webhook notifications.

    This demonstrates:
    1. Starting a webhook receiver
    2. Submitting a download with webhook URL
    3. Receiving real-time notifications
    """
    # Configuration
    DOWNLOADER_URL = "http://localhost:8080"
    API_KEY = "your-api-key-here"
    WEBHOOK_URL = "http://localhost:8081/webhook"

    # Video URL to download (use a short test video)
    VIDEO_URL = "https://www.sample-videos.com/video321/mp4/240/big_buck_bunny_240p_1mb.mp4"

    print("="*60)
    print("Webhook Example - Ultimate Media Downloader")
    print("="*60)
    print()
    print("Step 1: Start the webhook receiver server on port 8081")
    print("        (Run this in a separate terminal)")
    print()
    print("        python examples/webhook_example.py --receiver")
    print()
    print("Step 2: Submit a download with webhook notifications")
    print()

    # Create downloader client
    client = DownloaderClient(DOWNLOADER_URL, API_KEY)

    try:
        # Create download with webhook
        print(f"Submitting download for: {VIDEO_URL}")
        print(f"Webhook URL: {WEBHOOK_URL}")
        print()

        response = await client.create_download(
            url=VIDEO_URL,
            webhook_url=WEBHOOK_URL,
            quality="best"
        )

        request_id = response["request_id"]
        print(f"✓ Download created: {request_id}")
        print()
        print("Webhook notifications will be sent to your receiver as the download progresses:")
        print("  - download.started: When download begins")
        print("  - download.progress: Progress updates (every ~1 second)")
        print("  - download.completed: When download finishes")
        print()

        # Poll for status
        print("Polling download status...")
        while True:
            status = await client.get_download_status(request_id)

            if status["status"] in ["completed", "failed", "cancelled"]:
                print(f"\n✓ Download {status['status']}")
                if status["status"] == "completed":
                    print(f"File URL: {status.get('file_info', {}).get('file_url')}")
                break

            await asyncio.sleep(2)

    except httpx.HTTPStatusError as e:
        print(f"\n✗ HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"\n✗ Error: {e}")


async def run_batch_webhook_example():
    """
    Example: Batch download with webhooks.
    """
    DOWNLOADER_URL = "http://localhost:8080"
    API_KEY = "your-api-key-here"
    WEBHOOK_URL = "http://localhost:8081/webhook"

    # Multiple URLs
    URLS = [
        "https://www.sample-videos.com/video321/mp4/240/big_buck_bunny_240p_1mb.mp4",
        "https://www.sample-videos.com/video321/mp4/240/big_buck_bunny_240p_2mb.mp4",
    ]

    print("Batch Download with Webhooks")
    print("="*60)

    client = DownloaderClient(DOWNLOADER_URL, API_KEY)

    try:
        response = await client.create_batch_download(
            urls=URLS,
            webhook_url=WEBHOOK_URL,
            concurrent_limit=2
        )

        batch_id = response["batch_id"]
        print(f"✓ Batch created: {batch_id}")
        print(f"Total jobs: {response['total_jobs']}")
        print()
        print("Each job will send webhook notifications independently.")
        print("Check your webhook receiver for events!")

    except Exception as e:
        print(f"✗ Error: {e}")


# =========================
# Main
# =========================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--receiver":
        # Start webhook receiver
        print("Starting webhook receiver on http://localhost:8081")
        print("Waiting for webhook notifications...")
        print()
        uvicorn.run(app, host="0.0.0.0", port=8081)
    else:
        # Run example
        print("Example Usage:")
        print()
        print("Terminal 1 - Start webhook receiver:")
        print("  python examples/webhook_example.py --receiver")
        print()
        print("Terminal 2 - Submit download with webhook:")
        print("  python examples/webhook_example.py")
        print()

        # Uncomment to run the example
        # asyncio.run(run_webhook_example())
        # asyncio.run(run_batch_webhook_example())
