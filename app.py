import os, re, json, subprocess, asyncio, httpx
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

app = FastAPI()

BEST_FORMAT = "bv*+ba/bestvideo+bestaudio/best"

def build_drive():
    scopes = ["https://www.googleapis.com/auth/drive.file"]
    sa_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "/app/service_account.json")
    if not os.path.exists(sa_path):
        raise RuntimeError(f"Service account JSON not found at {sa_path}")
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

class DownloadReq(BaseModel):
    url: str
    tag: Optional[str] = None
    expected_name: Optional[str] = None
    drive_parent: Optional[str] = None
    callback_url: Optional[str] = None

@app.get("/health")
def health():
    return {"ok": True}

def derive_id(u: str) -> str:
    m = re.search(r"/(v[0-9a-z]+)", u, re.I)
    return m.group(1).lower() if m else "vid"

def slug(s: str, n: int = 15) -> str:
    sl = re.sub(r"[^A-Za-z0-9]+", "_", s.lower()).strip("_")
    return sl[:n]

def download_video(url: str, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [
        "yt-dlp",
        "-f", BEST_FORMAT,
        "-o", out_path,
        "--no-part",
        "--merge-output-format", "mp4",
        url,
    ]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {r.stderr[:1000]}")

def upload_to_drive(local_path: str, out_name: str, parent: Optional[str]) -> Dict[str, str]:
    drive = build_drive()
    file_metadata = {"name": out_name}
    folder_id = parent or os.environ.get("DRIVE_FOLDER_ID")
    if folder_id:
        file_metadata["parents"] = [folder_id]
    media = MediaFileUpload(local_path, mimetype="video/mp4", resumable=True)
    created = drive.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
    return {"id": created.get("id"), "webViewLink": created.get("webViewLink")}

async def post_callback(callback_url: str, payload: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(callback_url, json=payload)
    except Exception:
        pass  # don't crash job on callback failure

def run_job_sync(req: DownloadReq) -> Dict[str, str]:
    # decide final name
    if req.expected_name:
        out_name = req.expected_name if req.expected_name.endswith(".mp4") else f"{req.expected_name}.mp4"
    else:
        vid = derive_id(req.url)
        out_name = f"tate_{vid}_{slug(vid)}.mp4"

    tmp_dir = os.environ.get("WORK_DIR", "/data")
    tmp_path = os.path.join(tmp_dir, out_name)

    # download
    download_video(req.url, tmp_path)

    # upload
    drive_info = upload_to_drive(tmp_path, out_name, req.drive_parent)

    # cleanup (optional)
    try:
        os.remove(tmp_path)
    except Exception:
        pass

    result = {
        "status": "done",
        "out_name": out_name,
        "drive": drive_info,
        "url": req.url,
        "tag": req.tag or "",
    }
    return result

async def run_job_background(req: DownloadReq):
    try:
        result = run_job_sync(req)
        if req.callback_url:
            await post_callback(req.callback_url, result)
    except Exception as e:
        if req.callback_url:
            await post_callback(req.callback_url, {
                "status": "error",
                "url": req.url,
                "tag": req.tag or "",
                "error": str(e)
            })

@app.post("/download")
async def enqueue(req: DownloadReq, bg: BackgroundTasks):
    if not req.url or "rumble.com" not in req.url:
        raise HTTPException(status_code=400, detail="Provide a valid rumble.com URL")

    # Return immediately; run in background to avoid gateway timeouts
    bg.add_task(run_job_background, req)
    job_id = (req.tag or derive_id(req.url)) + "-" + str(int(asyncio.get_event_loop().time()*1000))
    return {"status": "accepted", "job_id": job_id}
