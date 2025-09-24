import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from threading import Event
from typing import Any, Dict, List, Optional, Set, Literal
from urllib.parse import urlparse

import httpx
import prometheus_client
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from process import StreamingPipeline

# =========================
# Configuration
# =========================

# Core settings
API_KEY = os.getenv("API_KEY", "")
if not API_KEY:
    raise RuntimeError("API_KEY environment variable is required")

ALLOW_YT_DOWNLOADS = os.getenv("ALLOW_YT_DOWNLOADS", "false").lower() == "true"
RCLONE_REMOTE_DEFAULT = os.getenv("RCLONE_REMOTE_DEFAULT", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
WORKERS = int(os.getenv("WORKERS", "2"))

# Rate limiting
RATE_LIMIT_RPS = int(os.getenv("RATE_LIMIT_RPS", "2"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "5"))

# Timeouts and limits
DEFAULT_TIMEOUT_SEC = int(os.getenv("DEFAULT_TIMEOUT_SEC", "1800"))
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "10737418240"))  # 10GB
PROGRESS_TIMEOUT_SEC = int(os.getenv("PROGRESS_TIMEOUT_SEC", "300"))  # 5min no progress = abort

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Domain allowlist (optional)
ALLOWED_DOMAINS = os.getenv("ALLOWED_DOMAINS", "").split(",") if os.getenv("ALLOWED_DOMAINS") else []

# =========================
# Logging Setup
# =========================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "app.log")
    ]
)
logger = logging.getLogger(__name__)

# =========================
# Metrics
# =========================
JOBS_TOTAL = prometheus_client.Counter('jobs_total', 'Total jobs processed', ['status'])
JOBS_DURATION = prometheus_client.Histogram('jobs_duration_seconds', 'Job duration')
BYTES_UPLOADED = prometheus_client.Counter('bytes_uploaded_total', 'Total bytes uploaded')
JOBS_IN_FLIGHT = prometheus_client.Gauge('jobs_in_flight', 'Jobs currently running')

# =========================
# State Management
# =========================
job_states: Dict[str, Dict[str, Any]] = {}
executor: Optional[ThreadPoolExecutor] = None
shutdown_event = Event()

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{RATE_LIMIT_RPS}/second"]
)

# =========================
# Models
# =========================
class DownloadRequest(BaseModel):
    url: str = Field(..., description="Source URL to download")
    dest: str = Field("BUCKET", description="Destination type")
    remote: Optional[str] = Field(None, description="rclone remote name")
    path: str = Field("videos/{safe_title}-{id}.{ext}", description="Object path template")
    format: str = Field("bv*+ba/best", description="yt-dlp format selector")
    webhook: Optional[str] = Field(None, description="Webhook URL for completion notification")
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers for object storage")
    cookies: Optional[str] = Field(None, description="Cookies for yt-dlp")
    timeout_sec: int = Field(DEFAULT_TIMEOUT_SEC, ge=60, le=7200, description="Timeout in seconds")
    content_type: Optional[str] = Field(None, description="Content-Type header override")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("URL is required")
        
        v = v.strip()
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("URL must start with http:// or https://")
        
        parsed = urlparse(v)
        
        # Check YouTube ToS compliance
        if not ALLOW_YT_DOWNLOADS and any(
            domain in parsed.netloc.lower() 
            for domain in ['youtube.com', 'youtu.be', 'googlevideo.com']
        ):
            raise ValueError("YouTube downloads are disabled per Terms of Service")
        
        # Check domain allowlist if configured
        if ALLOWED_DOMAINS and not any(
            domain in parsed.netloc.lower() 
            for domain in ALLOWED_DOMAINS
        ):
            raise ValueError(f"Domain not allowed. Allowed domains: {', '.join(ALLOWED_DOMAINS)}")
        
        return v

    @field_validator('dest')
    @classmethod
    def validate_dest(cls, v: str) -> str:
        if v not in ["BUCKET"]:
            raise ValueError("Only 'BUCKET' destination is supported")
        return v

class DownloadResponse(BaseModel):
    status: str = Field(..., description="Job status: QUEUED, RUNNING, DONE, ERROR")
    request_id: str = Field(..., description="Unique request identifier")
    object_url: Optional[str] = Field(None, description="URL to access the uploaded object")
    bytes: Optional[int] = Field(None, description="Bytes uploaded")
    duration_sec: Optional[float] = Field(None, description="Processing duration")
    logs_url: Optional[str] = Field(None, description="URL to access job logs")
    error: Optional[str] = Field(None, description="Error message if status is ERROR")
    created_at: Optional[str] = Field(None, description="Job creation timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    checks: Dict[str, str]

# =========================
# Security & Rate Limiting
# =========================
def require_api_key(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request') or (args[0] if args else None)
        if not request:
            raise HTTPException(status_code=500, detail="Internal error: no request object")
        
        auth_header = request.headers.get("X-API-Key")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-API-Key header required"
            )
        
        # Constant-time comparison
        if not hmac.compare_digest(auth_header, API_KEY):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        return await func(*args, **kwargs)
    return wrapper

# =========================
# Path Templating
# =========================
def sanitize_filename(name: str) -> str:
    """Sanitize filename for object storage keys."""
    if not name:
        return "unknown"
    
    # Replace problematic characters
    safe = re.sub(r'[^\w\-_\.]', '_', name)
    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe)
    # Remove leading/trailing underscores and dots
    safe = safe.strip('_.')
    
    return safe[:200] if safe else "unknown"  # Limit length

def expand_path_template(template: str, metadata: Dict[str, Any]) -> str:
    """Expand path template with metadata tokens."""
    
    # Extract common metadata with fallbacks
    video_id = metadata.get('id', 'unknown')
    title = metadata.get('title', 'Unknown Title')
    safe_title = sanitize_filename(title)
    ext = metadata.get('ext', 'mp4')
    uploader = sanitize_filename(metadata.get('uploader', 'unknown'))
    
    # Generate date string
    upload_date = metadata.get('upload_date')
    if upload_date:
        try:
            date_obj = datetime.strptime(str(upload_date), '%Y%m%d')
            date_str = date_obj.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    else:
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Generate random component
    random_str = secrets.token_hex(4)
    
    # Template expansion
    replacements = {
        '{id}': video_id,
        '{title}': title,
        '{safe_title}': safe_title,
        '{ext}': ext,
        '{uploader}': uploader,
        '{date}': date_str,
        '{random}': random_str,
    }
    
    expanded = template
    for token, value in replacements.items():
        expanded = expanded.replace(token, str(value))
    
    # Final sanitization of the full path
    return re.sub(r'/+', '/', expanded.strip('/'))

# =========================
# Job Management
# =========================
def create_job(request_id: str, payload: DownloadRequest) -> Dict[str, Any]:
    """Create a new job record."""
    now = datetime.now(timezone.utc)
    job = {
        'request_id': request_id,
        'status': 'QUEUED',
        'payload': payload.model_dump(),
        'created_at': now.isoformat(),
        'logs': [],
        'bytes': 0,
        'object_path': None,
        'object_url': None,
        'error': None,
        'completed_at': None,
        'duration_sec': None,
    }
    job_states[request_id] = job
    return job

def update_job(request_id: str, **updates) -> Dict[str, Any]:
    """Update job state."""
    if request_id not in job_states:
        raise ValueError(f"Job {request_id} not found")
    
    job = job_states[request_id]
    job.update(updates)
    
    # Auto-set completion timestamp and duration for terminal states
    if updates.get('status') in ['DONE', 'ERROR'] and not job.get('completed_at'):
        now = datetime.now(timezone.utc)
        job['completed_at'] = now.isoformat()
        
        created_at = datetime.fromisoformat(job['created_at'].replace('Z', '+00:00'))
        job['duration_sec'] = (now - created_at).total_seconds()
    
    return job

def get_job(request_id: str) -> Optional[Dict[str, Any]]:
    """Get job by request_id."""
    return job_states.get(request_id)

def add_job_log(request_id: str, message: str, level: str = "INFO"):
    """Add a log entry to job."""
    if request_id in job_states:
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = f"[{timestamp}] {level}: {message}"
        
        job_states[request_id]['logs'].append(log_entry)
        
        # Keep only last 100 log entries in memory
        if len(job_states[request_id]['logs']) > 100:
            job_states[request_id]['logs'] = job_states[request_id]['logs'][-100:]
        
        # Write to persistent log file
        log_file = LOG_DIR / f"{request_id}.log"
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            logger.error(f"Failed to write to log file {log_file}: {e}")

# =========================
# Background Job Processor
# =========================
async def process_download_job(request_id: str, payload: DownloadRequest):
    """Process a download job using streaming pipeline."""
    
    try:
        update_job(request_id, status='RUNNING')
        add_job_log(request_id, f"Starting download: {payload.url}")
        JOBS_IN_FLIGHT.inc()
        
        # Determine remote and validate rclone config
        remote = payload.remote or RCLONE_REMOTE_DEFAULT
        if not remote:
            raise ValueError("No rclone remote specified and no default configured")
        
        add_job_log(request_id, f"Using rclone remote: {remote}")
        
        # Create streaming pipeline
        pipeline = StreamingPipeline(
            request_id=request_id,
            source_url=payload.url,
            rclone_remote=remote,
            path_template=payload.path,
            yt_dlp_format=payload.format,
            timeout_sec=payload.timeout_sec,
            progress_timeout_sec=PROGRESS_TIMEOUT_SEC,
            max_content_length=MAX_CONTENT_LENGTH,
            headers=payload.headers,
            cookies=payload.cookies,
            content_type=payload.content_type,
            log_callback=lambda msg, level="INFO": add_job_log(request_id, msg, level)
        )
        
        # Execute pipeline
        result = await pipeline.execute()
        
        # Generate object URL
        object_url = None
        if result.get('object_path'):
            object_url = await get_object_url(remote, result['object_path'])
        
        # Update job with success
        update_job(
            request_id,
            status='DONE',
            bytes=result.get('bytes_transferred', 0),
            object_path=result.get('object_path'),
            object_url=object_url
        )
        
        add_job_log(request_id, f"Download completed successfully. Bytes: {result.get('bytes_transferred', 0)}")
        JOBS_TOTAL.labels(status='success').inc()
        BYTES_UPLOADED.inc(result.get('bytes_transferred', 0))
        
        # Send webhook if configured
        if payload.webhook:
            await send_webhook(payload.webhook, request_id, 'DONE')
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Job {request_id} failed: {error_msg}", exc_info=True)
        
        update_job(request_id, status='ERROR', error=error_msg)
        add_job_log(request_id, f"Job failed: {error_msg}", "ERROR")
        JOBS_TOTAL.labels(status='error').inc()
        
        # Send webhook if configured
        if payload.webhook:
            await send_webhook(payload.webhook, request_id, 'ERROR', error_msg)
    
    finally:
        JOBS_IN_FLIGHT.dec()

async def get_object_url(remote: str, object_path: str) -> Optional[str]:
    """Get public or signed URL for object using rclone link."""
    try:
        cmd = ['rclone', 'link', f"{remote}:{object_path}"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        
        if process.returncode == 0:
            url = stdout.decode().strip()
            if url:
                return url
        
        # Fallback to canonical path if rclone link not supported
        logger.warning(f"rclone link failed for {remote}:{object_path}, using canonical path")
        return f"{remote}:{object_path}"
        
    except Exception as e:
        logger.error(f"Failed to get object URL: {e}")
        return f"{remote}:{object_path}"

async def send_webhook(webhook_url: str, request_id: str, status: str, error: Optional[str] = None):
    """Send webhook notification."""
    try:
        job = get_job(request_id)
        if not job:
            return
        
        payload = {
            'request_id': request_id,
            'status': status,
            'created_at': job.get('created_at'),
            'completed_at': job.get('completed_at'),
            'object_url': job.get('object_url'),
            'bytes': job.get('bytes', 0),
            'duration_sec': job.get('duration_sec')
        }
        
        if error:
            payload['error'] = error
        
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(webhook_url, json=payload)
            
        logger.info(f"Webhook sent successfully for job {request_id}")
        
    except Exception as e:
        logger.error(f"Failed to send webhook for job {request_id}: {e}")

# =========================
# FastAPI App
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global executor
    
    # Startup
    executor = ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="download-")
    logger.info(f"Started download service with {WORKERS} workers")
    
    yield
    
    # Shutdown
    logger.info("Shutting down download service...")
    shutdown_event.set()
    
    if executor:
        executor.shutdown(wait=True)
    
    logger.info("Download service shutdown complete")

app = FastAPI(
    title="yt-dlp Streaming Service",
    description="Production-ready yt-dlp service with rclone streaming to object storage",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# =========================
# Routes
# =========================

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "yt-dlp Streaming Service",
        "version": "2.0.0",
        "status": "healthy",
        "features": {
            "youtube_downloads": ALLOW_YT_DOWNLOADS,
            "default_remote": RCLONE_REMOTE_DEFAULT or "(not configured)",
            "workers": WORKERS,
            "rate_limit_rps": RATE_LIMIT_RPS
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/download", response_model=DownloadResponse)
@require_api_key
@limiter.limit(f"{RATE_LIMIT_RPS}/second")
async def create_download(request: Request, payload: DownloadRequest):
    """Create a new download job."""
    
    request_id = str(uuid.uuid4())
    
    try:
        # Create job record
        job = create_job(request_id, payload)
        
        # Submit to executor
        loop = asyncio.get_event_loop()
        executor.submit(
            asyncio.run_coroutine_threadsafe,
            process_download_job(request_id, payload),
            loop
        )
        
        # Build response
        logs_url = None
        if PUBLIC_BASE_URL:
            logs_url = f"{PUBLIC_BASE_URL}/downloads/{request_id}/logs"
        
        logger.info(f"Created download job {request_id} for URL: {payload.url}")
        
        return DownloadResponse(
            status="QUEUED",
            request_id=request_id,
            logs_url=logs_url,
            created_at=job['created_at']
        )
        
    except Exception as e:
        logger.error(f"Failed to create download job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/downloads/{request_id}", response_model=DownloadResponse)
async def get_download_status(request_id: str):
    """Get download job status."""
    
    job = get_job(request_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build logs URL
    logs_url = None
    if PUBLIC_BASE_URL:
        logs_url = f"{PUBLIC_BASE_URL}/downloads/{request_id}/logs"
    
    return DownloadResponse(
        status=job['status'],
        request_id=request_id,
        object_url=job.get('object_url'),
        bytes=job.get('bytes'),
        duration_sec=job.get('duration_sec'),
        logs_url=logs_url,
        error=job.get('error'),
        created_at=job.get('created_at'),
        completed_at=job.get('completed_at')
    )

@app.get("/downloads/{request_id}/logs")
async def get_download_logs(request_id: str):
    """Get download job logs."""
    
    job = get_job(request_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Return in-memory logs with option to read from file
    logs = job.get('logs', [])
    
    # Try to read from persistent log file if available
    log_file = LOG_DIR / f"{request_id}.log"
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                file_logs = f.read().strip().split('\n') if f.read().strip() else []
            # Return file logs if more comprehensive than memory logs
            if len(file_logs) > len(logs):
                logs = file_logs
        except Exception as e:
            logger.error(f"Failed to read log file {log_file}: {e}")
    
    return {
        'request_id': request_id,
        'logs': logs,
        'status': job['status'],
        'log_count': len(logs)
    }

@app.get("/healthz", response_model=HealthResponse)
async def healthcheck():
    """Health check endpoint."""
    
    checks = {
        "executor": "healthy" if executor and not executor._shutdown else "unhealthy",
        "rclone": "unknown",
        "yt_dlp": "unknown"
    }
    
    # Check rclone availability
    try:
        process = await asyncio.create_subprocess_exec(
            'rclone', 'version',
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(process.communicate(), timeout=5)
        checks["rclone"] = "healthy" if process.returncode == 0 else "unhealthy"
    except Exception:
        checks["rclone"] = "unhealthy"
    
    # Check yt-dlp availability
    try:
        process = await asyncio.create_subprocess_exec(
            'yt-dlp', '--version',
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(process.communicate(), timeout=5)
        checks["yt_dlp"] = "healthy" if process.returncode == 0 else "unhealthy"
    except Exception:
        checks["yt_dlp"] = "unhealthy"
    
    # Determine overall status
    overall_status = "healthy" if all(
        check in ["healthy", "unknown"] for check in checks.values()
    ) else "unhealthy"
    
    status_code = 200 if overall_status == "healthy" else 503
    
    response = HealthResponse(
        status=overall_status,
        version="2.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=checks
    )
    
    return JSONResponse(content=response.model_dump(), status_code=status_code)

@app.get("/readyz")
async def readiness():
    """Readiness check endpoint."""
    
    if not executor or executor._shutdown or shutdown_event.is_set():
        return JSONResponse(
            {"status": "not ready", "reason": "service shutting down"},
            status_code=503
        )
    
    return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/version")
async def version():
    """Version endpoint."""
    return {
        "version": "2.0.0",
        "build_date": "2025-09-24",
        "features": ["streaming", "rclone", "yt-dlp"]
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# =========================
# Error Handlers
# =========================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent JSON format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)