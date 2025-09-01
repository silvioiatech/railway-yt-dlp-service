import os
import json
import base64
import subprocess
import tempfile
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ------------------------------
# ENV variables
# ------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
DELETE_LOCAL_AFTER_UPLOAD = os.getenv("DELETE_LOCAL_AFTER_UPLOAD", "false").lower() == "true"
QUALITY_MODE = os.getenv("QUALITY_MODE", "best")
TIMEOUT_SEC = int(os.getenv("TIMEOUT_SEC", "1800"))

# Load service account from BASE64
sa_info = json.loads(base64.b64decode(os.environ["DRIVE_SERVICE_ACCOUNT_B64"]))
creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
drive = build("drive", "v3", credentials=creds)

# ------------------------------
# Download video with yt-dlp
# ------------------------------
def download_video(url, out_name):
    tmp_dir = tempfile.gettempdir()
    out_path = os.path.join(tmp_dir, out_name)

    cmd = [
        "yt-dlp",
        "-f", QUALITY_MODE,
        "-o", out_path,
        url
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True, timeout=TIMEOUT_SEC)
    return out_path

# ------------------------------
# Upload to Google Drive
# ------------------------------
def upload_to_drive(file_path, out_name):
    file_metadata = {"name": out_name}
    if DRIVE_FOLDER_ID:
        file_metadata["parents"] = [DRIVE_FOLDER_ID]

    media = MediaFileUpload(file_path, resumable=True)
    file = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    print("Uploaded:", file)
    return file

# ------------------------------
# Main flow
# ------------------------------
def process(url, out_name):
    # Step 1: download
    local_file = download_video(url, out_name)

    # Step 2: upload
    uploaded = upload_to_drive(local_file, out_name)

    # Step 3: cleanup
    if DELETE_LOCAL_AFTER_UPLOAD:
        os.remove(local_file)

    return uploaded

# ------------------------------
# Example
# ------------------------------
if __name__ == "__main__":
    test_url = "https://rumble.com/v6w2w5e-a-motive-life-is-a-competition.html"
    out_name = "tate_test.mp4"
    result = process(test_url, out_name)
    print("✅ Done:", result)
