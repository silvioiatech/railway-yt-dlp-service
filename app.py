import os, re, time, subprocess
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Header
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import requests

# -------- config --------
VOLUME_DIR = Path("/data")             # Railway Volume mount
STORE_DIR  = VOLUME_DIR / "videos"     # where MP4s are kept
STORE_DIR.mkdir(parents=True, exist_ok=True)

RUMBLE_RE   = re.compile(r"^https?://(www\.)?rumble\.com/", re.I)
DEFAULT_FMT = 'bv*+ba/best'
TIMEOUT_SEC = 30 * 60                  # 30 mins
BASE_URL    = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")  # e.g. https://railway-yt-dlp-service-production.up.railway.app
AUTH_TOKEN  = os.getenv("AUTH_TOKEN", "")  # optional bearer for POST endpoints

# -------- models --------
class Job(BaseModel):
    url: str
    tag: Optional[str] = None
    callback_url: Optional[str] = None

class Batch(BaseModel):
    items: List[Job]

# -------- helpers --------
def sh(cmd, timeout=None):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        return 124, "", "timeout"
    return p.returncode, out, err

def newest(prefix: str):
    files = sorted(STORE_DIR.glob(f"{prefix}*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def check_auth(auth_header: Optional[str]):
    if not AUTH_TOKEN:
        return
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="invalid token")

def run_download(url: str, tag: str) -> Path:
    safe_tag = re.sub(r"[^A-Za-z0-9._-]+", "_", tag) if tag else "job"
    out_tpl = str(STORE_DIR / f"{safe_tag}_%(title).200B [%(id)s].%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-part",
        "--merge-output-format", "mp4",
        "-f", DEFAULT_FMT,
        "-o", out_tpl,
        "--restrict-filenames",
        "--write-info-json",
        "--write-thumbnail",
        url,
    ]
    rc, out, err = sh(cmd, timeout=TIMEOUT_SEC)
    if rc != 0:
        raise RuntimeError(f"yt-dlp failed rc={rc}\nstdout:\n{out[-400:]}\nstderr:\n{err[-400:]}")
    mp4 = newest(f"{safe_tag}_")
    if not mp4:
        raise RuntimeError("download ok but mp4 not found")
    return mp4

def file_public_url(filename: str, request: Optional[Request] = None) -> str:
    # Prefer PUBLIC_BASE_URL if set; else infer from request
    if BASE_URL:
        return f"{BASE_URL}/files/{filename}"
    if request:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host", request.url.hostname)
        base = f"{scheme}://{host}"
        # If you’re behind a subpath (e.g., none here), add it.
        return f"{base}/files/{filename}"
    return f"/files/{filename}"

def send_callback(cb_url: str, payload: dict):
    try:
        r = requests.post(cb_url, json=payload, timeout=20)
        print(f"[CALLBACK] POST {cb_url} -> {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"[CALLBACK] ERROR to {cb_url}: {e}")

# -------- API --------
api = FastAPI()

@api.get("/health")
def health():
    return {"ok": True, "store": str(STORE_DIR), "exists": STORE_DIR.exists()}

@api.get("/files/{filename}")
def get_file(filename: str):
    # Simple download endpoint; suits n8n to fetch/save elsewhere.
    file_path = STORE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path=str(file_path), media_type="video/mp4", filename=filename)

@api.post("/download")
def enqueue(job: Job, bg: BackgroundTasks, request: Request, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    if not RUMBLE_RE.match(job.url or ""):
        raise HTTPException(status_code=400, detail="Provide a valid rumble.com URL")
    tag = job.tag or f"job_{int(time.time())}"
    # wrap background task to include request for URL inference
    def _task():
        try:
            mp4 = run_download(job.url, tag)
            public_url = file_public_url(mp4.name, request)
            payload = {
                "status": "ready",
                "file_url": public_url,
                "file_name": mp4.name,
                "rumble_url": job.url,
                "tag": tag,
                "run_url": ""
            }
            if job.callback_url:
                send_callback(job.callback_url, payload)
        except Exception as e:
            err_payload = {
                "status": "error",
                "error": str(e),
                "rumble_url": job.url,
                "tag": tag
            }
            if job.callback_url:
                send_callback(job.callback_url, err_payload)
            print(f"[ERROR] {e}")

    bg.add_task(_task)
    return {"queued": True, "tag": tag, "url": job.url}

@api.post("/download/wait")
def download_wait(job: Job, request: Request, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    if not RUMBLE_RE.match(job.url or ""):
        raise HTTPException(status_code=400, detail="Provide a valid rumble.com URL")
    tag = job.tag or f"job_{int(time.time())}"
    mp4 = run_download(job.url, tag)
    public_url = file_public_url(mp4.name, request)
    return {
        "status": "ready",
        "file_url": public_url,
        "file_name": mp4.name,
        "rumble_url": job.url,
        "tag": tag,
        "run_url": ""
    }
