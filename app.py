# app.py (excerpt)
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

app = FastAPI()

# -------- Google Drive auth (Service Account) ----------
def build_drive():
    scopes = ["https://www.googleapis.com/auth/drive.file"]
    sa_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "/app/service_account.json")
    if not os.path.exists(sa_path):
        raise RuntimeError(f"Service account JSON not found at {sa_path}")
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

# -------- Model for /download body ----------
class DownloadReq(BaseModel):
    url: str
    tag: Optional[str] = None
    expected_name: Optional[str] = None   # <— allow client to force final name
    drive_parent: Optional[str] = None    # <— optional override folder
    callback_url: Optional[str] = None

# -------- Helper: pick best quality format for Rumble ----------
BEST_FORMAT = "bv*+ba/bestvideo+bestaudio/best"

# -------- Main worker (simplified) ----------
def run_download_and_upload(url: str, out_name: str, drive_parent: Optional[str]) -> dict:
    tmp_dir = "/data"  # or /data/videos if you prefer
    os.makedirs(tmp_dir, exist_ok=True)

    # Download with yt-dlp to temp path
    # -N 8 parallel segments; adjust if needed
    tmp_path = os.path.join(tmp_dir, out_name)
    cmd = [
        "yt-dlp",
        "-f", BEST_FORMAT,
        "-o", tmp_path,
        "--no-part",
        "--merge-output-format", "mp4",
        url,
    ]
    import subprocess
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {r.stderr[:800]}")

    # Upload to Drive
    drive = build_drive()
    file_metadata = {
        "name": out_name
    }
    # Prefer request drive_parent, otherwise env DRIVE_FOLDER_ID
    folder_id = drive_parent or os.environ.get("DRIVE_FOLDER_ID")
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(tmp_path, mimetype="video/mp4", resumable=True)
    created = drive.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()

    # (optional) cleanup local file
    try:
        os.remove(tmp_path)
    except Exception:
        pass

    return {"fileId": created.get("id"), "webViewLink": created.get("webViewLink")}

# -------- Endpoint ----------
@app.post("/download")
def enqueue(req: DownloadReq):
    if not req.url or "rumble.com" not in req.url:
        raise HTTPException(status_code=400, detail="Provide a valid rumble.com URL")

    # Decide final output name:
    # 1) use expected_name if provided by n8n
    # 2) else derive from URL id
    def derive_id(u: str) -> str:
        import re
        m = re.search(r"/(v[0-9a-z]+)", u, re.I)
        return m.group(1).lower() if m else "vid"

    def slug(s: str, n: int = 15) -> str:
        import re
        sl = re.sub(r"[^A-Za-z0-9]+", "_", s.lower()).strip("_")
        return sl[:n]

    if req.expected_name:
        out_name = req.expected_name
        if not out_name.endswith(".mp4"):
            out_name += ".mp4"
    else:
        vid = derive_id(req.url)
        # You can optionally pull a title first; kept simple:
        out_name = f"tate_{vid}_{slug(vid)}.mp4"

    try:
        result = run_download_and_upload(
            url=req.url,
            out_name=out_name,
            drive_parent=req.drive_parent,
        )
        return {
            "status": "queued",    # or "done" if you run synchronous like here
            "out_name": out_name,
            "drive": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
