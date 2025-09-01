import os, json, base64, tempfile, asyncio, subprocess, traceback
from typing import Optional

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

# ---- Google Drive client ----
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---- Optional callback ----
import httpx

app = FastAPI()

# ---------- ENV ----------
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
QUALITY_MODE = os.getenv("QUALITY_MODE", "best[ext=mp4]/best")
TIMEOUT_SEC = int(os.getenv("TIMEOUT_SEC", "1800"))
DELETE_LOCAL_AFTER_UPLOAD = os.getenv("DELETE_LOCAL_AFTER_UPLOAD", "true").lower() == "true"
DEFAULT_DRIVE_PARENT = os.getenv("DRIVE_FOLDER_ID", "")

# Prefer base64 to avoid JSON escaping in envs
sa_b64 = os.getenv("DRIVE_SERVICE_ACCOUNT_B64")
if not sa_b64:
    raise RuntimeError("Missing DRIVE_SERVICE_ACCOUNT_B64 env var (service account JSON as base64).")

sa_info = json.loads(base64.b64decode(sa_b64))
creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
drive = build("drive", "v3", credentials=creds)

# ---------- Models ----------
class DownloadReq(BaseModel):
    url: str
    out_name: Optional[str] = None
    tag: Optional[str] = None
    callback_url: Optional[str] = None
    drive_parent: Optional[str] = None  # overrides default folder

# ---------- Helpers ----------
def _slug15(s: str) -> str:
    return "".join([c.lower() if c.isalnum() else "_" for c in s])[:15].strip("_")

def _derive_out_name(url: str) -> str:
    # Try to extract rumble id vXXXXXX
    import re
    m = re.search(r"/(v[0-9a-z]+)[/\-]?", url, re.I)
    vid = (m.group(1).lower() if m else "vx")
    return f"tate_{vid}.mp4"

def yt_dlp_download(url: str, out_name: str) -> str:
    tmp_dir = tempfile.gettempdir()
    out_path = os.path.join(tmp_dir, out_name)
    cmd = [
        "yt-dlp",
        "-f", QUALITY_MODE,
        "-o", out_path,
        url
    ]
    subprocess.run(cmd, check=True, timeout=TIMEOUT_SEC)
    return out_path

def drive_upload(file_path: str, out_name: str, drive_parent: Optional[str]) -> dict:
    meta = {"name": out_name}
    parent = drive_parent or DEFAULT_DRIVE_PARENT
    if parent:
        meta["parents"] = [parent]
    media = MediaFileUpload(file_path, resumable=True)
    file = drive.files().create(
        body=meta, media_body=media, fields="id, name, webViewLink, size, mimeType"
    ).execute()
    return file

async def post_callback(url: str, payload: dict):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            await client.post(url, json=payload)
    except Exception:
        # Don’t crash worker on callback error
        pass

async def worker(req: DownloadReq):
    status = {"status": "started", "tag": req.tag, "url": req.url}
    out_name = req.out_name or _derive_out_name(req.url)

    try:
        path = await asyncio.to_thread(yt_dlp_download, req.url, out_name)
        uploaded = await asyncio.to_thread(drive_upload, path, out_name, req.drive_parent)
        if DELETE_LOCAL_AFTER_UPLOAD:
            try:
                os.remove(path)
            except Exception:
                pass

        status.update({
            "status": "done",
            "out_name": out_name,
            "drive": uploaded,
        })
    except subprocess.TimeoutExpired:
        status.update({"status": "error", "error": "download_timeout"})
    except subprocess.CalledProcessError as e:
        status.update({"status": "error", "error": "yt_dlp_failed", "detail": str(e)})
    except Exception as e:
        status.update({"status": "error", "error": "server_exception", "detail": str(e), "trace": traceback.format_exc()})

    # optional callback
    if req.callback_url:
        await post_callback(req.callback_url, status)

    return status

# ---------- Routes ----------
@app.get("/health")
def health():
    return {"ok": True}

@app.post("/download")
async def download_endpoint(req: DownloadReq, bg: BackgroundTasks):
    # Kick off background task so the HTTP request returns quickly
    bg.add_task(worker, req)
    return {"queued": True, "url": req.url, "tag": req.tag or "", "note": "processing in background"}
