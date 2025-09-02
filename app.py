import os
import re
import json
import asyncio
import shutil
import tempfile
import uuid
import pathlib
import time
import threading
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException, Header, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

import httpx
import uvicorn

# =========================
# Config
# =========================
APP_PORT = int(os.getenv("PORT", "8000"))

PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
PUBLIC_FILES_DIR = os.getenv("PUBLIC_FILES_DIR", "/data/public")
os.makedirs(PUBLIC_FILES_DIR, exist_ok=True)

ONCE_TOKEN_TTL_SEC = int(os.getenv("ONCE_TOKEN_TTL_SEC", "86400"))  # if never downloaded
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT_SEC") or 1800)   # default per job

# Always allow any URL
ALLOW_ANY_URL = True

# =========================
# In-memory registries
# =========================
# Single-use token registry: token -> meta
# meta: { path, size, active, consumed, last_seen, expiry }
ONCE_TOKENS: Dict[str, Dict[str, Any]] = {}

# Job status registry for polling: tag -> {status, payload}
# status: queued | downloading | ready | error
# payload (when ready): { tag, expected_name, once_url, expires_in_sec, quality }
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
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return 124, "", "Timeout"
    return proc.returncode, stdout.decode(errors="ignore"), stderr.decode(errors="ignore")

async def safe_callback(url: str, payload: dict):
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json=payload)
    except Exception:
        # best-effort; ignore failures
        pass

# =========================
# Single-use link helpers
# =========================
def _file_stat(path: str) -> tuple[int, str]:
    p = pathlib.Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError
    return (p.stat().st_size, p.name)

def make_single_use_url(filename: str, base_url: Optional[str] = None) -> str:
    path = os.path.join(PUBLIC_FILES_DIR, filename)
    size, _ = _file_stat(path)
    token = uuid.uuid4().hex
    ONCE_TOKENS[token] = {
        "path": path,
        "size": size,
        "active": 0,          # concurrent stream count
        "consumed": False,    # set True once any bytes are sent successfully
        "last_seen": time.time(),
        "expiry": time.time() + ONCE_TOKEN_TTL_SEC,
    }
    base = (base_url or PUBLIC_BASE_URL).rstrip("/")
    if not base:
        return f"/once/{token}"
    return f"{base}/once/{token}"

def _maybe_delete_and_purge(token: str):
    meta = ONCE_TOKENS.get(token)
    if not meta:
        return
    # Delete when all streams finished and at least one emitted bytes
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
                    # token expired without any real download → delete to free disk
                    try:
                        os.remove(m["path"])
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(60)

threading.Thread(target=_janitor_loop, daemon=True).start()

# =========================
# FastAPI app
# =========================
app = FastAPI()

@app.get("/")
def root():
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "public_base_url": PUBLIC_BASE_URL or "(unset)",
        "public_files_dir": PUBLIC_FILES_DIR,
        "allow_any_url": ALLOW_ANY_URL,
    }

@app.get("/healthz")
def healthz():
    return {"ok": True}

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

class DownloadAck(BaseModel):
    accepted: bool
    tag: str
    expected_name: Optional[str]
    note: str

# =========================
# Routes
# =========================
@app.post("/download", response_model=DownloadAck)
async def download(req: DownloadReq, bg: BackgroundTasks):
    if not req.url or not isinstance(req.url, str):
        raise HTTPException(status_code=400, detail="Missing url")

    # Any URL allowed (hard-enabled). Add your own allow/deny if needed.

    expected = req.expected_name or f"{req.tag}.mp4"
    expected = sanitize_filename(expected)
    if not expected.lower().endswith(".mp4"):
        expected += ".mp4"

    # Register job for polling
    JOBS[req.tag] = {"status": "queued", "payload": None}

    bg.add_task(worker_job, req, expected)
    return DownloadAck(accepted=True, tag=req.tag, expected_name=expected, note="processing")

@app.get("/once/{token}")
def serve_single_use(token: str, range_header: Optional[str] = Header(default=None, alias="Range")):
    """
    Streams the file ONCE (supports Range). After all concurrent streams finish,
    the file is deleted and the token is invalidated.
    """
    meta = ONCE_TOKENS.get(token)
    if not meta:
        raise HTTPException(status_code=404, detail="Expired or invalid link")

    path = meta["path"]
    if not os.path.exists(path):
        ONCE_TOKENS.pop(token, None)
        raise HTTPException(status_code=404, detail="File not found")

    size = meta["size"]
    meta["last_seen"] = time.time()

    # Default full-content
    start, end = 0, size - 1
    status_code = 200
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
        "Content-Disposition": f'inline; filename="{pathlib.Path(path).name}"',
        "Content-Type": "video/mp4",  # adjust by sniffing extension if needed
    }

    # Parse Range header
    if range_header and size > 0:
        try:
            unit, rng = range_header.split("=")
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
                    to_read = chunk if remaining >= chunk else remaining
                    data = f.read(to_read)
                    if not data:
                        break
                    emitted_any = True
                    yield data
                    remaining -= len(data)
        finally:
            meta["active"] -= 1
            if emitted_any:
                meta["consumed"] = True
            _maybe_delete_and_purge(token)

    return StreamingResponse(file_iter(), status_code=status_code, headers=headers)

@app.get("/status")
def get_status(tag: str = Query(...)):
    rec = JOBS.get(tag)
    if not rec:
        return JSONResponse({"tag": tag, "status": "unknown"}, status_code=404)
    return {"tag": tag, "status": rec["status"]}

@app.get("/result")
def get_result(tag: str = Query(...)):
    rec = JOBS.get(tag)
    if not rec:
        return JSONResponse({"tag": tag, "status": "unknown"}, status_code=404)
    if rec["status"] != "ready" or not rec.get("payload"):
        return JSONResponse({"tag": tag, "status": rec["status"]}, status_code=202)
    return {"tag": tag, "status": "ready", **rec["payload"]}

# =========================
# Worker
# =========================
async def worker_job(req: DownloadReq, expected_name: str):
    started_iso = datetime.utcnow().isoformat()
    work_dir = tempfile.mkdtemp(prefix="dl_")
    temp_tpl = os.path.join(work_dir, f"{req.tag}.%(ext)s")
    out_local = os.path.join(work_dir, expected_name)
    public_path = os.path.join(PUBLIC_FILES_DIR, expected_name)

    try:
        JOBS[req.tag]["status"] = "downloading"

        # Build yt-dlp command by quality
        base_cmd = ["yt-dlp", "--no-warnings", "--newline", "--force-ipv4", "-o", temp_tpl, req.url]
        if req.quality == "BEST_ORIGINAL":
            cmd = base_cmd + ["-f", "bestvideo*+bestaudio/best", "--merge-output-format", "mp4"]
        elif req.quality == "BEST_MP4":
            cmd = base_cmd + ["-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b", "--remux-video", "mp4"]
        else:  # STRICT_MP4_REENC
            cmd = base_cmd + ["-f", "bv*+ba/best", "--recode-video", "mp4"]

        rc, so, se = await run(cmd, timeout=req.timeout or DOWNLOAD_TIMEOUT)
        if rc != 0:
            JOBS[req.tag] = {"status": "error", "payload": {"message": f"yt-dlp failed (rc={rc})"}}
            await safe_callback(req.callback_url or "", {
                "status": "error",
                "tag": req.tag,
                "message": f"yt-dlp failed (rc={rc})",
                "stdout": so[-2000:], "stderr": se[-2000:],
                "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
            })
            return

        # Pick newest finished media file
        files = [
            f for f in os.listdir(work_dir)
            if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith(".part")
        ]
        files = [f for f in files if re.search(r"\.(mp4|mkv|webm|m4a|mov|mp3)$", f, re.I)]
        if not files:
            JOBS[req.tag] = {"status": "error", "payload": {"message": "Downloaded file not found"}}
            await safe_callback(req.callback_url or "", {
                "status": "error", "tag": req.tag, "message": "Downloaded file not found",
                "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
            })
            return
        files.sort(key=lambda f: os.path.getmtime(os.path.join(work_dir, f)), reverse=True)
        dl_path = os.path.join(work_dir, files[0])

        # Normalize to mp4 if needed
        if not dl_path.lower().endswith(".mp4") and expected_name.lower().endswith(".mp4"):
            # fast remux first
            rc2, _, _ = await run(["ffmpeg", "-y", "-i", dl_path, "-c", "copy", out_local], timeout=600)
            if rc2 != 0:
                # fallback to full re-encode
                rc3, _, _ = await run(
                    ["ffmpeg", "-y", "-i", dl_path, "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", out_local],
                    timeout=max(1800, req.timeout or DOWNLOAD_TIMEOUT)
                )
                if rc3 != 0:
                    JOBS[req.tag] = {"status": "error", "payload": {"message": "ffmpeg failed"}}
                    await safe_callback(req.callback_url or "", {
                        "status": "error", "tag": req.tag, "message": "ffmpeg failed",
                        "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
                    })
                    return
        else:
            shutil.move(dl_path, out_local)

        # Move into public dir (persistent volume)
        shutil.move(out_local, public_path)

        # Build single-use URL (auto-deletes after first full transfer)
        once_url = make_single_use_url(os.path.basename(public_path), base_url=PUBLIC_BASE_URL)

        # Record payload for polling
        ready_payload = {
            "tag": req.tag,
            "expected_name": expected_name,
            "once_url": once_url,
            "expires_in_sec": ONCE_TOKEN_TTL_SEC,
            "quality": req.quality,
        }
        JOBS[req.tag] = {"status": "ready", "payload": ready_payload}

        # Optional: still try to callback if provided
        await safe_callback(req.callback_url or "", {
            "status": "ready",
            **ready_payload,
            "started_at": started_iso,
            "completed_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        JOBS[req.tag] = {"status": "error", "payload": {"message": str(e)}}
        await safe_callback(req.callback_url or "", {
            "status": "error",
            "tag": req.tag,
            "message": str(e),
            "started_at": started_iso,
            "completed_at": datetime.utcnow().isoformat()
        })
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
