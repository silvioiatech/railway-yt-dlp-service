import os
import re
import json
import csv
import asyncio
import base64
import shutil
import tempfile
import uuid
import itertools
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

from asyncio import Semaphore, wait_for, TimeoutError as AsyncTimeout


# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
APP_PORT = int(os.getenv("PORT", "8000"))

# Drive auth mode: "oauth" uses user refresh token, "service" uses service account
AUTH_MODE = (os.getenv("DRIVE_AUTH") or "oauth").lower()  # "oauth" | "service"

DEFAULT_DRIVE_FOLDER_ID = (os.getenv("DRIVE_FOLDER_ID") or "").strip() or None
DRIVE_PUBLIC = (os.getenv("DRIVE_PUBLIC") or "false").lower() == "true"
DELETE_LOCAL_AFTER_UPLOAD = (os.getenv("DELETE_LOCAL_AFTER_UPLOAD") or "true").lower() == "true"

# yt-dlp Process Defaults
DISCOVER_TIMEOUT = int(os.getenv("DISCOVER_TIMEOUT_SEC") or 180)
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT_SEC") or 1800)

# Enriched default fields ALWAYS returned by /discover (unless explicitly overridden)
DEFAULT_DISCOVER_FIELDS = (
    "id,title,url,uploader,channel,channel_id,extractor,"
    "upload_date,duration,view_count,like_count,dislike_count,comment_count,rumbles,"
    "thumbnail"
)


# ──────────────────────────────────────────────────────────────────────────────
# Drive client
# ──────────────────────────────────────────────────────────────────────────────
def build_drive_service():
    """
    Build a Google Drive service either via OAuth (refresh token) or Service Account.
    Service Account requires Shared Drives or domain delegation to have storage quota.
    """
    if AUTH_MODE == "oauth":
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
        scopes = (os.getenv("GOOGLE_SCOPES") or "https://www.googleapis.com/auth/drive.file").split()
        if not (client_id and client_secret and refresh_token):
            raise RuntimeError("OAuth selected but GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET/GOOGLE_REFRESH_TOKEN missing")
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    # Service account (Workspace shared drive or domain-delegated)
    service_json = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON")
    if not service_json and os.getenv("DRIVE_SERVICE_ACCOUNT_JSON_B64"):
        service_json = base64.b64decode(os.getenv("DRIVE_SERVICE_ACCOUNT_JSON_B64")).decode("utf-8")
    if not service_json:
        raise RuntimeError("Service auth selected but DRIVE_SERVICE_ACCOUNT_JSON(_B64) not provided")
    creds_info = json.loads(service_json)
    scopes = ["https://www.googleapis.com/auth/drive"]
    sa = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
    # NOTE: if you need domain-wide delegation, use sa.with_subject("user@domain.com")
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
        try:
            proc.kill()
        except Exception:
            pass
        return 124, "", "Timeout"
    return proc.returncode, stdout.decode(errors="ignore"), stderr.decode(errors="ignore")

def upload_to_drive(local_path: str, out_name: str, folder_id: Optional[str]) -> dict:
    file_metadata = {"name": out_name}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    media = MediaFileUpload(local_path, resumable=True)
    file = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink", supportsAllDrives=True)
        .execute()
    )
    if DRIVE_PUBLIC:
        drive_service.permissions().create(
            fileId=file["id"], body={"role": "reader", "type": "anyone"}, supportsAllDrives=True
        ).execute()
    return {"file_id": file["id"], "drive_link": file.get("webViewLink")}

async def safe_callback(url: str, payload: dict):
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json=payload)
    except Exception:
        # Swallow callback errors to not break the worker
        pass


# ──────────────────────────────────────────────────────────────────────────────
# yt-dlp helpers
# ──────────────────────────────────────────────────────────────────────────────
def normalize_entry(e: dict) -> dict:
    """
    Normalize a yt-dlp entry across platforms.
    Exposes as many useful metrics as available (likes, rumbles, dislikes, comments).
    """
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
        "upload_date": e.get("upload_date"),  # YYYYMMDD
        "duration": e.get("duration"),
        "view_count": e.get("view_count"),
        "like_count": like_count,                   # YouTube/Rumble mapped
        "dislike_count": e.get("dislike_count"),    # rarely available
        "comment_count": e.get("comment_count"),
        "rumbles": rumble_count,                    # explicit rumble metric
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

async def ytdlp_playlist_json(source_url: str, extra_args: Optional[List[str]] = None, timeout: int = 180) -> dict:
    """
    Robust wrapper around `yt-dlp -J` that:
      - tries the given URL
      - if it's a Rumble channel (/c/NAME), retries with /videos and with API hint
      - adds compatibility flags to reduce extractor/CDN issues
    """
    base = ["yt-dlp", "-J", "--no-warnings", "--ignore-errors", "--force-ipv4"]
    args = base + (extra_args or []) + [source_url]

    rc, so, se = await run(args, timeout=timeout)
    if rc == 0:
        try:
            return json.loads(so)
        except Exception:
            pass  # fall through to retries

    # RUMBLE FALLBACKS
    if "rumble.com" in source_url and "/c/" in source_url:
        alt = source_url.rstrip("/") + "/videos"
        args_alt = base + (extra_args or []) + [alt]
        rc2, so2, se2 = await run(args_alt, timeout=timeout)
        if rc2 == 0:
            try:
                return json.loads(so2)
            except Exception:
                pass

        # Best-effort extractor hint (ignored if unsupported)
        args_alt2 = base + (extra_args or []) + [
            "--extractor-args", "rumble:use_api=1"
        ] + [alt]
        rc3, so3, se3 = await run(args_alt2, timeout=timeout)
        if rc3 == 0:
            try:
                return json.loads(so3)
            except Exception:
                pass

        raise RuntimeError(f"yt-dlp -J failed for Rumble channel. stderr={se3 or se2 or se}")

    # Non-Rumble: return the stderr snippet for debugging
    raise RuntimeError(f"yt-dlp -J failed (rc={rc}). stderr={se[-500:]}")

async def ytdlp_flat_entries(source_url: str, extra_args: Optional[List[str]] = None, timeout: int = 120) -> List[str]:
    """
    Use --flat-playlist to get entry URLs quickly, then we can fetch each entry's metadata separately.
    """
    base = ["yt-dlp", "-J", "--flat-playlist", "--no-warnings", "--ignore-errors", "--force-ipv4"]
    args = base + (extra_args or []) + [source_url]
    rc, so, se = await run(args, timeout=timeout)
    if rc != 0:
        raise RuntimeError(f"yt-dlp --flat-playlist failed: {se[-500:]}")
    data = json.loads(so)
    entries = data.get("entries") or []
    urls = []
    for e in entries:
        u = e.get("url") or e.get("webpage_url")
        if u:
            urls.append(u)
    return urls

async def ytdlp_dump_json(entry_url: str, extra_args: Optional[List[str]] = None, timeout: int = 30) -> Optional[dict]:
    """
    Dump a single entry's JSON (fast). Returns None on non-fatal failure.
    """
    base = ["yt-dlp", "--dump-json", "--no-warnings", "--ignore-errors", "--force-ipv4"]
    args = base + (extra_args or []) + [entry_url]
    rc, so, se = await run(args, timeout=timeout)
    if rc != 0:
        return None
    line = next((ln for ln in so.splitlines() if ln.strip().startswith("{")), None)
    return json.loads(line) if line else None

async def gather_limited(coros, limit: int, overall_timeout: int) -> List[Optional[dict]]:
    """
    Run coroutines with a concurrency limit and an overall deadline.
    """
    sem = Semaphore(max(1, limit))

    async def run_one(coro_factory):
        async with sem:
            return await coro_factory()

    tasks = [run_one(cf) for cf in coros]
    try:
        return await wait_for(asyncio.gather(*tasks, return_exceptions=False), timeout=overall_timeout)
    except AsyncTimeout:
        # Return only results from tasks that finished
        done = []
        for t in tasks:
            if hasattr(t, 'done') and t.done() and not t.cancelled():
                try:
                    done.append(t.result())
                except Exception:
                    done.append(None)
        return done


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI models
# ──────────────────────────────────────────────────────────────────────────────
class DownloadReq(BaseModel):
    url: str
    tag: Optional[str] = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:8]}")
    drive_folder: Optional[str] = None
    expected_name: Optional[str] = None
    callback_url: Optional[str] = None
    quality: Literal["BEST_ORIGINAL", "BEST_MP4", "STRICT_MP4_REENC"] = "BEST_MP4"
    timeout: Optional[int] = DOWNLOAD_TIMEOUT

class DownloadAck(BaseModel):
    accepted: bool
    tag: str
    expected_name: Optional[str]
    note: str


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok", "auth_mode": AUTH_MODE, "time": datetime.utcnow().isoformat()}


@app.get("/healthz")
def healthz():
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# /discover — multi-source with rich defaults (+fast mode, max_duration) [ROBUST]
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/discover")
async def discover(
    sources: str = Query(..., description="Comma-separated channel/playlist/video URLs (any yt-dlp site)"),
    limit: int = Query(100, ge=1, le=1000, description="Max items per source"),
    # filters:
    min_views: int = Query(0, ge=0, description="view_count >= this"),
    min_duration: int = Query(0, ge=0, description="duration >= this (sec)"),
    max_duration: int = Query(0, ge=0, description="duration <= this (sec)"),
    dateafter: str = Query("", description='yt-dlp --dateafter (e.g. "now-30days", "20240101")'),
    # advanced:
    match_filter: str = Query("", description='raw yt-dlp --match-filter (overrides simple knobs)'),
    # output:
    format: str = Query("json", pattern="^(json|ndjson|csv)$"),
    fields: str = Query(DEFAULT_DISCOVER_FIELDS, description='Comma-separated fields ("*" or empty = defaults)'),
    timeout: int = Query(DISCOVER_TIMEOUT, ge=10, le=3600, description="Overall server-side time budget (seconds)"),
    # fast mode knobs:
    fast: bool = Query(False, description="Enable flat listing + concurrent per-entry fetches"),
    concurrency: int = Query(6, ge=1, le=20, description="Max concurrent entry fetches when fast=1"),
    per_item_timeout: int = Query(25, ge=5, le=120, description="Per-entry dump-json timeout when fast=1"),
    debug: bool = Query(False, description="Include extractor errors in rows"),
):
    src_list = [s.strip() for s in sources.split(",") if s.strip()]
    if not src_list:
        raise HTTPException(status_code=400, detail="No sources provided")

    # Build filters
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
            extra_args += ["--match-filter", " & ".join(clauses)]
    if dateafter:
        extra_args += ["--dateafter", dateafter]

    # tolerate hiccups
    extra_args += ["--ignore-errors"]

    rows: List[Dict] = []

    # Overall deadline for the whole endpoint
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout

    async def time_left():
        return max(1, int(deadline - loop.time()))

    for src in src_list:
        # Normalize Rumble channel to /videos (more reliable)
        if re.search(r"https?://(?:www\.)?rumble\.com/c/[^/]+/?$", src, re.I):
            src = src.rstrip("/") + "/videos"

        try:
            if fast:
                # 1) Get a flat list of entry URLs quickly
                flat_urls = await ytdlp_flat_entries(src, extra_args=extra_args, timeout=min(120, await time_left()))
                if not flat_urls:
                    raise RuntimeError("No entries (flat)")

                # 2) Trim to limit early
                flat_urls = flat_urls[:limit]

                # 3) Build coroutine factories for concurrent per-entry dump-json
                def make_coro(u):
                    async def _c():
                        return await ytdlp_dump_json(u, extra_args=extra_args, timeout=min(per_item_timeout, await time_left()))
                    return _c

                coros = [make_coro(u) for u in flat_urls]
                metas = await gather_limited(coros, limit=concurrency, overall_timeout=await time_left())

                # 4) Normalize each successful meta
                for m in metas:
                    if isinstance(m, dict):
                        rows.append(normalize_entry(m))

                # If nothing succeeded, fall back to monolithic -J (single try within remaining time)
                if not rows:
                    data = await ytdlp_playlist_json(src, extra_args=extra_args, timeout=min(120, await time_left()))
                    entries = data.get("entries")
                    if isinstance(entries, list) and entries:
                        for e in entries[:limit]:
                            if isinstance(e, dict):
                                rows.append(normalize_entry(e))
                    else:
                        rows.append(normalize_entry(data))

            else:
                # Original path (monolithic -J)
                data = await ytdlp_playlist_json(src, extra_args=extra_args, timeout=min(240, await time_left()))
                entries = data.get("entries")
                if isinstance(entries, list) and entries:
                    for e in entries[:limit]:
                        if isinstance(e, dict):
                            rows.append(normalize_entry(e))
                else:
                    rows.append(normalize_entry(data))

        except Exception as e:
            err = {"error": str(e)[:500]} if debug else {}
            rows.append({
                "id": "", "title": f"[DISCOVER ERROR] {src}", "url": src,
                "uploader": "", "channel": "", "channel_id": "", "extractor": "",
                "upload_date": None, "duration": None, "view_count": None,
                "like_count": None, "dislike_count": None, "comment_count": None,
                "rumbles": None, "thumbnail": "", **err
            })
            # continue to next source

    # Field selection — fall back to defaults if empty/"*"
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
# /download — Rumble → mp4 → Drive upload (+callback with metadata)
# ──────────────────────────────────────────────────────────────────────────────
class DownloadReq(BaseModel):
    url: str
    tag: Optional[str] = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:8]}")
    drive_folder: Optional[str] = None
    expected_name: Optional[str] = None
    callback_url: Optional[str] = None
    quality: Literal["BEST_ORIGINAL", "BEST_MP4", "STRICT_MP4_REENC"] = "BEST_MP4"
    timeout: Optional[int] = DOWNLOAD_TIMEOUT

class DownloadAck(BaseModel):
    accepted: bool
    tag: str
    expected_name: Optional[str]
    note: str

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
        base_cmd = ["yt-dlp", "--no-warnings", "--newline", "--force-ipv4", "-o", temp_tpl, req.url]
        if req.quality == "BEST_ORIGINAL":
            fmt = "bestvideo*+bestaudio/best"
            cmd = base_cmd + ["-f", fmt, "--merge-output-format", "mp4"]
        elif req.quality == "BEST_MP4":
            fmt = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b"
            cmd = base_cmd + ["-f", fmt, "--remux-video", "mp4"]
        else:
            fmt = "bv*+ba/best"
            cmd = base_cmd + ["-f", fmt, "--recode-video", "mp4"]

        rc, so, se = await run(cmd, timeout=req.timeout or DOWNLOAD_TIMEOUT)
        if rc != 0:
            await safe_callback(req.callback_url or "", {
                "status": "error", "tag": req.tag,
                "message": f"yt-dlp failed (rc={rc})",
                "stdout": so[-2000:], "stderr": se[-2000:],
                "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
            })
            return

        # Find the downloaded media
        files = [
            f for f in os.listdir(work_dir)
            if os.path.isfile(os.path.join(work_dir, f)) and not f.endswith(".part")
        ]
        files = [f for f in files if re.search(r"\.(mp4|mkv|webm|m4a|mov|mp3)$", f, re.I)]
        if not files:
            await safe_callback(req.callback_url or "", {
                "status": "error", "tag": req.tag, "message": "Downloaded file not found",
                "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
            })
            return
        files.sort(key=lambda f: os.path.getmtime(os.path.join(work_dir, f)), reverse=True)
        dl_path = os.path.join(work_dir, files[0])

        # Ensure MP4
        if not dl_path.lower().endswith(".mp4") and expected_name.lower().endswith(".mp4"):
            # Try stream copy first, then fallback to re-encode
            rc2, _, _ = await run(["ffmpeg", "-y", "-i", dl_path, "-c", "copy", out_local], timeout=600)
            if rc2 != 0:
                rc3, _, _ = await run(
                    ["ffmpeg", "-y", "-i", dl_path, "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", out_local],
                    timeout=3600
                )
                if rc3 != 0:
                    await safe_callback(req.callback_url or "", {
                        "status": "error", "tag": req.tag, "message": "ffmpeg failed",
                        "started_at": started_iso, "completed_at": datetime.utcnow().isoformat()
                    })
                    return
        else:
            shutil.move(dl_path, out_local)

        # Upload to Drive
        up = upload_to_drive(out_local, expected_name, folder_id)

        # Enriched metadata (best-effort)
        meta = {}
        try:
            rc_meta, so_meta, se_meta = await run(["yt-dlp", "--dump-json", "--no-warnings", "--force-ipv4", req.url], timeout=90)
            if rc_meta == 0:
                m = json.loads(next((ln for ln in so_meta.splitlines() if ln.strip().startswith("{")), "{}"))
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
            else:
                meta = {"_meta_error": (se_meta or "")[-300:]}
        except Exception as _e:
            meta = {"_meta_error": str(_e)[:200]}

        if DELETE_LOCAL_AFTER_UPLOAD and os.path.exists(out_local):
            try:
                os.remove(out_local)
            except Exception:
                pass

        await safe_callback(req.callback_url or "", {
            "status": "done",
            "tag": req.tag,
            "expected_name": expected_name,
            "drive_file_id": up["file_id"],
            "drive_link": up["drive_link"],
            "metadata": meta,
            "started_at": started_iso,
            "completed_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
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


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=APP_PORT, reload=False)
