import os, re, json, subprocess, asyncio, base64
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import uvicorn

# ─────────────────────────────────────────────
# Load Google Drive credentials (Base64 JSON)
# ─────────────────────────────────────────────
service_json_str = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON")
if not service_json_str:
    b64 = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON_B64")
    if b64:
        service_json_str = base64.b64decode(b64).decode("utf-8")

if not service_json_str:
    raise RuntimeError(
        "No Google credentials found. "
        "Set DRIVE_SERVICE_ACCOUNT_JSON_B64 with base64-encoded service account JSON."
    )

creds_dict = json.loads(service_json_str)
creds = service_account.Credentials.from_service_account_info(
    creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
)

drive_service = build("drive", "v3", credentials=creds)

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
DELETE_LOCAL_AFTER_UPLOAD = os.getenv("DELETE_LOCAL_AFTER_UPLOAD", "true").lower() == "true"
QUALITY_MODE = os.getenv("QUALITY_MODE", "BEST_MP4")
TIMEOUT_SEC = int(os.getenv("TIMEOUT_SEC", "1800"))

# ─────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────
app = FastAPI()

def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)

async def run_cmd(cmd):
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()

def upload_to_drive(local_path: str, out_name: str):
    file_metadata = {"name": out_name}
    if DRIVE_FOLDER_ID:
        file_metadata["parents"] = [DRIVE_FOLDER_ID]

    media = MediaFileUpload(local_path, resumable=True)
    file = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )

    # Make file public if DRIVE_PUBLIC is set
    if os.getenv("DRIVE_PUBLIC", "false").lower() == "true":
        drive_service.permissions().create(
            fileId=file["id"], body={"role": "reader", "type": "anyone"}
        ).execute()

    return file

@app.post("/download")
async def download_video(req: Request):
    data = await req.json()
    url = data.get("url")
    tag = data.get("tag") or "video"
    if not url:
        raise HTTPException(400, detail="Missing url")

    # Filename
    out_name = sanitize_filename(f"{tag}.mp4")

    # yt-dlp command
    ytdlp_cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",
        "-o", out_name,
        url,
    ]

    rc, out, err = await run_cmd(ytdlp_cmd)
    if rc != 0:
        raise HTTPException(500, detail=f"yt-dlp failed: {err}")

    if not os.path.exists(out_name):
        raise HTTPException(500, detail="yt-dlp did not produce a file")

    # Upload to Drive
    file = upload_to_drive(out_name, out_name)

    # Delete local copy
    if DELETE_LOCAL_AFTER_UPLOAD:
        os.remove(out_name)

    return {"file_id": file["id"], "drive_link": file.get("webViewLink")}

@app.get("/")
async def root():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
