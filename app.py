import asyncio
import base64
import csv
import io
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

import httpx
import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# =========================
# Config
# =========================
APP_PORT = int(os.getenv("PORT", "8000"))

# Security configuration
API_KEY = os.getenv("API_KEY", "")  # Optional API key protection
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
RATE_LIMIT_REQUESTS = os.getenv("RATE_LIMIT_REQUESTS", "30/minute")

# Destination selection
DEFAULT_DEST = (os.getenv("DEFAULT_DEST") or "LOCAL").upper()  # "LOCAL" or "DRIVE"

# Local (internal storage) config
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
PUBLIC_FILES_DIR = os.getenv("PUBLIC_FILES_DIR", "/data/public")
os.makedirs(PUBLIC_FILES_DIR, exist_ok=True)

# Single-use token TTL (if nobody downloads within this TTL, file is deleted)
ONCE_TOKEN_TTL_SEC = int(os.getenv("ONCE_TOKEN_TTL_SEC", "86400"))
DELETE_AFTER_SERVE = os.getenv("DELETE_AFTER_SERVE", "true").lower() == "true"

# Google Drive (optional)
DRIVE_ENABLED = (
    os.getenv("DRIVE_ENABLED") or ("oauth" if os.getenv("GOOGLE_REFRESH_TOKEN") else "")
).lower() in ("oauth", "service")
DRIVE_AUTH = (os.getenv("DRIVE_AUTH") or "oauth").lower()  # "oauth" | "service"
DRIVE_FOLDER_ID_DEFAULT = (os.getenv("DRIVE_FOLDER_ID") or "").strip() or None
DRIVE_PUBLIC = (os.getenv("DRIVE_PUBLIC") or "false").lower() == "true"

# Timeouts
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT_SEC") or 5400)

# =========================
# Logging Configuration
# =========================
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=os.getenv("LOG_LEVEL", "INFO"),
    serialize=False,
)
logger.add(
    "logs/app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=os.getenv("LOG_LEVEL", "INFO"),
    rotation="100 MB",
    retention="7 days",
    compression="zip",
)

# Create logs directory
os.makedirs("logs", exist_ok=True)

# =========================
# Rate Limiting Setup
# =========================
limiter = Limiter(key_func=get_remote_address)

# =========================
# Security
# =========================
security = HTTPBearer(auto_error=False)


async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Optional API key verification"""
    if not API_KEY:
        return True  # No API key required

    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")

    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


# =========================
# In-memory registries
# =========================
# Single-use token registry: token -> meta
# meta: { path, size, active, consumed, last_seen, expiry, tag, file_id }
ONCE_TOKENS: Dict[str, Dict[str, Any]] = {}

# File registry: file_id -> { path, size, tokens, created_at }
# tokens: set of token IDs that reference this file
FILE_REGISTRY: Dict[str, Dict[str, Any]] = {}

# Job status registry: tag -> {status, payload, updated_at, dest, expected_name}
# status: queued | downloading | ready | error
JOBS: Dict[str, Dict[str, Any]] = {}


# =========================
# Utils
# =========================
def sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return safe.strip(" .")


async def run(cmd: List[str], timeout: Optional[int] = None) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        so, se = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return 124, "", "Timeout"
    return proc.returncode, so.decode(errors="ignore"), se.decode(errors="ignore")


async def safe_callback(url: str, payload: dict):
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json=payload)
    except Exception:
        # best effort only
        pass


def job_set(tag: str, **kw):
    rec = JOBS.get(tag, {"tag": tag})
    rec.update(kw)
    rec["updated_at"] = datetime.utcnow().isoformat()
    JOBS[tag] = rec


# =========================
# Discover endpoint helpers
# =========================
def _parse_dateafter(s: Optional[str]) -> Optional[str]:
    """Parse dateafter parameter into yt-dlp format, gracefully ignoring invalid patterns."""
    if not s or not s.strip():
        return None

    s = s.strip()

    # Handle YYYYMMDD format
    if re.match(r"^\d{8}$", s):
        return s

    # Handle now-<days>days format
    match = re.match(r"^now-(\d+)days?$", s)
    if match:
        days = int(match.group(1))
        target_date = datetime.utcnow() - timedelta(days=days)
        return target_date.strftime("%Y%m%d")

    # Invalid format - gracefully ignore
    return None


def _synthesize_match_filter(
    base: Optional[str], min_duration: Optional[int], max_duration: Optional[int]
) -> Optional[str]:
    """Synthesize match filter combining user expression with duration constraints."""
    filters = []

    # Add user-provided filter
    if base and base.strip():
        filters.append(f"({base.strip()})")

    # Add duration constraints
    if min_duration is not None and min_duration >= 0:
        filters.append(f"(duration >= {min_duration})")

    if max_duration is not None and max_duration >= 0:
        filters.append(f"(duration <= {max_duration})")

    if not filters:
        return None

    return " & ".join(filters)


def _rows_to_csv(rows: List[Dict[str, Any]], fields: Optional[str]) -> bytes:
    """Convert list of dicts to CSV bytes."""
    if not rows:
        return b""

    # Determine fields to include
    if fields and fields.strip():
        field_list = [f.strip() for f in fields.split(",") if f.strip()]
    else:
        # Default fields
        field_list = [
            "id",
            "title",
            "url",
            "duration",
            "view_count",
            "like_count",
            "uploader",
            "upload_date",
        ]

    # Filter to only include fields that exist in at least one row
    available_fields = set()
    for row in rows:
        available_fields.update(row.keys())

    field_list = [f for f in field_list if f in available_fields]

    # Generate CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=field_list, extrasaction="ignore")
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    return output.getvalue().encode("utf-8")


# =========================
# Single-use link helpers (LOCAL)
# =========================
def _file_stat(path: str) -> tuple[int, str]:
    p = pathlib.Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError
    return (p.stat().st_size, p.name)


def _build_once_url(token: str) -> str:
    if not PUBLIC_BASE_URL:
        return f"/once/{token}"
    return f"{PUBLIC_BASE_URL}/once/{token}"


def make_single_use_url(filename: str, tag: str, ttl_sec: Optional[int] = None) -> str:
    """Create a single-use URL for a file with optional custom TTL"""
    path = os.path.join(PUBLIC_FILES_DIR, filename)
    size, _ = _file_stat(path)
    
    # Generate unique file ID based on path for multi-token support
    file_id = f"file_{hash(path) & 0x7FFFFFFF:08x}"
    
    # Register file if not already registered
    if file_id not in FILE_REGISTRY:
        FILE_REGISTRY[file_id] = {
            "path": path,
            "size": size,
            "tokens": set(),
            "created_at": time.time(),
        }
    
    # Create token
    token = uuid.uuid4().hex
    effective_ttl = ttl_sec if ttl_sec is not None else ONCE_TOKEN_TTL_SEC
    
    ONCE_TOKENS[token] = {
        "path": path,
        "size": size,
        "active": 0,  # concurrent streams
        "consumed": False,  # true once any bytes were sent
        "last_seen": time.time(),
        "expiry": time.time() + effective_ttl,
        "tag": tag,
        "file_id": file_id,
    }
    
    # Link token to file
    FILE_REGISTRY[file_id]["tokens"].add(token)
    
    return _build_once_url(token)


def make_multiple_use_urls(filename: str, tag: str, count: int = 1, ttl_sec: Optional[int] = None) -> List[str]:
    """Create multiple single-use URLs for the same file"""
    if count <= 0:
        raise ValueError("count must be positive")
    
    urls = []
    for _ in range(count):
        urls.append(make_single_use_url(filename, tag, ttl_sec))
    return urls


def mint_additional_tokens(file_id: str, count: int = 1, ttl_sec: Optional[int] = None, tag: Optional[str] = None) -> List[str]:
    """Mint additional tokens for an existing file"""
    if file_id not in FILE_REGISTRY:
        raise FileNotFoundError(f"File {file_id} not found in registry")
    
    file_info = FILE_REGISTRY[file_id]
    path = file_info["path"]
    
    # Verify file still exists
    if not os.path.exists(path):
        # Clean up registry
        FILE_REGISTRY.pop(file_id, None)
        raise FileNotFoundError(f"File at {path} no longer exists")
    
    size = file_info["size"]
    effective_ttl = ttl_sec if ttl_sec is not None else ONCE_TOKEN_TTL_SEC
    effective_tag = tag or f"mint_{file_id}"
    
    urls = []
    for _ in range(count):
        token = uuid.uuid4().hex
        ONCE_TOKENS[token] = {
            "path": path,
            "size": size,
            "active": 0,
            "consumed": False,
            "last_seen": time.time(),
            "expiry": time.time() + effective_ttl,
            "tag": effective_tag,
            "file_id": file_id,
        }
        FILE_REGISTRY[file_id]["tokens"].add(token)
        urls.append(_build_once_url(token))
    
    return urls


def _maybe_delete_and_purge(token: str):
    """Delete file and clean up token if conditions are met"""
    meta = ONCE_TOKENS.get(token)
    if not meta:
        return
    
    # Only mark as consumed if active streams finished and bytes were sent
    if meta["active"] == 0 and meta["consumed"]:
        file_id = meta["file_id"]
        
        # Remove token from registry
        ONCE_TOKENS.pop(token, None)
        
        # Update file registry
        if file_id in FILE_REGISTRY:
            FILE_REGISTRY[file_id]["tokens"].discard(token)
            
            # Check if this was the last token for the file
            if not FILE_REGISTRY[file_id]["tokens"]:
                # No more tokens, safe to delete file
                try:
                    if os.path.exists(meta["path"]):
                        os.remove(meta["path"])
                        logger.info(f"Deleted file {meta['path']} (last token consumed)")
                except Exception as e:
                    logger.error(f"Failed to delete file {meta['path']}: {e}")
                
                # Remove from file registry
                FILE_REGISTRY.pop(file_id, None)


def _janitor_loop():
    """Enhanced janitor loop for cleaning up expired tokens and orphaned files"""
    while True:
        try:
            now = time.time()
            expired_tokens = []
            
            # Find expired tokens
            for token, meta in list(ONCE_TOKENS.items()):
                if now > meta.get("expiry", 0):
                    expired_tokens.append(token)
            
            # Process expired tokens
            for token in expired_tokens:
                meta = ONCE_TOKENS.pop(token, None)
                if not meta:
                    continue
                
                file_id = meta.get("file_id")
                if file_id and file_id in FILE_REGISTRY:
                    FILE_REGISTRY[file_id]["tokens"].discard(token)
                    
                    # Delete file if not consumed and no more tokens
                    if not meta["consumed"] and not FILE_REGISTRY[file_id]["tokens"]:
                        try:
                            if os.path.exists(meta["path"]):
                                os.remove(meta["path"])
                                logger.info(f"Deleted expired file {meta['path']}")
                        except Exception as e:
                            logger.error(f"Failed to delete expired file {meta['path']}: {e}")
                        
                        FILE_REGISTRY.pop(file_id, None)
            
            # Clean up orphaned file registry entries
            orphaned_files = []
            for file_id, file_info in list(FILE_REGISTRY.items()):
                if not file_info["tokens"]:  # No tokens reference this file
                    orphaned_files.append(file_id)
            
            for file_id in orphaned_files:
                file_info = FILE_REGISTRY.pop(file_id, None)
                if file_info:
                    try:
                        if os.path.exists(file_info["path"]):
                            os.remove(file_info["path"])
                            logger.info(f"Deleted orphaned file {file_info['path']}")
                    except Exception as e:
                        logger.error(f"Failed to delete orphaned file {file_info['path']}: {e}")
            
            if expired_tokens or orphaned_files:
                logger.info(f"Janitor cleaned up {len(expired_tokens)} expired tokens and {len(orphaned_files)} orphaned files")
                
        except Exception as e:
            logger.error(f"Janitor loop error: {e}")
        
        time.sleep(60)


threading.Thread(target=_janitor_loop, daemon=True).start()

# =========================
# Google Drive (optional)
# =========================
_drive_service = None


def _build_drive():
    global _drive_service
    if _drive_service or not DRIVE_ENABLED:
        return _drive_service
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if DRIVE_AUTH == "oauth":
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
        scopes = (
            os.getenv("GOOGLE_SCOPES") or "https://www.googleapis.com/auth/drive.file"
        ).split()
        if not (client_id and client_secret and refresh_token):
            raise RuntimeError("OAuth selected but GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN missing")
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )
        _drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return _drive_service
    # service account
    service_json = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON")
    if not service_json and os.getenv("DRIVE_SERVICE_ACCOUNT_JSON_B64"):
        service_json = base64.b64decode(os.getenv("DRIVE_SERVICE_ACCOUNT_JSON_B64")).decode("utf-8")
    if not service_json:
        raise RuntimeError(
            "Service auth selected but DRIVE_SERVICE_ACCOUNT_JSON(_B64) not provided"
        )
    creds_info = json.loads(service_json)
    scopes = ["https://www.googleapis.com/auth/drive"]
    sa = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
    _drive_service = build("drive", "v3", credentials=sa, cache_discovery=False)
    return _drive_service


def drive_upload(local_path: str, out_name: str, folder_id: Optional[str]) -> dict:
    svc = _build_drive()
    from googleapiclient.http import MediaFileUpload

    meta = {"name": out_name}
    if folder_id:
        meta["parents"] = [folder_id]
    media = MediaFileUpload(local_path, resumable=True)
    file = svc.files().create(body=meta, media_body=media, fields="id, webViewLink").execute()
    if DRIVE_PUBLIC:
        svc.permissions().create(
            fileId=file["id"], body={"role": "reader", "type": "anyone"}
        ).execute()
    return {"file_id": file["id"], "webViewLink": file.get("webViewLink")}


# =========================
# FastAPI app
# =========================
app = FastAPI(
    title="Railway yt-dlp Service",
    description="A FastAPI service for downloading media using yt-dlp with Google Drive integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Request: {request.method} {request.url}")

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    return response


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Railway yt-dlp Service",
        "version": "1.0.0",
        "default_dest": DEFAULT_DEST,
        "drive_enabled": DRIVE_ENABLED,
        "public_base_url": PUBLIC_BASE_URL or "(unset)",
        "public_files_dir": PUBLIC_FILES_DIR,
        "rate_limit": RATE_LIMIT_REQUESTS,
        "api_key_required": bool(API_KEY),
        "time": datetime.utcnow().isoformat(),
    }


@app.get("/healthz")
@limiter.limit("60/minute")
def healthz(request: Request):
    """Enhanced health check endpoint"""
    try:
        # Check critical dependencies
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "checks": {
                "storage": "healthy" if os.path.exists(PUBLIC_FILES_DIR) else "unhealthy",
                "drive": "enabled" if DRIVE_ENABLED else "disabled",
                "memory": "healthy",  # Could add actual memory check
            },
        }

        # Check if any critical checks failed
        if any(
            check == "unhealthy"
            for check in health_status["checks"].values()
            if check != "disabled"
        ):
            health_status["status"] = "unhealthy"
            return JSONResponse(health_status, status_code=503)

        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            {"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()},
            status_code=503,
        )


@app.get("/metrics")
@limiter.limit("30/minute")
def metrics(request: Request):
    """Basic metrics endpoint for monitoring"""
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return StreamingResponse(iter([generate_latest()]), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        # Fallback metrics if prometheus client not available
        return {
            "jobs": {
                "total": len(JOBS),
                "by_status": {
                    status: len([j for j in JOBS.values() if j.get("status") == status])
                    for status in ["queued", "downloading", "ready", "error"]
                },
            },
            "tokens": {
                "active": len(ONCE_TOKENS),
                "consumed": len([t for t in ONCE_TOKENS.values() if t.get("consumed", False)]),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


# =========================
# Models
# =========================
class DownloadReq(BaseModel):
    url: str
    tag: Optional[str] = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:8]}")
    expected_name: Optional[str] = None
    callback_url: Optional[str] = None
    quality: Literal["BEST_ORIGINAL", "BEST_MP4", "STRICT_MP4_REENC"] = "BEST_MP4"
    timeout: Optional[int] = DOWNLOAD_TIMEOUT
    dest: Optional[Literal["LOCAL", "DRIVE"]] = None
    drive_folder: Optional[str] = None
    # hardening knobs
    retries: Optional[int] = 3  # times per strategy
    socket_timeout: Optional[int] = 30  # yt-dlp --socket-timeout
    prefer_api: Optional[bool] = True  # try rumble:use_api first
    # multi-artifact support
    separate_audio_video: Optional[bool] = False  # download separate audio/video files
    audio_format: Optional[Literal["m4a", "mp3", "best"]] = "m4a"
    token_count: Optional[int] = Field(1, ge=1, le=5)  # number of tokens to create per artifact
    custom_ttl: Optional[int] = Field(None, ge=60, le=604800)  # custom TTL for tokens


class DownloadAck(BaseModel):
    accepted: bool
    tag: str
    expected_name: Optional[str]
    note: str


class MintTokenReq(BaseModel):
    file_id: str = Field(..., description="File ID to mint tokens for")
    count: int = Field(1, ge=1, le=10, description="Number of tokens to mint (1-10)")
    ttl_sec: Optional[int] = Field(None, ge=60, le=604800, description="Custom TTL in seconds (60s to 7 days)")
    tag: Optional[str] = Field(None, description="Optional tag for the new tokens")


class MintTokenResponse(BaseModel):
    success: bool
    file_id: str
    tokens_created: int
    urls: List[str]
    expires_in_sec: int


class FileInfo(BaseModel):
    file_id: str
    filename: str
    size: int
    active_tokens: int
    created_at: str


class ListFilesResponse(BaseModel):
    files: List[FileInfo]
    total_files: int


# =========================
# Routes
# =========================
@app.post("/download", response_model=DownloadAck)
@limiter.limit("10/minute")
async def download(
    request: Request, req: DownloadReq, bg: BackgroundTasks, _: bool = Depends(verify_api_key)
):
    """Download media from URL"""
    logger.info(f"Download request: {req.url} with tag {req.tag}")

    if not req.url or not isinstance(req.url, str):
        raise HTTPException(status_code=400, detail="Missing url")

    # resolve filename
    expected = req.expected_name or f"{req.tag}.mp4"
    expected = sanitize_filename(expected)
    if not expected.lower().endswith(".mp4"):
        expected += ".mp4"

    # pick destination
    dest = (req.dest or DEFAULT_DEST).upper()
    if dest == "DRIVE" and not DRIVE_ENABLED:
        raise HTTPException(
            status_code=400, detail="Drive not configured; use LOCAL or enable Drive"
        )

    job_set(req.tag, status="queued", expected_name=expected, dest=dest)
    bg.add_task(worker_job, req, expected, dest)

    logger.info(f"Download job queued: {req.tag}")
    return DownloadAck(accepted=True, tag=req.tag, expected_name=expected, note="processing")


@app.get("/status")
@limiter.limit("60/minute")
def get_status(request: Request, tag: str = Query(...)):
    """Get download job status"""
    rec = JOBS.get(tag)
    if not rec:
        return JSONResponse({"tag": tag, "status": "unknown"}, status_code=404)
    return {"tag": tag, "status": rec.get("status"), "dest": rec.get("dest")}


@app.get("/result")
@limiter.limit("30/minute")
def get_result(request: Request, tag: str = Query(...)):
    """Get download job result"""
    rec = JOBS.get(tag)
    if not rec:
        return JSONResponse({"tag": tag, "status": "unknown"}, status_code=404)
    st = rec.get("status")
    payload = rec.get("payload") or {}
    if st == "ready":
        return JSONResponse({"tag": tag, "status": "ready", **payload}, status_code=200)
    if st == "error":
        return JSONResponse(
            {
                "tag": tag,
                "status": "error",
                "error_message": payload.get("error_message", "unknown"),
            },
            status_code=500,
        )
    return JSONResponse({"tag": tag, "status": st or "queued"}, status_code=202)


@app.post("/mint", response_model=MintTokenResponse)
@limiter.limit("30/minute")
def mint_tokens(
    request: Request, 
    req: MintTokenReq, 
    _: bool = Depends(verify_api_key)
):
    """
    Mint additional one-time tokens for an existing file.
    Requires API key if configured.
    """
    logger.info(f"Minting {req.count} tokens for file {req.file_id}")
    
    try:
        urls = mint_additional_tokens(
            file_id=req.file_id,
            count=req.count,
            ttl_sec=req.ttl_sec,
            tag=req.tag
        )
        
        effective_ttl = req.ttl_sec if req.ttl_sec is not None else ONCE_TOKEN_TTL_SEC
        
        logger.info(f"Successfully minted {len(urls)} tokens for file {req.file_id}")
        return MintTokenResponse(
            success=True,
            file_id=req.file_id,
            tokens_created=len(urls),
            urls=urls,
            expires_in_sec=effective_ttl
        )
        
    except FileNotFoundError as e:
        logger.warning(f"File not found for minting: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error minting tokens: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mint tokens: {str(e)}")


@app.get("/files", response_model=ListFilesResponse)
@limiter.limit("30/minute")
def list_files(
    request: Request,
    _: bool = Depends(verify_api_key)
):
    """
    List available files that can have additional tokens minted.
    Requires API key if configured.
    """
    files = []
    
    for file_id, file_info in FILE_REGISTRY.items():
        if os.path.exists(file_info["path"]):
            files.append(FileInfo(
                file_id=file_id,
                filename=os.path.basename(file_info["path"]),
                size=file_info["size"],
                active_tokens=len(file_info["tokens"]),
                created_at=datetime.fromtimestamp(file_info["created_at"]).isoformat()
            ))
    
    return ListFilesResponse(
        files=files,
        total_files=len(files)
    )


@app.get("/once/{token}")
@limiter.limit("30/minute")
def serve_single_use(
    request: Request, token: str, range_header: Optional[str] = Header(default=None, alias="Range")
):
    """
    Streams the file ONCE (supports Range). After all concurrent streams finish,
    the file is deleted and the token is invalidated.
    """
    logger.info(f"Serving single-use file with token: {token}")

    meta = ONCE_TOKENS.get(token)
    if not meta:
        raise HTTPException(status_code=404, detail="Expired or invalid link")

    path = meta["path"]
    if not os.path.exists(path):
        ONCE_TOKENS.pop(token, None)
        raise HTTPException(status_code=404, detail="File not found")

    size = meta["size"]
    meta["last_seen"] = time.time()

    # defaults
    start, end = 0, size - 1
    status_code = 200
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
        "Content-Disposition": f'inline; filename="{pathlib.Path(path).name}"',
        "Content-Type": "video/mp4",
    }

    # Range parsing
    if range_header and size > 0:
        try:
            _, rng = range_header.split("=")
            s, e = rng.split("-")
            start = int(s) if s else 0
            end = int(e) if e else (size - 1)
            if end >= size:
                end = size - 1
            if start > end or start >= size:
                raise ValueError
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
            headers["Content-Length"] = str(end - start + 1)
            status_code = 206
        except Exception:
            start, end = 0, size - 1
            headers["Content-Length"] = str(size)
            status_code = 200
    else:
        headers["Content-Length"] = str(size)

    meta["active"] += 1

    def file_iter():
        emitted_any = False
        try:
            with open(path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                chunk = 1024 * 1024  # 1 MiB
                while remaining > 0:
                    data = f.read(min(chunk, remaining))
                    if not data:
                        break
                    emitted_any = True
                    yield data
                    remaining -= len(data)
        finally:
            meta["active"] -= 1
            if emitted_any:
                meta["consumed"] = True
            if DELETE_AFTER_SERVE:
                _maybe_delete_and_purge(token)
            logger.info(f"File streaming completed for token: {token}")

    return StreamingResponse(file_iter(), status_code=status_code, headers=headers)


@app.get("/discover")
@limiter.limit("20/minute")
async def discover(
    request: Request,
    sources: str = Query(..., description="Comma-separated URLs"),
    format: str = Query("csv", description="Output format: csv, json, or ndjson"),
    limit: int = Query(100, ge=1, le=1000, description="Limit per source (1-1000)"),
    min_views: Optional[int] = Query(None, ge=0, description="Minimum view count"),
    min_duration: Optional[int] = Query(None, ge=0, description="Minimum duration in seconds"),
    max_duration: Optional[int] = Query(None, ge=0, description="Maximum duration in seconds"),
    dateafter: Optional[str] = Query(None, description="Date filter: YYYYMMDD or now-<days>days"),
    match_filter: Optional[str] = Query(None, description="Raw yt-dlp match filter expression"),
    fields: Optional[str] = Query(None, description="CSV field list"),
    filename_hint: Optional[str] = Query(None, description="Ignored, for symmetry"),
    _: bool = Depends(verify_api_key),
):
    """Discover metadata from one or more video sources without downloading."""

    # Validate sources
    source_urls = [url.strip() for url in sources.split(",") if url.strip()]
    if not source_urls:
        raise HTTPException(status_code=400, detail="No valid sources provided")

    # Validate format
    if format not in ("csv", "json", "ndjson"):
        format = "csv"  # Default to csv for invalid formats

    logger.info(f"Discover request: {len(source_urls)} sources, format={format}, limit={limit}")

    all_videos = []
    seen_ids = set()

    # Parse dateafter
    parsed_dateafter = _parse_dateafter(dateafter)

    # Synthesize match filter
    combined_match_filter = _synthesize_match_filter(match_filter, min_duration, max_duration)

    # Process each source
    for source_url in source_urls:
        try:
            # Build yt-dlp command
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--dump-json",
                "--ignore-errors",
                "--no-warnings",
                "--force-ipv4",
                "--socket-timeout",
                "30",
                "--retries",
                "10",
                "--fragment-retries",
                "50",
                "--concurrent-fragments",
                "10",
                "--user-agent",
                "Mozilla/5.0",
                "--playlist-end",
                str(limit),
            ]

            # Add optional filters
            if parsed_dateafter:
                cmd.extend(["--dateafter", parsed_dateafter])

            if min_views is not None:
                cmd.extend(["--min-views", str(min_views)])

            if combined_match_filter:
                cmd.extend(["--match-filter", combined_match_filter])

            cmd.append(source_url)

            logger.info(f"Running yt-dlp for source: {source_url}")

            # Execute command
            rc, stdout, stderr = await run(cmd, timeout=DOWNLOAD_TIMEOUT)

            # Log warnings for non-zero return codes (but continue processing)
            if rc not in (0, 1):
                logger.warning(f"yt-dlp returned rc={rc} for source {source_url}: {stderr}")

            # Parse JSON lines from stdout
            for line in stdout.strip().split("\n"):
                if not line.strip():
                    continue

                try:
                    obj = json.loads(line)

                    # Skip playlist objects, only process actual videos
                    if obj.get("_type") in ("playlist", "multi_video"):
                        continue

                    # Normalize URL field
                    obj["url"] = obj.get("webpage_url") or obj.get("url") or ""

                    # De-duplicate by ID
                    video_id = obj.get("id")
                    if video_id and video_id not in seen_ids:
                        seen_ids.add(video_id)
                        all_videos.append(obj)

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse JSON line: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error processing source {source_url}: {e}")
            continue

    # Sort by upload_date (newest first)
    def get_upload_date(video):
        upload_date = video.get("upload_date")
        if upload_date:
            try:
                return datetime.strptime(str(upload_date), "%Y%m%d")
            except ValueError:
                pass
        return datetime.min

    all_videos.sort(key=get_upload_date, reverse=True)

    logger.info(f"Discover completed: {len(all_videos)} unique videos found")

    # Format output
    if format == "csv":
        csv_data = _rows_to_csv(all_videos, fields)
        return Response(content=csv_data, media_type="text/csv")
    elif format == "json":
        return Response(content=json.dumps(all_videos, indent=2), media_type="application/json")
    elif format == "ndjson":
        ndjson_lines = [json.dumps(video) for video in all_videos]
        ndjson_content = "\n".join(ndjson_lines)
        return Response(content=ndjson_content, media_type="application/x-ndjson")


# =========================
# Worker
# =========================
async def worker_job(req: DownloadReq, expected_name: str, dest: str):
    """Enhanced worker job with logging"""
    started_iso = datetime.utcnow().isoformat()
    work_dir = tempfile.mkdtemp(prefix="dl_")
    temp_tpl = os.path.join(work_dir, f"{req.tag}.%(ext)s")
    out_local = os.path.join(work_dir, expected_name)

    logger.info(f"Starting download job {req.tag}: {req.url}")

    try:
        job_set(req.tag, status="downloading", dest=dest)

        # ---------- Hardened yt-dlp with fallbacks ----------
        sock_to = int(req.socket_timeout or 30)
        overall_to = int(req.timeout or DOWNLOAD_TIMEOUT)

        def build_quality_flags(mode: str) -> List[str]:
            if mode == "BEST_ORIGINAL":
                return ["-f", "bestvideo*+bestaudio/best", "--merge-output-format", "mp4"]
            if mode == "BEST_MP4":
                return ["-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b", "--remux-video", "mp4"]
            return ["-f", "bv*+ba/best", "--recode-video", "mp4"]  # STRICT_MP4_REENC

        common = [
            "yt-dlp",
            "--no-warnings",
            "--ignore-errors",
            "--force-ipv4",
            "--socket-timeout",
            str(sock_to),
            "--retries",
            "10",
            "--fragment-retries",
            "50",
            "--concurrent-fragments",
            "10",
            "-o",
            temp_tpl,
            req.url,
        ]
        common_ua = common + [
            "--user-agent",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        ]
        qual_flags = build_quality_flags(req.quality)

        strategies: List[List[str]] = []
        if bool(req.prefer_api):
            strategies.append(common_ua + ["--extractor-args", "rumble:use_api=1"] + qual_flags)
        strategies.append(common_ua + qual_flags)
        if req.quality != "STRICT_MP4_REENC":
            strategies.append(common_ua + build_quality_flags("STRICT_MP4_REENC"))

        attempts = int(req.retries or 3)
        last_rc, last_se = None, ""
        success = False

        logger.info(
            f"Job {req.tag}: Trying {len(strategies)} strategies with {attempts} attempts each"
        )

        for strat_idx, strat_cmd in enumerate(strategies):
            logger.info(f"Job {req.tag}: Strategy {strat_idx + 1}/{len(strategies)}")
            for attempt in range(1, attempts + 1):
                logger.info(f"Job {req.tag}: Attempt {attempt}/{attempts}")
                rc, so, se = await run(strat_cmd, timeout=overall_to)
                if rc == 0:
                    success = True
                    logger.info(
                        f"Job {req.tag}: Download successful on strategy {strat_idx + 1}, attempt {attempt}"
                    )
                    break
                last_rc, last_se = rc, se
                logger.warning(f"Job {req.tag}: Attempt {attempt} failed with rc={rc}")
                await asyncio.sleep(4 * attempt)  # 4s, 8s, 12s...
            if success:
                break

        if not success:
            err = f"yt-dlp failed (last rc={last_rc})\n{(last_se or '')[-1500:]}"
            logger.error(f"Job {req.tag}: {err}")
            job_set(req.tag, status="error", payload={"error_message": err})
            await safe_callback(
                req.callback_url or "",
                {
                    "status": "error",
                    "tag": req.tag,
                    "error_message": err,
                    "started_at": started_iso,
                    "completed_at": datetime.utcnow().isoformat(),
                },
            )
            return

        # ---------- Pick newest finished media ----------
        files = [
            f
            for f in os.listdir(work_dir)
            if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith(".part")
        ]
        files = [f for f in files if re.search(r"\.(mp4|mkv|webm|m4a|mov|mp3)$", f, re.I)]
        if not files:
            err = "no media file produced"
            logger.error(f"Job {req.tag}: {err}")
            job_set(req.tag, status="error", payload={"error_message": err})
            await safe_callback(
                req.callback_url or "",
                {
                    "status": "error",
                    "tag": req.tag,
                    "error_message": err,
                    "started_at": started_iso,
                    "completed_at": datetime.utcnow().isoformat(),
                },
            )
            return

        files.sort(key=lambda f: os.path.getmtime(os.path.join(work_dir, f)), reverse=True)
        src = os.path.join(work_dir, files[0])
        logger.info(f"Job {req.tag}: Selected file: {files[0]}")

        # ---------- Normalize to mp4 if needed ----------
        if not src.lower().endswith(".mp4") and expected_name.lower().endswith(".mp4"):
            logger.info(f"Job {req.tag}: Converting to mp4")
            rc2, _, _ = await run(["ffmpeg", "-y", "-i", src, "-c", "copy", out_local], timeout=600)
            if rc2 != 0:
                logger.warning(f"Job {req.tag}: Copy failed, trying re-encode")
                rc3, _, _ = await run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        src,
                        "-c:v",
                        "libx264",
                        "-c:a",
                        "aac",
                        "-movflags",
                        "+faststart",
                        out_local,
                    ],
                    timeout=max(1800, overall_to),
                )
                if rc3 != 0:
                    err = "ffmpeg failed"
                    logger.error(f"Job {req.tag}: {err}")
                    job_set(req.tag, status="error", payload={"error_message": err})
                    await safe_callback(
                        req.callback_url or "",
                        {
                            "status": "error",
                            "tag": req.tag,
                            "error_message": err,
                            "started_at": started_iso,
                            "completed_at": datetime.utcnow().isoformat(),
                        },
                    )
                    return
        else:
            shutil.move(src, out_local)

        # ---------- Deliver ----------
        if dest == "DRIVE":
            logger.info(f"Job {req.tag}: Uploading to Google Drive")
            try:
                folder_id = req.drive_folder or DRIVE_FOLDER_ID_DEFAULT
                if not folder_id:
                    raise RuntimeError("DRIVE_FOLDER_ID missing")
                up = drive_upload(out_local, expected_name, folder_id)
                payload = {
                    "tag": req.tag,
                    "expected_name": expected_name,
                    "drive_file_id": up["file_id"],
                    "drive_link": up.get("webViewLink"),
                    "quality": req.quality,
                    "dest": "DRIVE",
                }
                job_set(req.tag, status="ready", payload=payload)
                logger.info(f"Job {req.tag}: Successfully uploaded to Drive: {up['file_id']}")
                await safe_callback(
                    req.callback_url or "",
                    {
                        "status": "ready",
                        **payload,
                        "started_at": started_iso,
                        "completed_at": datetime.utcnow().isoformat(),
                    },
                )
            finally:
                try:
                    os.remove(out_local)
                except Exception:
                    pass
        else:
            logger.info(f"Job {req.tag}: Saving to local storage")
            
            artifacts = []
            
            # Check if we should try to extract separate audio/video
            if req.separate_audio_video and dest == "LOCAL":
                logger.info(f"Job {req.tag}: Attempting to extract separate audio/video")
                
                # Try to extract audio
                audio_name = expected_name.replace(".mp4", f"_audio.{req.audio_format}")
                audio_path = os.path.join(work_dir, audio_name)
                
                # Extract audio using ffmpeg
                audio_cmd = [
                    "ffmpeg", "-y", "-i", out_local, 
                    "-vn", "-acodec", "copy" if req.audio_format == "m4a" else "mp3",
                    audio_path
                ]
                
                rc_audio, _, _ = await run(audio_cmd, timeout=300)
                
                if rc_audio == 0 and os.path.exists(audio_path):
                    # Move audio to public directory
                    public_audio_path = os.path.join(PUBLIC_FILES_DIR, audio_name)
                    shutil.move(audio_path, public_audio_path)
                    
                    # Create tokens for audio
                    audio_urls = make_multiple_use_urls(
                        audio_name, 
                        tag=f"{req.tag}_audio", 
                        count=req.token_count or 1,
                        ttl_sec=req.custom_ttl
                    )
                    
                    artifacts.append({
                        "type": "audio",
                        "filename": audio_name,
                        "urls": audio_urls,
                        "format": req.audio_format
                    })
                    logger.info(f"Job {req.tag}: Audio extracted to {audio_name}")
                
                # Video file (remove audio if we successfully extracted it)
                video_name = expected_name.replace(".mp4", "_video.mp4")
                video_path = os.path.join(work_dir, video_name)
                
                if rc_audio == 0:
                    # Create video-only version
                    video_cmd = [
                        "ffmpeg", "-y", "-i", out_local,
                        "-an", "-vcodec", "copy",
                        video_path
                    ]
                    
                    rc_video, _, _ = await run(video_cmd, timeout=300)
                    
                    if rc_video == 0 and os.path.exists(video_path):
                        # Move video to public directory
                        public_video_path = os.path.join(PUBLIC_FILES_DIR, video_name)
                        shutil.move(video_path, public_video_path)
                        
                        # Create tokens for video
                        video_urls = make_multiple_use_urls(
                            video_name,
                            tag=f"{req.tag}_video",
                            count=req.token_count or 1,
                            ttl_sec=req.custom_ttl
                        )
                        
                        artifacts.append({
                            "type": "video",
                            "filename": video_name,
                            "urls": video_urls,
                            "format": "mp4"
                        })
                        logger.info(f"Job {req.tag}: Video extracted to {video_name}")
                        
                        # Remove original combined file
                        try:
                            os.remove(out_local)
                        except Exception:
                            pass
                    else:
                        # Video extraction failed, fall back to combined file
                        logger.warning(f"Job {req.tag}: Video extraction failed, using combined file")
                        req.separate_audio_video = False
            
            # If not separating or if separation failed, handle as single file
            if not req.separate_audio_video or not artifacts:
                public_path = os.path.join(PUBLIC_FILES_DIR, expected_name)
                shutil.move(out_local, public_path)
                
                # Create multiple tokens if requested
                once_urls = make_multiple_use_urls(
                    expected_name,
                    tag=req.tag,
                    count=req.token_count or 1,
                    ttl_sec=req.custom_ttl
                )
                
                artifacts.append({
                    "type": "combined",
                    "filename": expected_name,
                    "urls": once_urls,
                    "format": "mp4"
                })
            
            # Prepare response payload
            effective_ttl = req.custom_ttl if req.custom_ttl is not None else ONCE_TOKEN_TTL_SEC
            
            if len(artifacts) == 1 and artifacts[0]["type"] == "combined":
                # Legacy single-file response format for backward compatibility
                payload = {
                    "tag": req.tag,
                    "expected_name": expected_name,
                    "once_url": artifacts[0]["urls"][0],  # First URL for backward compatibility
                    "once_urls": artifacts[0]["urls"],  # All URLs
                    "expires_in_sec": effective_ttl,
                    "quality": req.quality,
                    "dest": "LOCAL",
                }
            else:
                # Multi-artifact response format
                payload = {
                    "tag": req.tag,
                    "expected_name": expected_name,
                    "artifacts": artifacts,
                    "expires_in_sec": effective_ttl,
                    "quality": req.quality,
                    "dest": "LOCAL",
                    "separate_audio_video": req.separate_audio_video,
                }
            
            job_set(req.tag, status="ready", payload=payload)
            
            if len(artifacts) == 1:
                logger.info(f"Job {req.tag}: File ready with {len(artifacts[0]['urls'])} URLs")
            else:
                logger.info(f"Job {req.tag}: {len(artifacts)} artifacts ready")
            
            await safe_callback(
                req.callback_url or "",
                {
                    "status": "ready",
                    **payload,
                    "started_at": started_iso,
                    "completed_at": datetime.utcnow().isoformat(),
                },
            )

    except Exception as e:
        err = str(e)
        logger.error(f"Job {req.tag}: Unexpected error: {err}")
        job_set(req.tag, status="error", payload={"error_message": err})
        await safe_callback(
            req.callback_url or "",
            {
                "status": "error",
                "tag": req.tag,
                "error_message": err,
                "started_at": started_iso,
                "completed_at": datetime.utcnow().isoformat(),
            },
        )
    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


# =========================
# Main
# =========================
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=APP_PORT, reload=False)
