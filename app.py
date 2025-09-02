import os, re, json, asyncio, base64, tempfile, shutil, uuid, csv
from io import StringIO
from typing import Optional, Literal, List, Dict
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

import httpx
import uvicorn

# Google Drive
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
APP_PORT = int(os.getenv("PORT", "8000"))
DEFAULT_DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "").strip() or None
DRIVE_PUBLIC = os.getenv("DRIVE_PUBLIC", "false").lower() == "true"
DELETE_LOCAL_AFTER_UPLOAD = os.getenv("DELETE_LOCAL_AFTER_UPLOAD", "true").lower() == "true"
AUTH_MODE = os.getenv("DRIVE_AUTH", "oauth").lower()  # 'oauth' or 'service'

# Default fields ALWAYS returned by /discover (unless you override via ?fields=)
DEFAULT_DISCOVER_FIELDS = (
    "id,title,url,uploader,channel,channel_id,extractor,"
    "upload_date,duration,view_count,like_count,dislike_count,comment_count,rumbles,"
    "thumbnail"
)

# ──────────────────────────────────────────────────────────────────────────────
# Drive client
# ──────────────────────────────────────────────────────────────────────────────
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

    # service account (Workspace + Shared Drive)
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

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
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
            .create(body=file_metadata, media_body=media, fields="id, webViewLink", supportsAllDrives=True)
            .execute())
    if DRIVE_PUBLIC:
        drive_service.permissions().create(
            fileId=file["id"], body={"role": "reader", "type": "anyone"}, supportsAllDrives=True
        ).execute()
    return {"file_id": file["id"], "drive_link": file.get("webViewLink")}

async def safe_callback(url: str, payload: dict):
    if not url: return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json=payload)
    except Exception:
        pass

# yt-dlp helpers
async def get_metadata(url: str, timeout: int = 90) -> dict:
    cmd = ["yt-dlp", "--dump-json", "--no-warnings", url]
    rc, so, se = await run(cmd, timeout=timeout)
    if rc != 0:
        raise RuntimeError(f"yt-dlp --dump-json failed: {se[-500:]}")
    line = next((ln for ln in so.splitlines() if ln.strip().startswith("{")), "{}")
    return json.loads(line)

async def ytdlp_playlist_json(source_url: str, extra_args: Optional[List[str]] = None, timeout: int = 180) -> dict:
    args = ["yt-dlp", "-J", "--no-warnings", source_url]
    if extra_args:
        args[3:3] = extra_args
    rc, so, se = await run(args, timeout=timeout)
    if rc != 0:
        raise RuntimeError(f"yt-dlp -J failed ({rc}): {se[-500:]}")
    return json.loads(so)

def normalize_entry(e: dict) -> dict:
    # Try to expose as much useful info as available across extractors.
    rumble_count = e.get("rumble_count")
    like_count = e.get("like_count") or rumble_count
    return {
        "id": (e.get("id") or e.get("webpage_url_basename") or "") or "",
        "title": e.get("title") or "",
        "url": e.get("webpage_url") or e.get("url") or "",
        "uploader": e.get("uploader") or e.get("uploader_id") or "",
        "channel": e.get("channel") or e.get("uploader") or "",
        "channel_id": e.get("channel_id") or e.get("uploader_id") or "",
        "extractor": e.get("extractor") or "",
        "upload_date": e.get("upload_date"),          # YYYYMMDD
        "duration": e.get("duration"),
        "view_count": e.get("view_count"),
        "like_count": like_count,                     # YouTube/Rumble (mapped)
        "dislike_count": e.get("dislike_count"),      # rare (YouTube cache/third-party)
        "comment_count": e.get("comment_count"),
        "rumbles": rumble_count,                      # explicit Rumble metric
        "thumbnail": e.get("thumbnail") or "",
    }

def to_csv(rows: List[dict], fields: List[str]) -> str:
    buf = StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()

def to_ndjson(rows: List[dict]) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)

# ──────────────────────────────────────────────────────────────────────────────
# API models
# ──────────────────────────────────────────────────────────────────────────────
class DownloadReq(BaseModel):
    url: str
    tag: Optional[str] = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:8]}")
    drive_folder: Optional[str] = None
    expected_name: Optional[str] = None
    callback_url: Optional[str] = None
    quality: Literal["BEST_ORIGINAL", "BEST_MP4", "STRICT_MP4_REENC"] = "BEST_MP4"
    timeout: Optional[int] = 1800

class DownloadAck(BaseModel):
    accepted: bool
    tag: str
    expected_name: Optional[str]
    note: str

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "auth_mode": AUTH_MODE, "time": datetime.utcnow().isoformat()}

@app.get("/healthz")
def healthz():
    return {"ok": True}

# ──────────────────────────────────────────────────────────────────────────────
# /discover — multi-source with rich defaults (+max_duration)  [FIXED]
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/discover")
async def discover(
    sources: str = Query(..., description="Comma-separated channel/playlist/video URLs (any yt-dlp site)"),
    limit: int = Query(100, ge=1, le=1000, description="Max items per source"),
    # easy filters:
    min_views: int = Query(0, ge=0, description="Keep items with view_count >= this"),
    min_duration: int = Query(0, ge=0, description="Keep items with duration >= this (sec)"),
    max_duration: int = Query(0, ge=0, description="Keep items with duration <= this (sec)"),
    dateafter: str = Query("", description='yt-dlp --dateafter (e.g. "now-30days", "20240101")'),
    # advanced:
    match_filter: str = Query("", description='raw yt-dlp --match-filter (overrides the simple knobs if present)'),
    # output format:
    format: str = Query("json", pattern="^(json|ndjson|csv)$"),
    fields: str = Query(DEFAULT_DISCOVER_FIELDS, description="Comma-separated fields to output (\"*\" or empty = defaults)"),
    timeout: int = Query(180, ge=10, le=3600),
):
    src_list = [s.strip() for s in sources.split(",") if s.strip()]
    if not src_list:
        raise HTTPException(status_code=400, detail="No sources provided")

    # Build yt-dlp filters
    extra_args: List[str] = []
    if match_filter:
        extra_args += ["--match-filter", match_filter]
    else:
        clauses = []
        if min_duration > 0:
            clauses.append(f"duration >= {min_duration}")
        if max_duration > 0:
            clauses.append(f"duration <= {max_duration}")
        if min_views > 0:
            clauses.append(f"view_count >= {min_views}")
        if clauses:
            # AND = all constraints must hold
            extra_args += ["--match-filter", " & ".join(clauses)]
    if dateafter:
        extra_args += ["--dateafter", dateafter]

    # Be tolerant to extractor hiccups
    extra_args += ["--ignore-errors"]

    rows: List[Dict] = []
    for src in src_list:
        try:
            data = await ytdlp_playlist_json(src, extra_args=extra_args, timeout=timeout)
        except Exception as e:
            rows.append({
                "id": "", "title": f"[DISCOVER ERROR] {src}", "url": src,
                "uploader": "", "channel": "", "channel_id": "", "extractor": "",
                "upload_date": None, "duration": None, "view_count": None,
                "like_count": None, "dislike_count": None, "comment_count": None,
                "rumbles": None, "thumbnail": "", "error": str(e)[:500]
            })
            continue

        # Handle both playlist/channel (with entries) and single video (no entries)
        entries = data.get("entries")
        if isinstance(entries, list) and entries:
            for e in entries[:limit]:
                if not isinstance(e, dict):
                    continue
                rows.append(normalize_entry(e))
        else:
            # Single video JSON object
            rows.append(normalize_entry(data))

    # Fields selection — fall back to defaults if empty/"*"
    raw_fields = (fields or "").strip()
    if not raw_fields or raw_fields == "*":
        raw_fields = DEFAULT_DISCOVER_FIELDS
    field_list = [f.strip() for f in raw_fields.split(",") if f.strip()]

    # Project items to requested fields
    items = [{k: r.get(k) for k in field_list} for r in rows]

    if format == "csv":
        csv_text = to_csv(items, field_list)
        return PlainTextResponse(csv_text, media_type="text/csv; charset=utf-8")
    elif format == "ndjson":
        ndjson_text = to_ndjson(items)
        return PlainTextResponse(ndjson_text, media_type="application/x-ndjson; charset=utf-8")
    else:
        return JSONResponse({
            "count": len(items),
            "fetched_at": datetime.utcnow().isoformat(),
            "sources": src_list,
            "fields": field_list,
            "items": items,
        })

# ──────────────────────────────────────────────────────────────────────────────
# /download — unchanged core, callback enriched with metadata
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/download", response_model=DownloadAck)
async def download(req: DownloadReq, bg: BackgroundTasks):
    if not req.url or "rumble.com" not in req.url.lower():
        raise HTTPException(status_code=400, detail="Only rumble.com links are supported")
    expected = req.expected_name or f"{req.tag}.mp4"
    expected = sanitize_filename(expected)
    if not expected.lower().endswith(".mp4"):
        expected += ".mp4"
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

        meta = {}
        try:
            m = await get_metadata(req.url, timeout=60)
            # build enriched meta similar to normalize_entry
            rumble_count = m.get("rumble_count")
            meta = {
                "id": m.get("id"),
                "title": m.get("title"),
                "url": m.get("webpage_url") or m.get("url"),
                "uploader": m.get("uploader") or m.get("channel"),
                "channel": m.get("channel") or m.get("uploader"),
                "channel_id": m.get("channel_id") or m.get("uploader_id"),
                "extractor": m.get("extractor"),
                "upload_date": m.get("upload_date"),
                "duration": m.get("duration"),
                "view_count": m.get("view_count"),
                "like_count": m.get("like_count") or rumble_count,
                "dislike_count": m.get("dislike_count"),
                "comment_count": m.get("comment_count"),
                "rumbles": rumble_count,
                "thumbnail": m.get("thumbnail"),
            }
        except Exception as _e:
            meta = {"_meta_error": str(_e)[:200]}

        if DELETE_LOCAL_AFTER_UPLOAD and os.path.exists(out_local):
            try: os.remove(out_local)
            except Exception: pass

        await safe_callback(req.callback_url or "", {
            "status":"done","tag":req.tag,"expected_name":expected_name,
            "drive_file_id": up["file_id"], "drive_link": up["drive_link"],
            "metadata": meta, "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        await safe_callback(req.callback_url or "", {
            "status":"error","tag":req.tag,"message":str(e),
            "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
        })
    finally:
        try: shutil.rmtree(work_dir, ignore_errors=True)
        except Exception: pass

# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=APP_PORT, reload=False)
