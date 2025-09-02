import os, re, json, asyncio, base64, tempfile, shutil, uuid
from typing import Optional, Literal
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

import httpx
import uvicorn

# Google Drive
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

APP_PORT = int(os.getenv("PORT", "8000"))
DEFAULT_DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "").strip() or None
DRIVE_PUBLIC = os.getenv("DRIVE_PUBLIC", "false").lower() == "true"
DELETE_LOCAL_AFTER_UPLOAD = os.getenv("DELETE_LOCAL_AFTER_UPLOAD", "true").lower() == "true"
AUTH_MODE = os.getenv("DRIVE_AUTH", "oauth").lower()  # 'oauth' or 'service'

def build_drive_service():
    if AUTH_MODE == "oauth":
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
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    else:
        service_json = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON") or (
            os.getenv("DRIVE_SERVICE_ACCOUNT_JSON_B64") and
            base64.b64decode(os.getenv("DRIVE_SERVICE_ACCOUNT_JSON_B64")).decode("utf-8")
        )
        if not service_json:
            raise RuntimeError("Service account selected but DRIVE_SERVICE_ACCOUNT_JSON(_B64) missing")
        creds_info = json.loads(service_json)
        scopes = ["https://www.googleapis.com/auth/drive"]
        sa = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
        return build("drive", "v3", credentials=sa, cache_discovery=False)

drive_service = build_drive_service()

def sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return safe.strip(" .")

async def run(cmd: list[str], timeout: Optional[int] = None) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try: proc.kill()
        except Exception: pass
        return 124, "", "Timeout"
    return proc.returncode, stdout.decode(errors="ignore"), stderr.decode(errors="ignore")

def upload_to_drive(local_path: str, out_name: str, folder_id: Optional[str]) -> dict:
    file_metadata = {"name": out_name}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    media = MediaFileUpload(local_path, resumable=True)
    file = (drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink",
                    supportsAllDrives=True)
            .execute())
    if DRIVE_PUBLIC:
        drive_service.permissions().create(
            fileId=file["id"],
            body={"role": "reader", "type": "anyone"},
            supportsAllDrives=True
        ).execute()
    return {"file_id": file["id"], "drive_link": file.get("webViewLink")}

async def safe_callback(url: str, payload: dict):
    if not url: return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json=payload)
    except Exception:
        pass

# ---------- yt-dlp metadata helpers ----------
async def get_metadata(url: str, timeout: int = 90) -> dict:
    cmd = ["yt-dlp", "--dump-json", "--no-warnings", url]
    rc, so, se = await run(cmd, timeout=timeout)
    if rc != 0:
        raise RuntimeError(f"yt-dlp --dump-json failed: {se[-500:]}")
    line = next((ln for ln in so.splitlines() if ln.strip().startswith("{")), "{}")
    return json.loads(line)

async def get_playlist_json(url: str, timeout: int = 180) -> dict:
    cmd = ["yt-dlp", "-J", "--no-warnings", url]
    rc, so, se = await run(cmd, timeout=timeout)
    if rc != 0:
        raise RuntimeError(f"yt-dlp -J failed: {se[-500:]}")
    return json.loads(so)

# ---------- API models ----------
class DownloadReq(BaseModel):
    url: str
    tag: Optional[str] = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:8]}")
    drive_folder: Optional[str] = None
    expected_name: Optional[str] = None
    callback_url: Optional[str] = None
    quality: Literal["BEST_ORIGINAL","BEST_MP4","STRICT_MP4_REENC"] = "BEST_MP4"
    timeout: Optional[int] = 1800

class DownloadAck(BaseModel):
    accepted: bool
    tag: str
    expected_name: Optional[str]
    note: str

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "auth_mode": AUTH_MODE, "time": datetime.utcnow().isoformat()}

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/discover")
async def discover(
    channel_url: str = Query(..., description="Rumble channel or playlist (e.g., https://rumble.com/c/TateSpeech)"),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
    min_duration: int = Query(0, ge=0, description="Keep items with duration >= this (sec)"),
    min_views: int = Query(0, ge=0, description="Keep items with views >= this"),
    dateafter: str = Query("now-30days", description="yt-dlp dateafter filter, e.g. now-30days or 20240101")
):
    if "rumble.com" not in channel_url.lower():
        raise HTTPException(status_code=400, detail="Only rumble.com URLs are supported")

    # Use yt-dlp filter flags in-process for speed/accuracy
    data = await get_playlist_json(
        f'{channel_url} --match-filter "duration >= {min_duration} | view_count >= {min_views}" --dateafter {dateafter}',
        timeout=180
    ) if (min_duration or min_views or dateafter) else await get_playlist_json(channel_url, timeout=180)

    entries = data.get("entries") or []
    out = []
    for e in entries[:limit]:
        id_     = (e.get("id") or e.get("webpage_url_basename") or "").lower()
        title   = e.get("title")
        dur     = e.get("duration")
        up_date = e.get("upload_date")
        views   = e.get("view_count")
        likes   = e.get("like_count") or e.get("rumble_count")
        url     = e.get("webpage_url") or e.get("url")
        out.append({
            "id": id_,
            "title": title,
            "duration": dur,
            "upload_date": up_date,
            "view_count": views,
            "rumbles": likes,
            "url": url,
        })
    return {"count": len(out), "source": channel_url, "fetched_at": datetime.utcnow().isoformat(), "items": out}

@app.post("/download", response_model=DownloadAck)
async def download(req: DownloadReq, bg: BackgroundTasks):
    if not req.url or "rumble.com" not in req.url.lower():
        raise HTTPException(status_code=400, detail="Only rumble.com links are supported")
    expected = req.expected_name or f"{req.tag}.mp4"
    expected = sanitize_filename(expected)
    if not expected.lower().endswith(".mp4"): expected += ".mp4"
    target_folder = req.drive_folder or DEFAULT_DRIVE_FOLDER_ID
    if not target_folder:
        raise HTTPException(status_code=400, detail="No Drive folder provided (drive_folder) and no default DRIVE_FOLDER_ID is set")
    bg.add_task(worker_job, req, expected, target_folder)
    return DownloadAck(accepted=True, tag=req.tag, expected_name=expected, note="processing")

async def worker_job(req: DownloadReq, expected_name: str, folder_id: str):
    started_iso = datetime.utcnow().isoformat()
    work_dir = tempfile.mkdtemp(prefix="dl_")
    temp_tpl = os.path.join(work_dir, f"{req.tag}.%(ext)s")
    out_local = os.path.join(work_dir, expected_name)
    try:
        base_cmd = ["yt-dlp", "--no-warnings", "--newline", "-o", temp_tpl, req.url]
        if req.quality == "BEST_ORIGINAL":
            fmt = "bestvideo*+bestaudio/best"; cmd = base_cmd + ["-f", fmt, "--merge-output-format", "mp4"]
        elif req.quality == "BEST_MP4":
            fmt = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b"; cmd = base_cmd + ["-f", fmt, "--remux-video", "mp4"]
        else:
            fmt = "bv*+ba/best"; cmd = base_cmd + ["-f", fmt, "--recode-video", "mp4"]
        rc, so, se = await run(cmd, timeout=req.timeout or 1800)
        if rc != 0:
            await safe_callback(req.callback_url or "", {
                "status":"error","tag": req.tag,"message": f"yt-dlp failed (rc={rc})",
                "stdout": so[-2000:], "stderr": se[-2000:], "started_at": started_iso,
                "completed_at": datetime.utcnow().isoformat()
            }); return

        files = [f for f in os.listdir(work_dir) if os.path.isfile(os.path.join(work_dir,f)) and not f.endswith(".part")]
        files = [f for f in files if re.search(r"\.(mp4|mkv|webm|m4a|mov|mp3)$", f, re.I)]
        if not files:
            await safe_callback(req.callback_url or "", {
                "status":"error","tag":req.tag,"message":"Downloaded file not found",
                "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
            }); return
        files.sort(key=lambda f: os.path.getmtime(os.path.join(work_dir, f)), reverse=True)
        dl_path = os.path.join(work_dir, files[0])

        if not dl_path.lower().endswith(".mp4") and expected_name.lower().endswith(".mp4"):
            rc2, _, _ = await run(["ffmpeg","-y","-i",dl_path,"-c","copy",out_local], timeout=600)
            if rc2 != 0:
                rc3, _, _ = await run(["ffmpeg","-y","-i",dl_path,"-c:v","libx264","-c:a","aac","-movflags","+faststart",out_local], timeout=3600)
                if rc3 != 0:
                    await safe_callback(req.callback_url or "", {
                        "status":"error","tag":req.tag,"message":"ffmpeg failed",
                        "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
                    }); return
        else:
            shutil.move(dl_path, out_local)

        up = upload_to_drive(out_local, expected_name, folder_id)

        # enrich callback with metadata (best-effort)
        meta = {}
        try:
            meta = await get_metadata(req.url, timeout=60)
        except Exception as _e:
            meta = {"_meta_error": str(_e)[:200]}

        if DELETE_LOCAL_AFTER_UPLOAD and os.path.exists(out_local):
            try: os.remove(out_local)
            except Exception: pass

        await safe_callback(req.callback_url or "", {
            "status":"done","tag":req.tag,"expected_name":expected_name,
            "drive_file_id": up["file_id"], "drive_link": up["drive_link"],
            "metadata": {
                "id": meta.get("id"),
                "title": meta.get("title"),
                "duration": meta.get("duration"),
                "uploader": meta.get("uploader"),
                "upload_date": meta.get("upload_date"),
                "view_count": meta.get("view_count"),
                "like_count": meta.get("like_count") or meta.get("rumble_count"),
                "webpage_url": meta.get("webpage_url"),
            },
            "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        await safe_callback(req.callback_url or "", {
            "status":"error","tag":req.tag,"message":str(e),
            "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
        })
    finally:
        try: shutil.rmtree(work_dir, ignore_errors=True)
        except Exception: pass

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=APP_PORT, reload=False)
