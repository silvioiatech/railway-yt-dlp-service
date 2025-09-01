import os, re, time, json, subprocess
from pathlib import Path
from typing import Optional, List
from datetime import timedelta

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Header, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests

# Google Drive (service account)
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ======================
# Config
# ======================
# Optional Railway volume for temp files
VOLUME_DIR = Path("/data")
STORE_DIR  = (VOLUME_DIR / "videos")
STORE_DIR.mkdir(parents=True, exist_ok=True)

# Accept rumble.com (any subdomain)
RUMBLE_RE   = re.compile(r"^https?://([a-z0-9-]+\.)?rumble\.com(/|$)", re.I)
TIMEOUT_SEC = int(os.getenv("TIMEOUT_SEC", "1800"))  # default 30 min

# Quality mode: BEST_ORIGINAL | BEST_MP4 | STRICT_MP4_REENC
QUALITY_MODE = os.getenv("QUALITY_MODE", "BEST_ORIGINAL").upper().strip()

# Fallback local base URL (only used if Drive upload fails)
BASE_URL   = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

# Optional bearer for POST endpoints
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")

# Retention for local volume (optional)
MAX_KEEP  = int(os.getenv("MAX_KEEP", "0"))   # 0 = disabled
MAX_BYTES = int(os.getenv("MAX_BYTES", "0"))  # 0 = disabled
DELETE_LOCAL_AFTER_UPLOAD = os.getenv("DELETE_LOCAL_AFTER_UPLOAD", "true").lower() == "true"

# ---- Google Drive (Service Account) ----
# Paste the full JSON key into DRIVE_SERVICE_ACCOUNT_JSON
DRIVE_SA_JSON = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON", "")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "")  # target folder (share with the SA email)
DRIVE_PUBLIC = os.getenv("DRIVE_PUBLIC", "true").lower() == "true"

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]  # allow permission change when making public

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
    files = sorted(STORE_DIR.glob(f"{prefix}*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
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
    files = sorted(STORE_DIR.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if MAX_KEEP and len(files) > MAX_KEEP:
        for p in files[MAX_KEEP:]:
            try: p.unlink()
            except: pass
    if MAX_BYTES:
        files = sorted(STORE_DIR.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
        total = sum(p.stat().st_size for p in files)
        if total > MAX_BYTES:
            for p in reversed(files):
                if total <= MAX_BYTES: break
                try:
                    sz = p.stat().st_size
                    p.unlink()
                    total -= sz
                except: pass

# ----- Drive client -----
def drive_service():
    if not DRIVE_SA_JSON or not DRIVE_FOLDER_ID:
        return None
    info = json.loads(DRIVE_SA_JSON)
    creds = Credentials.from_service_account_info(info, scopes=DRIVE_SCOPES)
    # cache_discovery=False avoids warnings on serverless
    return build("drive", "v3", credentials=creds, cache_discovery=False)

DRIVE = drive_service()

def upload_to_drive(local_path: Path, out_name: str) -> dict:
    """
    Uploads the file to Google Drive into DRIVE_FOLDER_ID.
    Returns dict with {id, webViewLink, webContentLink, url} where url is a good link to store.
    """
    if not DRIVE:
        raise RuntimeError("Drive not configured: set DRIVE_SERVICE_ACCOUNT_JSON and DRIVE_FOLDER_ID")

    file_metadata = {"name": out_name}
    if DRIVE_FOLDER_ID:
        file_metadata["parents"] = [DRIVE_FOLDER_ID]

    media = MediaFileUpload(str(local_path), mimetype="video/mp4", resumable=True)
    created = DRIVE.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink, webContentLink"
    ).execute()

    file_id = created["id"]

    if DRIVE_PUBLIC:
        # Make file publicly readable
        try:
            DRIVE.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
                fields="id"
            ).execute()
        except Exception as e:
            print(f"[DRIVE] set public failed: {e}")

    # Refresh links after permission (some fields may be empty right after create)
    fetched = DRIVE.files().get(fileId=file_id, fields="id, name, webViewLink, webContentLink").execute()

    # Pick a stable link to store (webViewLink is good for humans; webContentLink direct-download may be gated)
    final_url = fetched.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
    return {
        "id": file_id,
        "name": fetched.get("name", out_name),
        "webViewLink": fetched.get("webViewLink", ""),
        "webContentLink": fetched.get("webContentLink", ""),
        "url": final_url,
    }

# ----- yt-dlp -----
def build_ytdlp_args(out_tpl: str) -> list:
    if QUALITY_MODE == "BEST_MP4":
        return [
            "yt-dlp",
            "-f", "bv*+ba/best",
            "-o", out_tpl,
            "--no-part",
            "--restrict-filenames",
            "--write-info-json",
            "--write-thumbnail",
            "-S", "ext:mp4:m4a,res,br,codec:avc",
            "--remux-video", "mp4",     # no re-encode when possible
        ]
    elif QUALITY_MODE == "STRICT_MP4_REENC":
        return [
            "yt-dlp",
            "-f", "bv*+ba/best",
            "-o", out_tpl,
            "--no-part",
            "--restrict-filenames",
            "--write-info-json",
            "--write-thumbnail",
            "--recode-video", "mp4",    # re-encode if needed (slow + lossy)
        ]
    else:  # BEST_ORIGINAL
        return [
            "yt-dlp",
            "-f", "bv*+ba/best",
            "-o", out_tpl,
            "--no-part",
            "--restrict-filenames",
            "--write-info-json",
            "--write-thumbnail",
            "-S", "res,br",
        ]

def run_download(url: str, tag: str) -> Path:
    safe_tag = re.sub(r"[^A-Za-z0-9._-]+", "_", tag) if tag else "job"
    out_tpl = str(STORE_DIR / f"{safe_tag}_%(title).200B [%(id)s].%(ext)s")
    args = build_ytdlp_args(out_tpl)

    rc, out, err = sh(args + [url], timeout=TIMEOUT_SEC)
    if rc != 0:
        raise RuntimeError(f"yt-dlp failed rc={rc}\nstdout:\n{out[-400:]}\nstderr:\n{err[-400:]}")

    produced = newest(f"{safe_tag}_")
    if not produced:
        raise RuntimeError("download ok but file not found")
    return produced

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
        "files": len(list(STORE_DIR.glob("*.*"))),
        "quality_mode": QUALITY_MODE,
        "drive_enabled": bool(DRIVE and DRIVE_FOLDER_ID),
    }

@api.get("/files")
def list_files(limit: int = Query(100, ge=1, le=1000)):
    entries = []
    for p in sorted(STORE_DIR.glob("*.*"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
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
    media_type = "video/mp4" if filename.lower().endswith(".mp4") else "application/octet-stream"
    return FileResponse(path=str(path), media_type=media_type, filename=filename)

@api.delete("/files/{filename}")
def delete_file(filename: str, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    path = STORE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    path.unlink()
    return {"deleted": filename}

def _finish_and_callback(url: str, tag: str, request: Request, callback_url: Optional[str]):
    if not RUMBLE_RE.match(url or ""):
        raise HTTPException(status_code=400, detail="Provide a valid rumble.com URL")

    mp4 = run_download(url, tag)

    # Upload to Drive first
    drive_info = None
    try:
        # Use the produced filename for Drive
        drive_info = upload_to_drive(mp4, mp4.name)
    except Exception as e:
        print(f"[DRIVE_UPLOAD_ERROR] {e}")

    final_url = None
    if drive_info and drive_info.get("url"):
        final_url = drive_info["url"]
    else:
        # fallback to serving from local volume
        final_url = public_url(mp4.name, request)

    payload = {
        "status": "ready",
        "file_url": final_url,
        "file_name": drive_info["name"] if (drive_info and drive_info.get("name")) else mp4.name,
        "drive_file_id": (drive_info or {}).get("id", ""),
        "rumble_url": url,
        "tag": tag,
        "run_url": ""
    }

    if DELETE_LOCAL_AFTER_UPLOAD and drive_info:
        try: mp4.unlink()
        except: pass

    if callback_url:
        send_callback(callback_url, payload)

    print(f"[DONE] {payload}")
    return payload

@api.post("/download")
def enqueue(job: Job, bg: BackgroundTasks, request: Request, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    if not RUMBLE_RE.match(job.url or ""):
        raise HTTPException(status_code=400, detail="Provide a valid rumble.com URL")
    tag = job.tag or f"job_{int(time.time())}"

    def _task():
        try:
            _finish_and_callback(job.url, tag, request, job.callback_url)
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
    tag = job.tag or f"job_{int(time.time())}"
    return _finish_and_callback(job.url, tag, request, job.callback_url)

@api.post("/download/batch")
def download_batch(batch: Batch, bg: BackgroundTasks, request: Request, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    results = []
    for j in batch.items:
        if not RUMBLE_RE.match(j.url or ""):
            results.append({"queued": False, "url": j.url, "reason": "invalid rumble url"})
            continue
        tag = j.tag or f"job_{int(time.time())}"
        bg.add_task(_finish_and_callback, j.url, tag, request, j.callback_url)
        results.append({"queued": True, "tag": tag, "url": j.url})
    return {"queued": results}
