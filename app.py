import os, re, json, asyncio, shutil, tempfile, uuid, pathlib, time, threading, base64
from datetime import datetime
from typing import Optional, Literal, List, Dict, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException, Header, Query, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from loguru import logger
import sys

import httpx
import uvicorn

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
DELETE_AFTER_SERVE = (os.getenv("DELETE_AFTER_SERVE", "true").lower() == "true")

# Google Drive (optional)
DRIVE_ENABLED = (os.getenv("DRIVE_ENABLED") or ("oauth" if os.getenv("GOOGLE_REFRESH_TOKEN") else "")).lower() in ("oauth","service")
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
# meta: { path, size, active, consumed, last_seen, expiry, tag }
ONCE_TOKENS: Dict[str, Dict[str, Any]] = {}

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
        try: proc.kill()
        except Exception: pass
        return 124, "", "Timeout"
    return proc.returncode, so.decode(errors="ignore"), se.decode(errors="ignore")

async def safe_callback(url: str, payload: dict):
    if not url: return
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

def make_single_use_url(filename: str, tag: str) -> str:
    path = os.path.join(PUBLIC_FILES_DIR, filename)
    size, _ = _file_stat(path)
    token = uuid.uuid4().hex
    ONCE_TOKENS[token] = {
        "path": path,
        "size": size,
        "active": 0,         # concurrent streams
        "consumed": False,   # true once any bytes were sent
        "last_seen": time.time(),
        "expiry": time.time() + ONCE_TOKEN_TTL_SEC,
        "tag": tag,
    }
    return _build_once_url(token)

def _maybe_delete_and_purge(token: str):
    meta = ONCE_TOKENS.get(token)
    if not meta: return
    if meta["active"] == 0 and meta["consumed"]:
        try:
            if os.path.exists(meta["path"]):
                os.remove(meta["path"])
        except Exception:
            pass
        ONCE_TOKENS.pop(token, None)

def _janitor_loop():
    while True:
        try:
            now = time.time()
            expired = []
            for tk, meta in list(ONCE_TOKENS.items()):
                if now > meta.get("expiry", 0):
                    expired.append(tk)
            for tk in expired:
                m = ONCE_TOKENS.pop(tk, None)
                if m and os.path.exists(m["path"]) and not m["consumed"]:
                    try: os.remove(m["path"])
                    except Exception: pass
        except Exception:
            pass
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
        scopes = (os.getenv("GOOGLE_SCOPES") or "https://www.googleapis.com/auth/drive.file").split()
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
        raise RuntimeError("Service auth selected but DRIVE_SERVICE_ACCOUNT_JSON(_B64) not provided")
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
        svc.permissions().create(fileId=file["id"], body={"role": "reader", "type": "anyone"}).execute()
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
            }
        }
        
        # Check if any critical checks failed
        if any(check == "unhealthy" for check in health_status["checks"].values() if check != "disabled"):
            health_status["status"] = "unhealthy"
            return JSONResponse(health_status, status_code=503)
            
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status_code=503)

@app.get("/metrics")
@limiter.limit("30/minute")
def metrics(request: Request):
    """Basic metrics endpoint for monitoring"""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return StreamingResponse(
            iter([generate_latest()]), 
            media_type=CONTENT_TYPE_LATEST
        )
    except ImportError:
        # Fallback metrics if prometheus client not available
        return {
            "jobs": {
                "total": len(JOBS),
                "by_status": {
                    status: len([j for j in JOBS.values() if j.get("status") == status])
                    for status in ["queued", "downloading", "ready", "error"]
                }
            },
            "tokens": {
                "active": len(ONCE_TOKENS),
                "consumed": len([t for t in ONCE_TOKENS.values() if t.get("consumed", False)])
            },
            "timestamp": datetime.utcnow().isoformat()
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
    dest: Optional[Literal["LOCAL","DRIVE"]] = None
    drive_folder: Optional[str] = None
    # hardening knobs
    retries: Optional[int] = 3            # times per strategy
    socket_timeout: Optional[int] = 30    # yt-dlp --socket-timeout
    prefer_api: Optional[bool] = True     # try rumble:use_api first

class DownloadAck(BaseModel):
    accepted: bool
    tag: str
    expected_name: Optional[str]
    note: str

# =========================
# Routes
# =========================
@app.post("/download", response_model=DownloadAck)
@limiter.limit("10/minute")
async def download(request: Request, req: DownloadReq, bg: BackgroundTasks, _: bool = Depends(verify_api_key)):
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
        raise HTTPException(status_code=400, detail="Drive not configured; use LOCAL or enable Drive")

    job_set(req.tag, status="queued", expected_name=expected, dest=dest)
    bg.add_task(worker_job, req, expected, dest)
    
    logger.info(f"Download job queued: {req.tag}")
    return DownloadAck(accepted=True, tag=req.tag, expected_name=expected, note="processing")

# =========================
# Status Check Functions
# =========================
def _check_storage_config() -> Dict[str, Any]:
    """Check local storage configuration and state"""
    try:
        configured = bool(PUBLIC_FILES_DIR)
        accessible = os.path.exists(PUBLIC_FILES_DIR) and os.access(PUBLIC_FILES_DIR, os.W_OK)
        
        if configured and accessible:
            state = "active"
        elif configured:
            state = "degraded"  # Configured but not accessible
        else:
            state = "inactive"  # Not configured
            
        return {
            "configured": configured,
            "state": state,
            "details": {
                "directory_exists": os.path.exists(PUBLIC_FILES_DIR) if configured else None,
                "writable": accessible if configured else None
            }
        }
    except Exception as e:
        logger.error(f"Storage config check failed: {e}")
        return {
            "configured": False,
            "state": "inactive",
            "details": {"error": "check_failed"}
        }


def _check_drive_config() -> Dict[str, Any]:
    """Check Google Drive configuration and state"""
    try:
        if not DRIVE_ENABLED:
            return {"configured": False, "state": "inactive", "details": {"enabled": False}}
        
        configured = True
        
        # Check if required environment variables are present
        if DRIVE_AUTH == "oauth":
            required_vars = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                return {
                    "configured": False, 
                    "state": "inactive",
                    "details": {"auth_type": "oauth", "missing_config": True}
                }
        elif DRIVE_AUTH == "service":
            service_json = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON")
            service_json_b64 = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON_B64")
            if not service_json and not service_json_b64:
                return {
                    "configured": False,
                    "state": "inactive", 
                    "details": {"auth_type": "service", "missing_config": True}
                }
        
        # Try to build drive service to test connectivity
        try:
            _build_drive()
            state = "active"
            details = {"auth_type": DRIVE_AUTH, "connectivity": "ok"}
        except Exception as e:
            state = "degraded"  # Configured but connection failed
            details = {"auth_type": DRIVE_AUTH, "connectivity": "failed"}
            
        return {"configured": configured, "state": state, "details": details}

    except Exception as e:
        logger.error(f"Drive config check failed: {e}")
        return {
            "configured": False,
            "state": "inactive",
            "details": {"error": "check_failed"}
        }


def _check_security_config() -> Dict[str, Any]:
    """Check security configuration and state"""
    try:
        api_key_configured = bool(API_KEY)
        cors_configured = CORS_ORIGINS != ["*"]  # Default is "*", so configured means restricted
        
        if api_key_configured and cors_configured:
            state = "active"  # Both security measures enabled
        elif api_key_configured or cors_configured:
            state = "degraded"  # Partial security
        else:
            state = "degraded"  # No additional security (still functional)
            
        return {
            "configured": api_key_configured or cors_configured,
            "state": state,
            "details": {
                "api_key_protection": api_key_configured,
                "cors_restricted": cors_configured
            }
        }
    except Exception as e:
        logger.error(f"Security config check failed: {e}")
        return {
            "configured": False,
            "state": "inactive",
            "details": {"error": "check_failed"}
        }


def _check_rate_limiting_config() -> Dict[str, Any]:
    """Check rate limiting configuration and state"""
    try:
        configured = bool(RATE_LIMIT_REQUESTS)
        
        # Rate limiting is always active if configured (slowapi handles it)
        state = "active" if configured else "degraded"
        
        return {
            "configured": configured,
            "state": state,
            "details": {
                "limit_setting": RATE_LIMIT_REQUESTS if configured else None
            }
        }
    except Exception as e:
        logger.error(f"Rate limiting config check failed: {e}")
        return {
            "configured": False,
            "state": "inactive",
            "details": {"error": "check_failed"}
        }


@app.get("/status")
@limiter.limit("60/minute")
def get_status(request: Request, tag: Optional[str] = Query(None)):
    """Get system status or download job status"""
    if tag is None:
        # System status - check configuration and state of core services
        try:
            status_checks = {
                "storage": _check_storage_config(),
                "drive": _check_drive_config(),
                "security": _check_security_config(),
                "rate_limiting": _check_rate_limiting_config(),
            }
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            # Return error state if status checks fail
            return {
                "service": "Railway yt-dlp Service",
                "version": "1.0.0",
                "state": "inactive",
                "timestamp": datetime.utcnow().isoformat(),
                "error": "status_check_failed"
            }
        
        # Determine overall state based on critical vs optional components
        storage_state = status_checks["storage"]["state"]
        rate_limiting_state = status_checks["rate_limiting"]["state"]
        drive_state = status_checks["drive"]["state"]  
        security_state = status_checks["security"]["state"]
        
        # Storage is critical - if it's inactive, whole service is inactive
        if storage_state == "inactive":
            overall_state = "inactive"
        # If any component is degraded, service is degraded
        elif any(state == "degraded" for state in [storage_state, rate_limiting_state, drive_state, security_state]):
            overall_state = "degraded"
        # Drive being inactive is OK if not enabled (doesn't affect service)
        # Security being degraded is OK for basic functionality
        else:
            overall_state = "active"
        
        return {
            "service": "Railway yt-dlp Service",
            "version": "1.0.0",
            "state": overall_state,
            "timestamp": datetime.utcnow().isoformat(),
            "components": status_checks
        }
    else:
        # Job status (existing functionality)
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
        return JSONResponse({"tag": tag, "status": "error", "error_message": payload.get("error_message","unknown")}, status_code=500)
    return JSONResponse({"tag": tag, "status": st or "queued"}, status_code=202)

@app.get("/once/{token}")
@limiter.limit("30/minute")
def serve_single_use(request: Request, token: str, range_header: Optional[str] = Header(default=None, alias="Range")):
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
            if end >= size: end = size - 1
            if start > end or start >= size: raise ValueError
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
            "--socket-timeout", str(sock_to),
            "--retries", "10",
            "--fragment-retries", "50",
            "--concurrent-fragments", "10",
            "-o", temp_tpl,
            req.url,
        ]
        common_ua = common + ["--user-agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"]
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
        
        logger.info(f"Job {req.tag}: Trying {len(strategies)} strategies with {attempts} attempts each")
        
        for strat_idx, strat_cmd in enumerate(strategies):
            logger.info(f"Job {req.tag}: Strategy {strat_idx + 1}/{len(strategies)}")
            for attempt in range(1, attempts + 1):
                logger.info(f"Job {req.tag}: Attempt {attempt}/{attempts}")
                rc, so, se = await run(strat_cmd, timeout=overall_to)
                if rc == 0:
                    success = True
                    logger.info(f"Job {req.tag}: Download successful on strategy {strat_idx + 1}, attempt {attempt}")
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
            await safe_callback(req.callback_url or "", {
                "status":"error","tag":req.tag,"error_message":err,
                "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
            })
            return

        # ---------- Pick newest finished media ----------
        files = [
            f for f in os.listdir(work_dir)
            if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith(".part")
        ]
        files = [f for f in files if re.search(r"\.(mp4|mkv|webm|m4a|mov|mp3)$", f, re.I)]
        if not files:
            err = "no media file produced"
            logger.error(f"Job {req.tag}: {err}")
            job_set(req.tag, status="error", payload={"error_message": err})
            await safe_callback(req.callback_url or "", {
                "status":"error","tag":req.tag,"error_message":err,
                "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
            })
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
                    ["ffmpeg", "-y", "-i", src, "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", out_local],
                    timeout=max(1800, overall_to)
                )
                if rc3 != 0:
                    err = "ffmpeg failed"
                    logger.error(f"Job {req.tag}: {err}")
                    job_set(req.tag, status="error", payload={"error_message": err})
                    await safe_callback(req.callback_url or "", {
                        "status":"error","tag":req.tag,"error_message":err,
                        "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
                    })
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
                await safe_callback(req.callback_url or "", {
                    "status":"ready", **payload,
                    "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
                })
            finally:
                try: os.remove(out_local)
                except Exception: pass
        else:
            logger.info(f"Job {req.tag}: Saving to local storage")
            public_path = os.path.join(PUBLIC_FILES_DIR, expected_name)
            shutil.move(out_local, public_path)
            once_url = make_single_use_url(os.path.basename(public_path), tag=req.tag)
            payload = {
                "tag": req.tag,
                "expected_name": expected_name,
                "once_url": once_url,
                "expires_in_sec": ONCE_TOKEN_TTL_SEC,
                "quality": req.quality,
                "dest": "LOCAL",
            }
            job_set(req.tag, status="ready", payload=payload)
            logger.info(f"Job {req.tag}: File ready at {once_url}")
            await safe_callback(req.callback_url or "", {
                "status":"ready", **payload,
                "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
            })

    except Exception as e:
        err = str(e)
        logger.error(f"Job {req.tag}: Unexpected error: {err}")
        job_set(req.tag, status="error", payload={"error_message": err})
        await safe_callback(req.callback_url or "", {
            "status":"error","tag":req.tag,"error_message":err,
            "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
        })
    finally:
        try: shutil.rmtree(work_dir, ignore_errors=True)
        except Exception: pass

# =========================
# Main
# =========================
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=APP_PORT, reload=False)
