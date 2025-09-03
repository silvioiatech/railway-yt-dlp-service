import os, re, json, asyncio, shutil, tempfile, uuid, pathlib, time, threading, base64
from datetime import datetime, timedelta
from typing import Optional, Literal, List, Dict, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

import httpx
import uvicorn

# ============== Config ==============
APP_PORT = int(os.getenv("PORT", "8000"))

# Destination selection
DEFAULT_DEST = (os.getenv("DEFAULT_DEST") or "LOCAL").upper()  # "LOCAL" or "DRIVE"

# Local (internal storage) config
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
PUBLIC_FILES_DIR = os.getenv("PUBLIC_FILES_DIR", "/data/public")
os.makedirs(PUBLIC_FILES_DIR, exist_ok=True)
ONCE_TOKEN_TTL_SEC = int(os.getenv("ONCE_TOKEN_TTL_SEC", "86400"))  # if never downloaded
DELETE_AFTER_SERVE = (os.getenv("DELETE_AFTER_SERVE", "true").lower() == "true")

# Drive config (optional)
DRIVE_ENABLED = (os.getenv("DRIVE_ENABLED") or ("oauth" if os.getenv("GOOGLE_REFRESH_TOKEN") else "")).lower() in ("oauth","service")
DRIVE_AUTH = (os.getenv("DRIVE_AUTH") or "oauth").lower()  # "oauth" | "service"
DRIVE_FOLDER_ID_DEFAULT = (os.getenv("DRIVE_FOLDER_ID") or "").strip() or None
DRIVE_PUBLIC = (os.getenv("DRIVE_PUBLIC") or "false").lower() == "true"

# Timeouts / quality
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT_SEC") or 5400)

# ============== State ==============
# Single-use tokens: token -> { path, size, active, consumed, last_seen, expiry, tag }
ONCE_TOKENS: Dict[str, Dict[str, Any]] = {}
# Jobs: tag -> {status, payload, updated_at}
JOBS: Dict[str, Dict[str, Any]] = {}

# ============== Utils ==============
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
        pass

def job_set(tag: str, **kw):
    rec = JOBS.get(tag, {"tag": tag})
    rec.update(kw)
    rec["updated_at"] = datetime.utcnow().isoformat()
    JOBS[tag] = rec

# ============== Single-use (LOCAL) helpers ==============
def _file_stat(path: str) -> tuple[int, str]:
    p = pathlib.Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError
    return (p.stat().st_size, p.name)

def build_once_url(token: str) -> str:
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
        "active": 0,
        "consumed": False,
        "last_seen": time.time(),
        "expiry": time.time() + ONCE_TOKEN_TTL_SEC,
        "tag": tag,
    }
    return build_once_url(token)

def _maybe_delete_and_purge(token: str):
    meta = ONCE_TOKENS.get(token)
    if not meta: return
    if meta["active"] == 0 and meta["consumed"]:
        try:
            if os.path.exists(meta["path"]):
                os.remove(meta["path"])
        except Exception: pass
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

# ============== Google Drive (optional) ==============
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

# ============== FastAPI app ==============
app = FastAPI()

@app.get("/")
def root():
    return {
        "ok": True,
        "default_dest": DEFAULT_DEST,
        "drive_enabled": DRIVE_ENABLED,
        "public_base_url": PUBLIC_BASE_URL or "(unset)",
        "public_files_dir": PUBLIC_FILES_DIR,
        "time": datetime.utcnow().isoformat(),
    }

@app.get("/healthz")
def healthz():
    return {"ok": True}

# ===== Models =====
class DownloadReq(BaseModel):
    url: str
    tag: Optional[str] = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:8]}")
    expected_name: Optional[str] = None
    callback_url: Optional[str] = None
    quality: Literal["BEST_ORIGINAL", "BEST_MP4", "STRICT_MP4_REENC"] = "BEST_MP4"
    timeout: Optional[int] = DOWNLOAD_TIMEOUT
    dest: Optional[Literal["LOCAL","DRIVE"]] = None
    drive_folder: Optional[str] = None

class DownloadAck(BaseModel):
    accepted: bool
    tag: str
    expected_name: Optional[str]
    note: str

# ===== Routes =====
@app.post("/download", response_model=DownloadAck)
async def download(req: DownloadReq, bg: BackgroundTasks):
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
    return DownloadAck(accepted=True, tag=req.tag, expected_name=expected, note="processing")

@app.get("/status")
def status(tag: str = Query(...)):
    rec = JOBS.get(tag)
    if not rec:
        return JSONResponse({"tag": tag, "status": "unknown"}, status_code=404)
    return {"tag": tag, "status": rec.get("status"), "dest": rec.get("dest")}

@app.get("/result")
def result(tag: str = Query(...)):
    rec = JOBS.get(tag)
    if not rec:
        return JSONResponse({"tag": tag, "status": "unknown"}, status_code=404)
    st = rec.get("status")
    payload = rec.get("payload") or {}
    if st == "ready":
        return JSONResponse({"tag": tag, "status": "ready", **payload}, status_code=200)
    if st == "error":
        return JSONResponse({"tag": tag, "status": "error", "error_message": payload.get("error_message","unknown")}, status_code=500)
    # queued/downloading
    return JSONResponse({"tag": tag, "status": st or "queued"}, status_code=202)

@app.get("/once/{token}")
def serve_once(token: str, range_header: Optional[str] = Header(default=None, alias="Range")):
    meta = ONCE_TOKENS.get(token)
    if not meta:
        raise HTTPException(status_code=404, detail="Expired or invalid link")
    path = meta["path"]
    if not os.path.exists(path):
        ONCE_TOKENS.pop(token, None)
        raise HTTPException(status_code=404, detail="File not found")

    size = meta["size"]
    meta["last_seen"] = time.time()

    start, end = 0, size - 1
    status_code = 200
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
        "Content-Disposition": f'inline; filename="{pathlib.Path(path).name}"',
        "Content-Type": "video/mp4",
    }
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
        emitted = False
        try:
            with open(path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                chunk = 1024 * 1024
                while remaining > 0:
                    data = f.read(min(chunk, remaining))
                    if not data: break
                    emitted = True
                    yield data
                    remaining -= len(data)
        finally:
            meta["active"] -= 1
            if emitted: meta["consumed"] = True
            if DELETE_AFTER_SERVE: _maybe_delete_and_purge(token)

    return StreamingResponse(file_iter(), status_code=status_code, headers=headers)

# ===== Worker =====
async def worker_job(req: DownloadReq, expected_name: str, dest: str):
    started_iso = datetime.utcnow().isoformat()
    work_dir = tempfile.mkdtemp(prefix="dl_")
    temp_tpl = os.path.join(work_dir, f"{req.tag}.%(ext)s")
    out_local = os.path.join(work_dir, expected_name)

    try:
        job_set(req.tag, status="downloading", dest=dest)
        # yt-dlp cmd
        base = ["yt-dlp", "--no-warnings", "--newline", "--force-ipv4", "-o", temp_tpl, req.url]
        if req.quality == "BEST_ORIGINAL":
            cmd = base + ["-f", "bestvideo*+bestaudio/best", "--merge-output-format", "mp4"]
        elif req.quality == "BEST_MP4":
            cmd = base + ["-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b", "--remux-video", "mp4"]
        else:
            cmd = base + ["-f", "bv*+ba/best", "--recode-video", "mp4"]

        rc, so, se = await run(cmd, timeout=req.timeout or DOWNLOAD_TIMEOUT)
        if rc != 0:
            err = f"yt-dlp failed (rc={rc})\n{(se or '')[-1500:]}"
            job_set(req.tag, status="error", payload={"error_message": err})
            await safe_callback(req.callback_url or "", {"status":"error","tag":req.tag,"error_message":err,"started_at":started_iso,"completed_at":datetime.utcnow().isoformat()})
            return

        files = [f for f in os.listdir(work_dir) if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith(".part")]
        files = [f for f in files if re.search(r"\.(mp4|mkv|webm|m4a|mov|mp3)$", f, re.I)]
        if not files:
            err = "no media file produced"
            job_set(req.tag, status="error", payload={"error_message": err})
            await safe_callback(req.callback_url or "", {"status":"error","tag":req.tag,"error_message":err,"started_at":started_iso,"completed_at":datetime.utcnow().isoformat()})
            return
        files.sort(key=lambda f: os.path.getmtime(os.path.join(work_dir, f)), reverse=True)
        src = os.path.join(work_dir, files[0])

        # ensure mp4 if expected ends with .mp4
        if not src.lower().endswith(".mp4") and expected_name.lower().endswith(".mp4"):
            rc2, _, _ = await run(["ffmpeg", "-y", "-i", src, "-c", "copy", out_local], timeout=600)
            if rc2 != 0:
                rc3, _, _ = await run(
                    ["ffmpeg", "-y", "-i", src, "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", out_local],
                    timeout=max(1800, req.timeout or DOWNLOAD_TIMEOUT)
                )
                if rc3 != 0:
                    err = "ffmpeg failed"
                    job_set(req.tag, status="error", payload={"error_message": err})
                    await safe_callback(req.callback_url or "", {"status":"error","tag":req.tag,"error_message":err,"started_at":started_iso,"completed_at":datetime.utcnow().isoformat()})
                    return
        else:
            shutil.move(src, out_local)

        if dest == "DRIVE":
            # Upload to Drive
            try:
                folder_id = req.drive_folder or DRIVE_FOLDER_ID_DEFAULT
                if not folder_id:
                    raise RuntimeError("DRIVE_FOLDER_ID missing")
                up = drive_upload(out_local, expected_name, folder_id)
                # success payload
                payload = {
                    "tag": req.tag,
                    "expected_name": expected_name,
                    "drive_file_id": up["file_id"],
                    "drive_link": up.get("webViewLink"),
                    "quality": req.quality,
                    "dest": "DRIVE",
                }
                job_set(req.tag, status="ready", payload=payload)
                await safe_callback(req.callback_url or "", {"status":"ready", **payload, "started_at":started_iso, "completed_at":datetime.utcnow().isoformat()})
            finally:
                # always remove local temp
                try: os.remove(out_local)
                except Exception: pass
        else:
            # LOCAL single-use link
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
            await safe_callback(req.callback_url or "", {"status":"ready", **payload, "started_at":started_iso, "completed_at":datetime.utcnow().isoformat()})

    except Exception as e:
        err = str(e)
        job_set(req.tag, status="error", payload={"error_message": err})
        await safe_callback(req.callback_url or "", {"status":"error","tag":req.tag,"error_message":err,"started_at":started_iso,"completed_at":datetime.utcnow().isoformat()})
    finally:
        try: shutil.rmtree(work_dir, ignore_errors=True)
        except Exception: pass

# ============== Main ==============
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=APP_PORT, reload=False)
