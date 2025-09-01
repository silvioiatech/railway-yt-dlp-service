import os
import re
import json
import base64
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---------- Config ----------
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "").strip()  # your folder id can go in env
GOOGLE_SA_JSON_B64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64", "").strip()
GOOGLE_CREDS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

# ---------- FastAPI ----------
app = FastAPI(title="yt-dlp → Google Drive bridge")

# ---------- Models ----------
class DownloadRequest(BaseModel):
    url: HttpUrl
    tag: Optional[str] = None
    expected_name: Optional[str] = None  # if you want to force the output mp4 name
    drive_folder_id: Optional[str] = None  # override per request
    callback_url: Optional[str] = None  # optional webhook after upload

# ---------- Helpers ----------
_slug_re = re.compile(r"[^a-z0-9]+")

def slugify(s: str, length: int = 40) -> str:
    s = s.lower()
    s = _slug_re.sub("_", s).strip("_")
    return s[:length] if length else s

def safe_filename_from_url(url: str) -> str:
    # try to pull rumble id like /vxxxxxx-
    m = re.search(r"/(v[0-9a-z]+)", url, re.I)
    vid = (m.group(1).lower() if m else "vid")
    return f"tate_{vid}.mp4"

def get_drive_service():
    creds = None
    if GOOGLE_SA_JSON_B64:
        try:
            decoded = base64.b64decode(GOOGLE_SA_JSON_B64)
            info = json.loads(decoded)
            creds = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/drive.file",
                        "https://www.googleapis.com/auth/drive.readonly",
                        "https://www.googleapis.com/auth/drive.metadata",
                        "https://www.googleapis.com/auth/drive"]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON_BASE64: {e}")
    elif GOOGLE_CREDS_PATH and os.path.exists(GOOGLE_CREDS_PATH):
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDS_PATH,
            scopes=["https://www.googleapis.com/auth/drive.file",
                    "https://www.googleapis.com/auth/drive.readonly",
                    "https://www.googleapis.com/auth/drive.metadata",
                    "https://www.googleapis.com/auth/drive"]
        )
    else:
        raise RuntimeError("No service account credentials provided. Set GOOGLE_SERVICE_ACCOUNT_JSON_BASE64 or GOOGLE_APPLICATION_CREDENTIALS.")
    return build("drive", "v3", credentials=creds, cache_discovery=False)

async def run_cmd(*args: str) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    return proc.returncode, out.decode(errors="ignore"), err.decode(errors="ignore")

async def do_download_and_upload(req: DownloadRequest):
    # decide filename
    out_name = req.expected_name or safe_filename_from_url(str(req.url))
    # extra: add short slug of url tail for uniqueness
    if not req.expected_name:
        tail = slugify(str(req.url).split("/")[-1], length=15)
        out_name = f"{out_name[:-4]}_{tail}.mp4" if out_name.endswith(".mp4") else f"{out_name}_{tail}.mp4"
    out_path = DATA_DIR / out_name

    # yt-dlp best quality + merge
    # Note: we specify output path explicitly to avoid temp files elsewhere
    ytdlp_args = [
        "yt-dlp",
        "-f", "bv*+ba/b",             # best video+audio or best
        "--merge-output-format", "mp4",
        "-o", str(out_path),
        "--no-part",                  # avoid .part
        "--retries", "10",
        "--fragment-retries", "10",
        "--concurrent-fragments", "8",
        "--no-check-certificate",
        str(req.url),
    ]
    code, out, err = await run_cmd(*ytdlp_args)
    if code != 0 or not out_path.exists():
        raise RuntimeError(f"yt-dlp failed (code {code}). stderr:\n{err[:1000]}")

    # upload to Drive
    parent_id = (req.drive_folder_id or DEFAULT_DRIVE_FOLDER_ID or "").strip()
    try:
        drive = get_drive_service()
        metadata = {"name": out_name}
        if parent_id:
            metadata["parents"] = [parent_id]
        media = MediaFileUpload(str(out_path), mimetype="video/mp4", resumable=True)
        file = drive.files().create(body=metadata, media_body=media, fields="id, webViewLink").execute()
        file_id = file.get("id")
        link = file.get("webViewLink")
    finally:
        # cleanup local file to save disk
        try:
            out_path.unlink(missing_ok=True)
        except Exception:
            pass

    # optional callback (best effort)
    if req.callback_url:
        try:
            import httpx
            payload = {
                "status": "uploaded",
                "file_id": file_id,
                "webViewLink": link,
                "tag": req.tag,
                "expected_name": out_name,
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(str(req.callback_url), json=payload)
        except Exception:
            # non-fatal
            pass

    return {"file_id": file_id, "webViewLink": link, "name": out_name}

# ---------- Routes ----------
@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/download")
async def enqueue(req: DownloadRequest, bg: BackgroundTasks):
    # quick param validation
    if not str(req.url).startswith(("http://", "https://")):
        raise HTTPException(400, "Provide a valid URL")
    # schedule background job
    bg.add_task(do_download_and_upload, req)
    # respond immediately
    return {"queued": True, "tag": req.tag or "", "expected_name": req.expected_name or ""}
