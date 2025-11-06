# Webhook Notification System Guide

## Overview

The Ultimate Media Downloader supports webhook notifications to provide real-time updates about download job lifecycle events. Webhooks enable you to integrate downloads into your workflow by receiving HTTP callbacks when events occur.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Event Types](#event-types)
- [Payload Structure](#payload-structure)
- [Security](#security)
- [Retry Logic](#retry-logic)
- [Integration Examples](#integration-examples)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Enable Webhooks

Add to your `.env` file:

```bash
# Webhook Configuration
WEBHOOK_ENABLE=true
WEBHOOK_TIMEOUT_SEC=10
WEBHOOK_MAX_RETRIES=3
```

### 2. Create a Download with Webhook

```bash
curl -X POST "http://localhost:8080/api/v1/download" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video",
    "quality": "1080p",
    "webhook_url": "https://your-server.com/webhook"
  }'
```

### 3. Receive Webhook Events

Your webhook endpoint will receive POST requests with JSON payloads:

```json
{
  "event": "download.completed",
  "timestamp": "2025-11-06T10:30:00Z",
  "request_id": "req_abc123",
  "data": {
    "url": "https://example.com/video",
    "title": "Video Title",
    "file_url": "https://your-app.railway.app/files/video.mp4",
    "file_size": 52428800,
    "status": "completed"
  }
}
```

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WEBHOOK_ENABLE` | boolean | `true` | Enable/disable webhook system |
| `WEBHOOK_TIMEOUT_SEC` | integer | `10` | Request timeout (1-60 seconds) |
| `WEBHOOK_MAX_RETRIES` | integer | `3` | Maximum retry attempts (1-10) |

### Per-Request Configuration

Include `webhook_url` in your download request:

```json
{
  "url": "https://example.com/video",
  "webhook_url": "https://your-server.com/webhook"
}
```

## Event Types

### `download.started`

Triggered when a download job begins processing.

**Payload:**
```json
{
  "event": "download.started",
  "timestamp": "2025-11-06T10:00:00Z",
  "request_id": "req_abc123",
  "data": {
    "request_id": "req_abc123",
    "url": "https://example.com/video",
    "status": "started"
  }
}
```

### `download.progress`

Triggered periodically during download (throttled to ~1 second intervals).

**Payload:**
```json
{
  "event": "download.progress",
  "timestamp": "2025-11-06T10:00:30Z",
  "request_id": "req_abc123",
  "data": {
    "request_id": "req_abc123",
    "url": "https://example.com/video",
    "status": "downloading",
    "progress": {
      "percent": 45.5,
      "downloaded_bytes": 23855104,
      "total_bytes": 52428800,
      "speed": 1048576.0,
      "eta": 27
    }
  }
}
```

### `download.completed`

Triggered when a download finishes successfully.

**Payload:**
```json
{
  "event": "download.completed",
  "timestamp": "2025-11-06T10:05:00Z",
  "request_id": "req_abc123",
  "data": {
    "request_id": "req_abc123",
    "url": "https://example.com/video",
    "title": "Example Video Title",
    "file_url": "https://your-app.railway.app/files/videos/video.mp4",
    "file_path": "videos/video.mp4",
    "file_size": 52428800,
    "status": "completed",
    "duration": 600
  }
}
```

### `download.failed`

Triggered when a download fails.

**Payload:**
```json
{
  "event": "download.failed",
  "timestamp": "2025-11-06T10:05:00Z",
  "request_id": "req_abc123",
  "data": {
    "request_id": "req_abc123",
    "url": "https://example.com/video",
    "status": "failed",
    "error": "Video not available",
    "error_type": "download_error"
  }
}
```

**Error Types:**
- `timeout`: Download exceeded timeout limit
- `download_error`: General download failure
- `unexpected_error`: Unexpected system error

## Payload Structure

All webhook payloads follow this structure:

```typescript
{
  event: "download.started" | "download.progress" | "download.completed" | "download.failed",
  timestamp: string,  // ISO 8601 format with Z suffix
  request_id: string, // Unique job identifier
  data: object        // Event-specific data
}
```

### Common Data Fields

| Field | Type | Events | Description |
|-------|------|--------|-------------|
| `request_id` | string | All | Unique job identifier |
| `url` | string | All | Original video URL |
| `status` | string | All | Current status |
| `title` | string | completed | Video title |
| `file_url` | string | completed | Public URL to download file |
| `file_size` | integer | completed | File size in bytes |
| `progress` | object | progress | Progress information |
| `error` | string | failed | Error message |

## Security

### HMAC Signature Verification

All webhooks include an HMAC-SHA256 signature in the `X-Webhook-Signature` header for verification.

#### Signature Format

```
X-Webhook-Signature: sha256={hex_digest}
```

#### Verification Example (Python)

```python
import hmac
import hashlib

def verify_webhook_signature(payload: str, signature: str, secret_key: str) -> bool:
    """
    Verify HMAC-SHA256 webhook signature.

    Args:
        payload: Raw JSON payload string from request body
        signature: Value from X-Webhook-Signature header
        secret_key: Your API_KEY from downloader config

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

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_sig, calculated_sig)


# Usage in Flask
from flask import request

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Webhook-Signature')

    if not verify_webhook_signature(payload, signature, 'your-api-key'):
        return {'error': 'Invalid signature'}, 401

    # Process webhook...
    return {'status': 'received'}, 200
```

#### Verification Example (Node.js)

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secretKey) {
    if (!signature || !signature.startsWith('sha256=')) {
        return false;
    }

    const expectedSig = signature.substring(7);

    const calculatedSig = crypto
        .createHmac('sha256', secretKey)
        .update(payload)
        .digest('hex');

    return crypto.timingSafeEqual(
        Buffer.from(expectedSig),
        Buffer.from(calculatedSig)
    );
}

// Usage in Express
app.post('/webhook', (req, res) => {
    const payload = JSON.stringify(req.body);
    const signature = req.headers['x-webhook-signature'];

    if (!verifyWebhookSignature(payload, signature, 'your-api-key')) {
        return res.status(401).json({ error: 'Invalid signature' });
    }

    // Process webhook...
    res.json({ status: 'received' });
});
```

### Security Best Practices

1. **Always verify signatures** before processing webhooks
2. **Use HTTPS** for your webhook endpoint
3. **Validate payload structure** before processing
4. **Rate limit** webhook endpoints to prevent abuse
5. **Log suspicious activity** (invalid signatures, unexpected payloads)

## Retry Logic

### Exponential Backoff

Webhooks use exponential backoff retry on failures:

- **Attempt 1**: Immediate
- **Attempt 2**: Wait 1 second
- **Attempt 3**: Wait 2 seconds
- **Attempt 4**: Wait 4 seconds (if max_retries > 3)

### Retry Conditions

| Status Code | Retry? | Description |
|-------------|--------|-------------|
| `2xx` | No | Success - no retry needed |
| `4xx` | No | Client error - permanent failure |
| `5xx` | Yes | Server error - temporary failure |
| Timeout | Yes | Network timeout - retry |
| Connection Error | Yes | Network issue - retry |

### Configuration

```env
# Maximum retry attempts (1-10)
WEBHOOK_MAX_RETRIES=3

# Timeout per request (1-60 seconds)
WEBHOOK_TIMEOUT_SEC=10
```

## Integration Examples

### Python + FastAPI

```python
from fastapi import FastAPI, Request, Header
from typing import Optional
import hmac
import hashlib

app = FastAPI()

@app.post("/webhook")
async def webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
):
    # Get raw body
    body = await request.body()
    payload = body.decode('utf-8')

    # Verify signature
    if not verify_signature(payload, x_webhook_signature):
        return {"error": "Invalid signature"}, 401

    # Parse payload
    data = await request.json()
    event = data.get("event")

    # Handle events
    if event == "download.completed":
        # Process completed download
        file_url = data["data"]["file_url"]
        # ... your logic here

    return {"status": "received"}
```

### Node.js + Express

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/webhook', (req, res) => {
    const signature = req.headers['x-webhook-signature'];
    const payload = JSON.stringify(req.body);

    // Verify signature
    if (!verifySignature(payload, signature)) {
        return res.status(401).json({ error: 'Invalid signature' });
    }

    const { event, data } = req.body;

    // Handle events
    switch(event) {
        case 'download.completed':
            console.log('Download completed:', data.file_url);
            break;
        case 'download.failed':
            console.error('Download failed:', data.error);
            break;
    }

    res.json({ status: 'received' });
});

app.listen(3000);
```

### Webhook Endpoint Requirements

Your webhook endpoint must:

1. **Accept POST requests** with JSON body
2. **Return 2xx status** within timeout (default 10 seconds)
3. **Handle duplicate events** (idempotent processing)
4. **Process asynchronously** (respond quickly, process later)

### Example Webhook Receiver

```python
from fastapi import FastAPI, BackgroundTasks
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    # Respond immediately
    background_tasks.add_task(process_webhook, await request.json())
    return {"status": "received"}

async def process_webhook(data: dict):
    """Process webhook in background."""
    try:
        event = data.get("event")
        # ... your processing logic
        logger.info(f"Processed webhook: {event}")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
```

## Testing

### Local Testing with ngrok

1. **Install ngrok**:
   ```bash
   npm install -g ngrok
   ```

2. **Start your webhook receiver**:
   ```bash
   python examples/webhook_example.py --receiver
   ```

3. **Expose to internet**:
   ```bash
   ngrok http 8081
   ```

4. **Use ngrok URL**:
   ```bash
   curl -X POST "http://localhost:8080/api/v1/download" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com/video",
       "webhook_url": "https://abc123.ngrok.io/webhook"
     }'
   ```

### Testing with Webhook.site

For quick testing without a server:

1. Visit [webhook.site](https://webhook.site)
2. Copy your unique URL
3. Use it as `webhook_url` in your request
4. View received webhooks in the browser

### Unit Testing

Run the webhook service tests:

```bash
pytest tests/test_webhook_service.py -v
```

## Troubleshooting

### Webhooks Not Received

**Check webhook is enabled:**
```bash
# Verify in logs
grep "Webhook service initialized" logs/app.log
```

**Verify webhook URL is accessible:**
```bash
curl -X POST https://your-server.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### Signature Verification Fails

**Common issues:**
- Using wrong API key
- Parsing JSON before verification (breaks signature)
- Incorrect HMAC algorithm (must be SHA256)

**Solution:**
```python
# ✓ Correct: Verify raw body
body = await request.body()
verify_signature(body.decode('utf-8'), signature)

# ✗ Wrong: Verify parsed JSON
data = await request.json()
verify_signature(json.dumps(data), signature)  # Different JSON formatting
```

### Webhook Timeouts

**Increase timeout:**
```env
WEBHOOK_TIMEOUT_SEC=30
```

**Make endpoint faster:**
- Process webhooks asynchronously
- Return 200 immediately
- Process in background job

### Missing Progress Events

**Progress events are throttled** to ~1 second intervals to avoid flooding.

**To receive all progress:**
- Poll the status endpoint: `GET /api/v1/download/{request_id}`

## Best Practices

### 1. Idempotent Processing

Process webhooks idempotently in case of duplicates:

```python
processed_events = set()

def process_webhook(request_id: str, event: str):
    event_key = f"{request_id}:{event}"

    if event_key in processed_events:
        return  # Already processed

    # Process event
    # ...

    processed_events.add(event_key)
```

### 2. Async Processing

Respond quickly, process later:

```python
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    # Respond immediately
    data = await request.json()
    background_tasks.add_task(process_webhook, data)
    return {"status": "received"}
```

### 3. Error Handling

Handle webhook processing errors gracefully:

```python
try:
    process_webhook(data)
except Exception as e:
    logger.error(f"Webhook processing failed: {e}")
    # Don't return error - webhook already delivered successfully
```

### 4. Monitoring

Monitor webhook delivery:

```python
import prometheus_client as prom

webhook_received = prom.Counter(
    'webhook_received_total',
    'Total webhooks received',
    ['event_type', 'status']
)

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    webhook_received.labels(
        event_type=data['event'],
        status='success'
    ).inc()
    return {"status": "received"}
```

## API Reference

### Webhook Payload

```typescript
interface WebhookPayload {
  event: 'download.started' | 'download.progress' | 'download.completed' | 'download.failed';
  timestamp: string;      // ISO 8601 with Z
  request_id: string;
  data: object;
}
```

### Headers

```
Content-Type: application/json
X-Webhook-Signature: sha256={hex_digest}
User-Agent: Ultimate-Media-Downloader-Webhook/{version}
```

### Response Codes

Your webhook endpoint should return:
- `200-299`: Success - webhook processed
- `4xx`: Client error - won't retry
- `5xx`: Server error - will retry

## Support

For issues or questions:
- GitHub Issues: [railway-yt-dlp-service/issues](https://github.com/your-repo/issues)
- Documentation: [docs/](../docs/)
- Examples: [examples/webhook_example.py](../examples/webhook_example.py)
