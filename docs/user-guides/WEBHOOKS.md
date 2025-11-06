# Webhooks Guide

Complete guide to setting up and receiving real-time webhook notifications for download events.

## Overview

Webhooks provide real-time notifications for:

- **Download Started** - When a download begins
- **Download Progress** - Progress updates (throttled to 1/second)
- **Download Completed** - When download finishes successfully
- **Download Failed** - When download fails with error

## Quick Start

### 1. Provide Webhook URL

Include `webhook_url` in any download request:

```bash
curl -X POST http://localhost:8080/api/v1/download \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video",
    "quality": "1080p",
    "webhook_url": "https://your-app.com/webhook"
  }'
```

### 2. Receive Webhook Events

Your webhook endpoint will receive HTTP POST requests with event data.

## Webhook Payload Format

### Event Structure

```json
{
  "event": "download.completed",
  "timestamp": "2025-11-06T10:02:30Z",
  "request_id": "req_abc123",
  "data": {
    // Event-specific data
  }
}
```

### Event Types

#### download.started

```json
{
  "event": "download.started",
  "timestamp": "2025-11-06T10:00:00Z",
  "request_id": "req_abc123",
  "data": {
    "request_id": "req_abc123",
    "url": "https://example.com/video",
    "status": "running"
  }
}
```

#### download.progress

```json
{
  "event": "download.progress",
  "timestamp": "2025-11-06T10:01:00Z",
  "request_id": "req_abc123",
  "data": {
    "request_id": "req_abc123",
    "url": "https://example.com/video",
    "status": "running",
    "progress": {
      "percent": 45.5,
      "downloaded_bytes": 47721881,
      "total_bytes": 104857600,
      "speed": 1048576,
      "eta": 54
    }
  }
}
```

#### download.completed

```json
{
  "event": "download.completed",
  "timestamp": "2025-11-06T10:02:30Z",
  "request_id": "req_abc123",
  "data": {
    "request_id": "req_abc123",
    "url": "https://example.com/video",
    "status": "completed",
    "file_info": {
      "filename": "video-abc123.mp4",
      "filepath": "videos/video-abc123.mp4",
      "size_bytes": 104857600,
      "download_url": "https://api.example.com/files/videos/video-abc123.mp4"
    },
    "metadata": {
      "title": "Example Video",
      "uploader": "Channel Name",
      "duration": 600
    }
  }
}
```

#### download.failed

```json
{
  "event": "download.failed",
  "timestamp": "2025-11-06T10:02:30Z",
  "request_id": "req_abc123",
  "data": {
    "request_id": "req_abc123",
    "url": "https://example.com/video",
    "status": "failed",
    "error": "Video not available"
  }
}
```

## Webhook Signature Verification

All webhooks include an HMAC-SHA256 signature for verification.

### Signature Header

```http
X-Webhook-Signature: sha256=abc123def456789...
```

### Python Verification

```python
import hmac
import hashlib
from fastapi import Request, HTTPException

def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret_key: str
) -> bool:
    """Verify webhook signature."""
    if not signature or not signature.startswith('sha256='):
        return False

    expected_sig = signature[7:]  # Remove "sha256=" prefix

    calculated_sig = hmac.new(
        secret_key.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    return hmac.compare_digest(expected_sig, calculated_sig)

# FastAPI webhook endpoint
@app.post("/webhook")
async def webhook_handler(request: Request):
    payload = await request.body()
    signature = request.headers.get('X-Webhook-Signature')

    if not verify_webhook_signature(payload, signature, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    event_type = data['event']

    # Process event
    if event_type == 'download.completed':
        handle_download_complete(data['data'])

    return {"status": "ok"}
```

### Node.js Verification

```javascript
const crypto = require('crypto');
const express = require('express');
const app = express();

app.use(express.raw({ type: 'application/json' }));

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
    Buffer.from(expectedSig, 'hex'),
    Buffer.from(calculatedSig, 'hex')
  );
}

app.post('/webhook', (req, res) => {
  const signature = req.headers['x-webhook-signature'];

  if (!verifyWebhookSignature(req.body, signature, process.env.API_KEY)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  const data = JSON.parse(req.body);
  const eventType = data.event;

  // Process event
  if (eventType === 'download.completed') {
    handleDownloadComplete(data.data);
  }

  res.json({ status: 'ok' });
});
```

## Webhook Receiver Examples

### Complete Flask Receiver

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import json

app = Flask(__name__)
API_KEY = "your-api-key"

def verify_signature(payload, signature):
    if not signature or not signature.startswith('sha256='):
        return False
    expected = signature[7:]
    calculated = hmac.new(
        API_KEY.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, calculated)

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers.get('X-Webhook-Signature')
    payload = request.get_data()

    if not verify_signature(payload, signature):
        return jsonify({'error': 'Invalid signature'}), 401

    data = request.json
    event = data['event']
    request_id = data['request_id']

    print(f"Received {event} for {request_id}")

    if event == 'download.started':
        print(f"Download started: {data['data']['url']}")

    elif event == 'download.progress':
        progress = data['data']['progress']
        print(f"Progress: {progress['percent']:.1f}%")

    elif event == 'download.completed':
        file_info = data['data']['file_info']
        print(f"Completed: {file_info['filename']}")
        # Download or process file
        download_url = file_info['download_url']

    elif event == 'download.failed':
        error = data['data']['error']
        print(f"Failed: {error}")

    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(port=5000)
```

### FastAPI Async Receiver

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib

app = FastAPI()
API_KEY = "your-api-key"

@app.post("/webhook")
async def webhook_handler(request: Request):
    signature = request.headers.get('X-Webhook-Signature')
    payload = await request.body()

    # Verify signature
    if not signature or not signature.startswith('sha256='):
        raise HTTPException(status_code=401, detail="Missing signature")

    expected = signature[7:]
    calculated = hmac.new(
        API_KEY.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, calculated):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Process event
    data = await request.json()
    event = data['event']

    # Handle event asynchronously
    if event == 'download.completed':
        file_info = data['data']['file_info']
        # Process completed download
        await process_completed_download(file_info)

    return {"status": "ok"}

async def process_completed_download(file_info: dict):
    """Process completed download."""
    # Your processing logic here
    print(f"Processing: {file_info['filename']}")
```

## Configuration

### Environment Variables

```bash
# Enable/disable webhooks
WEBHOOK_ENABLE=true

# Webhook timeout (1-60 seconds)
WEBHOOK_TIMEOUT_SEC=10

# Maximum retry attempts (1-10)
WEBHOOK_MAX_RETRIES=3
```

### Per-Request Configuration

```json
{
  "url": "https://example.com/video",
  "webhook_url": "https://your-app.com/webhook"
}
```

## Retry Logic

### Automatic Retries

- **Max Retries**: 3 attempts (configurable)
- **Backoff**: Exponential (1s, 2s, 4s)
- **Timeout**: 10 seconds per request (configurable)

### HTTP Status Code Handling

- **2xx (Success)**: No retry, webhook delivered
- **4xx (Client Error)**: No retry, permanent failure
- **5xx (Server Error)**: Retry with exponential backoff
- **Timeout**: Retry with exponential backoff

### Example Retry Sequence

```
Attempt 1: POST webhook -> Timeout
Wait 1 second
Attempt 2: POST webhook -> 503 Service Unavailable
Wait 2 seconds
Attempt 3: POST webhook -> 200 OK (Success!)
```

## Testing Webhooks

### Local Testing with ngrok

```bash
# Start ngrok tunnel
ngrok http 5000

# Use ngrok URL in webhook_url
curl -X POST http://localhost:8080/api/v1/download \
  -H "X-API-Key: your-api-key" \
  -d '{
    "url": "https://example.com/video",
    "webhook_url": "https://abc123.ngrok.io/webhook"
  }'
```

### Testing with RequestBin

1. Create bin at [requestbin.com](https://requestbin.com)
2. Use bin URL as `webhook_url`
3. Inspect received webhooks in browser

### Mock Webhook Server

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        data = json.loads(body)

        print(f"Received {data['event']} for {data['request_id']}")
        print(json.dumps(data, indent=2))

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

server = HTTPServer(('localhost', 5000), WebhookHandler)
print("Webhook server listening on http://localhost:5000")
server.serve_forever()
```

## Use Cases

### 1. Notification System

Send email/SMS when download completes:

```python
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    if data['event'] == 'download.completed':
        file_info = data['data']['file_info']
        await send_email(
            to="user@example.com",
            subject="Download Complete",
            body=f"Your download is ready: {file_info['filename']}"
        )

    return {"status": "ok"}
```

### 2. Post-Processing Pipeline

Trigger transcoding after download:

```python
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    if data['event'] == 'download.completed':
        file_path = data['data']['file_info']['filepath']
        # Trigger transcoding job
        await transcode_video(file_path, output_format='h264')

    return {"status": "ok"}
```

### 3. Database Updates

Track download status in database:

```python
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    event = data['event']
    request_id = data['request_id']

    if event == 'download.started':
        await db.downloads.update_one(
            {'request_id': request_id},
            {'$set': {'status': 'downloading'}}
        )

    elif event == 'download.completed':
        file_info = data['data']['file_info']
        await db.downloads.update_one(
            {'request_id': request_id},
            {'$set': {
                'status': 'completed',
                'file_path': file_info['filepath'],
                'completed_at': data['timestamp']
            }}
        )

    return {"status": "ok"}
```

### 4. Cloud Upload

Upload to S3 after download:

```python
import boto3

s3 = boto3.client('s3')

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    if data['event'] == 'download.completed':
        file_info = data['data']['file_info']
        download_url = file_info['download_url']

        # Download file
        response = requests.get(download_url)

        # Upload to S3
        s3.put_object(
            Bucket='my-bucket',
            Key=file_info['filename'],
            Body=response.content
        )

    return {"status": "ok"}
```

## Best Practices

### 1. Always Verify Signatures

Never trust webhook payloads without signature verification:

```python
if not verify_signature(payload, signature, secret_key):
    raise HTTPException(status_code=401)
```

### 2. Return 200 Quickly

Process webhooks asynchronously to avoid timeouts:

```python
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    # Queue for async processing
    await task_queue.enqueue(process_webhook, data)

    # Return immediately
    return {"status": "ok"}
```

### 3. Handle Duplicate Events

Progress events may be sent multiple times:

```python
# Use request_id to deduplicate
processed_events = set()

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    event_id = f"{data['request_id']}:{data['event']}"

    if event_id in processed_events:
        return {"status": "duplicate"}

    processed_events.add(event_id)
    # Process event
```

### 4. Log All Events

Keep audit trail of webhook events:

```python
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    # Log to database
    await db.webhook_events.insert_one({
        'event': data['event'],
        'request_id': data['request_id'],
        'timestamp': data['timestamp'],
        'data': data['data']
    })

    return {"status": "ok"}
```

## Troubleshooting

### Webhooks not received

1. Check webhook URL is accessible from internet
2. Verify firewall allows incoming connections
3. Check webhook endpoint returns 200 status
4. Review server logs for errors

### Signature verification fails

1. Ensure secret key matches API_KEY
2. Verify you're using raw request body for signature
3. Check for any body modifications by middleware

### Getting duplicate events

This is normal for progress events. Implement deduplication logic.

### Webhook timeouts

1. Reduce webhook timeout: `WEBHOOK_TIMEOUT_SEC=30`
2. Return 200 immediately, process asynchronously
3. Optimize webhook endpoint performance

## Related Guides

- [API Reference](../api/API_REFERENCE_COMPLETE.md)
- [Batch Downloads](BATCH_DOWNLOADS.md)
- [Channel Downloads](CHANNEL_DOWNLOADS.md)

---

**Last Updated**: 2025-11-06
