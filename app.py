import os, re, time, subprocess
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Header, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests

# ======================
# Config
# ======================
VOLUME_DIR = Path("/data")                 # Attach a Railway Volume mounted at /data
STORE_DIR  = VOLUME_DIR / "videos"
STORE_DIR.mkdir(parents=True, exist_ok=True)

# Accept rumble.com (any subdomain), must start with http(s)
RUMBLE_RE   = re.compile(r"^https?://([a-z0-9-]+\.)?rumble\.com(/|$)", re.I)
DEFAULT_FMT = "bv*+ba/best"                # best video+audio fallback
TIMEOUT_SEC = 30 * 60                      # 30 min per download

# Optional: set in Railway variables
BASE_URL   = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")  # e.g. https://your-service.up.railway.app
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")                    # if set, require Bearer token on POST endpoints

# Retention (optional)
MAX_KEEP  = int(os.getenv("MAX_KEEP", "0"))                 # 0 = disabled; else keep newest N files
MAX_BYTES = int(os.getenv("MAX_BYTES", "0"))                # 0 = disabled; else cap total bytes

# ======================
# Models
# ======================
class Job(BaseModel):
    url: str
    tag: Optional[str] = None
    callback_url: Optional[str] = None

class Batch(BaseModel):
    items: List[Job]

# ======================
# Helpers
# ======================
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

def public_url(filename: str, request: Optional[Request] = None) -> str:
    if BASE_URL:
        return f"{BASE_URL}/files/{filename}"
    if request:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host", request.url.hostname)
        return f"{scheme}://{host}/files/{filename}"
    return f"/files/{filename}"

def prune_store():
    # count limit
    files = sorted(STORE_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if MAX_KEEP and len(files) > MAX_KEEP:
        for p in files[MAX_KEEP:]:
            try: p.unlink()
            except: pass
    # size limit
    if MAX_BYTES:
        files = sorted(STORE_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        total = sum(p.stat().st_size for p in files)
        if total > MAX_BYTES:
            for p in reversed(files):  # oldest first
                if total <= MAX_BYTES: break
                try:
                    sz = p.stat().st_size
                    p.unlink()
                    total -= sz
                except:
                    pass

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

def send_callback(cb_url: str, payload: dict):
    try:
        r = requests.post(cb_url, json=payload, timeout=20)
        print(f"[CALLBACK] POST {cb_url} -> {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"[CALLBACK] ERROR to {cb_url}: {e}")

# ======================
# API
# ======================
api = FastAPI()

@api.on_event("startup")
def _startup():
    try:
        prune_store()
    except Exception as e:
        print("[PRUNE_ERR]", e)

@api.get("/health")
def health():
    return {
        "ok": True,
        "store": str(STORE_DIR),
        "exists": STORE_DIR.exists(),
        "files": len(list(STORE_DIR.glob("*.mp4")))
    }

@api.get("/files")
def list_files(limit: int = Query(100, ge=1, le=1000)):
    entries = []
    for p in sorted(STORE_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        entries.append({
            "file_name": p.name,
            "size_bytes": p.stat().st_size,
            "updated_at": int(p.stat().st_mtime),
            "url": public_url(p.name)
        })
    return {"count": len(entries), "files": entries}

@api.get("/files/{filename}")
def get_file(filename: str):
    path = STORE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path=str(path), media_type="video/mp4", filename=filename)

@api.delete("/files/{filename}")
def delete_file(filename: str, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    path = STORE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    path.unlink()
    return {"deleted": filename}

@api.post("/download")
def enqueue(job: Job, bg: BackgroundTasks, request: Request, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    if not RUMBLE_RE.match(job.url or ""):
        raise HTTPException(status_code=400, detail="Provide a valid rumble.com URL")
    tag = job.tag or f"job_{int(time.time())}"

    def _task():
        try:
            mp4 = run_download(job.url, tag)
            payload = {
                "status": "ready",
                "file_url": public_url(mp4.name, request),
                "file_name": mp4.name,
                "rumble_url": job.url,
                "tag": tag,
                "run_url": ""
            }
            if job.callback_url:
                send_callback(job.callback_url, payload)
            print(f"[DONE] {payload}")
        except Exception as e:
            err_payload = {"status": "error", "error": str(e), "rumble_url": job.url, "tag": tag}
            if job.callback_url:
                send_callback(job.callback_url, err_payload)
            print(f"[ERROR] {e}")

    bg.add_task(_task)
    print(f"[QUEUE] url={job.url} tag={tag}")
    return {"queued": True, "tag": tag, "url": job.url}

@api.post("/download/wait")
def download_wait(job: Job, request: Request, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    if not RUMBLE_RE.match(job.url or ""):
        raise HTTPException(status_code=400, detail="Provide a valid rumble.com URL")
    tag = job.tag or f"job_{int(time.time())}"
    mp4 = run_download(job.url, tag)
    payload = {
        "status": "ready",
        "file_url": public_url(mp4.name, request),
        "file_name": mp4.name,
        "rumble_url": job.url,
        "tag": tag,
        "run_url": ""
    }
    print(f"[SYNC_DONE] {payload}")
    return payload

@api.post("/download/batch")
def download_batch(batch: Batch, bg: BackgroundTasks, request: Request, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    results = []
    for j in batch.items:
        if not RUMBLE_RE.match(j.url or ""):
            results.append({"queued": False, "url": j.url, "reason": "invalid rumble url"})
            continue
        tag = j.tag or f"job_{int(time.time())}"
        def _task(job=j, tag=tag):
            try:
                mp4 = run_download(job.url, tag)
                payload = {
                    "status": "ready",
                    "file_url": public_url(mp4.name, request),
                    "file_name": mp4.name,
                    "rumble_url": job.url,
                    "tag": tag,
                    "run_url": ""
                }
                if job.callback_url:
                    send_callback(job.callback_url, payload)
                print(f"[DONE] {payload}")
            except Exception as e:
                err_payload = {"status": "error", "error": str(e), "rumble_url": job.url, "tag": tag}
                if job.callback_url:
                    send_callback(job.callback_url, err_payload)
                print(f"[ERROR] {e}")
        bg.add_task(_task)
        results.append({"queued": True, "tag": tag, "url": j.url})
    return {"queued": results}
