import os, re, time, subprocess
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header
from pydantic import BaseModel
import requests

# ---------- config ----------
OUT_DIR = Path("/app/out"); OUT_DIR.mkdir(parents=True, exist_ok=True)
RUMBLE_RE = re.compile(r"^https?://(www\.)?rumble\.com/", re.I)
DEFAULT_FMT = 'bv*+ba/best'     # best video+audio fallback
TIMEOUT_SEC = 30 * 60           # 30 minutes
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")  # optional simple bearer

# ---------- models ----------
class Job(BaseModel):
    url: str
    tag: Optional[str] = None
    callback_url: Optional[str] = None

class Batch(BaseModel):
    items: List[Job]

# ---------- utils ----------
def sh(cmd: list[str], timeout: Optional[int] = None) -> tuple[int, str, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        return 124, "", "timeout"
    return p.returncode, out, err

def newest(prefix: str) -> Optional[Path]:
    files = sorted(OUT_DIR.glob(f"{prefix}*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def upload_transfersh(file_path: Path) -> tuple[str, str]:
    # transfer.sh returns a single URL
    rc, out, err = sh(["bash", "-lc", f'curl --silent --upload-file "{file_path}" "https://transfer.sh/{file_path.name}"'])
    if rc != 0 or not out.strip().startswith("https://"):
        raise RuntimeError(f"transfer.sh failed rc={rc} out={out[-200:]} err={err[-200:]}")
    return out.strip(), file_path.name

def callback(cb_url: str, payload: dict) -> None:
    try:
        requests.post(cb_url, json=payload, timeout=15)
    except Exception:
        # don't crash if callback fails
        pass

def run_download(url: str, tag: str) -> Path:
    safe_tag = re.sub(r"[^A-Za-z0-9._-]+", "_", tag) if tag else "job"
    out_tpl = str(OUT_DIR / f"{safe_tag}_%(title).200B [%(id)s].%(ext)s")

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

def process_one(url: str, tag: Optional[str], cb: Optional[str]) -> dict:
    if not RUMBLE_RE.match(url or ""):
        raise HTTPException(status_code=400, detail="Provide a valid rumble.com URL")
    tag = tag or f"job_{int(time.time())}"
    mp4 = run_download(url, tag)
    file_url, file_name = upload_transfersh(mp4)
    payload = {
        "status": "ready",
        "file_url": file_url,
        "file_name": file_name,
        "rumble_url": url,
        "tag": tag,
        "run_url": ""  # not GH anymore
    }
    if cb:
        callback(cb, payload)
    return payload

# ---------- api ----------
api = FastAPI()

def check_auth(auth_header: Optional[str]):
    if not AUTH_TOKEN:
        return
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="invalid token")

@api.get("/health")
def health():
    return {"ok": True}

@api.post("/download")
def download(job: Job, bg: BackgroundTasks, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    # async queue
    tag = job.tag or f"job_{int(time.time())}"
    bg.add_task(process_one, job.url, tag, job.callback_url)
    return {"queued": True, "tag": tag, "url": job.url}

@api.post("/download/wait")
def download_wait(job: Job, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    return process_one(job.url, job.tag, job.callback_url)

@api.post("/download/batch")
def download_batch(batch: Batch, bg: BackgroundTasks, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    results = []
    for j in batch.items:
        tag = j.tag or f"job_{int(time.time())}"
        bg.add_task(process_one, j.url, tag, j.callback_url)
        results.append({"queued": True, "tag": tag, "url": j.url})
    return {"queued": results}
