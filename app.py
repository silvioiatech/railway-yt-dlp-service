import os
import re
import json
import asyncio
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- Config ---
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
DRIVE_PUBLIC = os.getenv("DRIVE_PUBLIC", "false").lower() == "true"
QUALITY_MODE = os.getenv("QUALITY_MODE", "BEST_MP4")
TIMEOUT_SEC = int(os.getenv("TIMEOUT_SEC", "1800"))

# Service Account JSON (from env var or file)
service_json_str = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON")
if not service_json_str and os.path.exists("service_account.json"):
    with open("service_account.json", "r") as f:
        service_json_str = f.read()

creds = None
if service_json_str:
    creds_dict = json.loads(service_json_str)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )

# Google Drive client
drive_service = build("drive", "v3", credentials=creds)

# --- App ---
app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "drive_folder": DRIVE_FOLDER_ID}

@app.post("/download")
async def download_video(request: Request):
    body = await request.json()
    url = body.get("url")
    out_name = body.get("out_name")
    tag = body.get("tag", "job")

    if not url:
        return JSONResponse(status_code=400, content={"detail": "Provide a valid rumble.com URL"})

    # Safe filename
    if not out_name:
        match = re.search(r"/(v[0-9a-z]+)/", url)
        vid_id = match.group(1) if match else "video"
        out_name = f"tate_{vid_id}.mp4"

    out_path = f"/tmp/{out_name}"

    # yt-dlp command
    ytdlp_cmd = [
        "yt-dlp",
        "-f", "mp4/best",
        "-o", out_path,
        url,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *ytdlp_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SEC)
        except asyncio.TimeoutError:
            proc.kill()
            return JSONResponse(status_code=500, content={"detail": f"Timeout after {TIMEOUT_SEC}s"})

        if proc.returncode != 0:
            return JSONResponse(status_code=500, content={"detail": f"yt-dlp failed", "stderr": stderr.decode()})

        # Upload to Drive
        file_metadata = {"name": out_name}
        if DRIVE_FOLDER_ID:
            file_metadata["parents"] = [DRIVE_FOLDER_ID]

        media = MediaFileUpload(out_path, mimetype="video/mp4", resumable=True)
        uploaded = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink, webContentLink"
        ).execute()

        # Make file public if needed
        if DRIVE_PUBLIC:
            drive_service.permissions().create(
                fileId=uploaded["id"],
                body={"type": "anyone", "role": "reader"},
            ).execute()

        # Cleanup tmp
        os.remove(out_path)

        return {
            "status": "done",
            "fileId": uploaded["id"],
            "webViewLink": uploaded.get("webViewLink"),
            "webContentLink": uploaded.get("webContentLink"),
            "tag": tag
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=port)
