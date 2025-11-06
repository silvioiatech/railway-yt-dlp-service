# Implementation Guide - Ultimate Media Downloader UI

## Quick Start (30 minutes to working prototype)

This guide will help you integrate the designed UI with your existing FastAPI backend.

---

## Phase 1: Immediate Integration (Day 1)

### Step 1: Serve Static Files

Update your FastAPI app to serve the static HTML files:

```python
# app.py or main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve main UI
@app.get("/")
async def root():
    return FileResponse("static/index.html")

# Mobile version
@app.get("/mobile")
async def mobile():
    return FileResponse("static/mobile.html")

# Playlist browser
@app.get("/playlist")
async def playlist():
    return FileResponse("static/playlist.html")
```

### Step 2: Connect API Endpoints

Update the JavaScript in `static/index.html` to connect to your actual API:

```javascript
// Replace the app() function with real API integration
function app() {
    return {
        // ... existing state ...

        async startDownload(mode) {
            if (!this.url || this.downloading) return;

            try {
                this.downloading = true;

                // Call your actual API
                const response = await fetch('/api/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        url: this.url,
                        quality: this.selectedQuality,
                        format: mode === 'custom' ? {
                            video: this.videoFormat,
                            audio: this.audioFormat
                        } : 'best',
                        subtitles: this.downloadSubtitles,
                        embed_thumbnail: this.embedThumbnail,
                        embed_metadata: this.embedMetadata
                    })
                });

                const data = await response.json();

                // Create download object
                const download = {
                    id: data.request_id,
                    url: this.url,
                    title: data.title || 'Processing...',
                    status: 'downloading',
                    progress: 0,
                    speed: '0 MB/s',
                    downloaded: '0 MB',
                    totalSize: data.estimated_size || '0 MB',
                    eta: 'Calculating...',
                    fileUrl: null,
                    error: null
                };

                this.downloads.unshift(download);
                this.saveDownloads();

                // Start polling for progress
                this.pollProgress(download.id);

            } catch (error) {
                console.error('Download error:', error);
                this.showNotification('Failed to start download', 'error');
                this.downloading = false;
            }
        },

        async pollProgress(downloadId) {
            const interval = setInterval(async () => {
                try {
                    const response = await fetch(`/api/download/${downloadId}`);
                    const data = await response.json();

                    const download = this.downloads.find(d => d.id === downloadId);
                    if (!download) {
                        clearInterval(interval);
                        return;
                    }

                    // Update download object
                    download.title = data.title || download.title;
                    download.status = data.status;
                    download.progress = data.progress || 0;
                    download.speed = data.speed || '0 MB/s';
                    download.downloaded = data.downloaded || '0 MB';
                    download.eta = data.eta || 'Calculating...';

                    if (data.status === 'completed') {
                        download.fileUrl = data.file_url;
                        this.downloading = false;
                        clearInterval(interval);
                        this.showNotification('Download completed!', 'success');
                    } else if (data.status === 'failed') {
                        download.error = data.error || 'Download failed';
                        this.downloading = false;
                        clearInterval(interval);
                        this.showNotification('Download failed', 'error');
                    }

                    this.saveDownloads();

                } catch (error) {
                    console.error('Progress polling error:', error);
                    clearInterval(interval);
                }
            }, 1000); // Poll every second
        }
    }
}
```

---

## API Endpoints Required

Your backend must implement these endpoints for the UI to work:

```python
# 1. Download endpoint
@app.post("/api/download")
async def create_download(request: DownloadRequest):
    """
    Returns: {
        "request_id": "uuid",
        "status": "queued",
        "estimated_size": 52428800
    }
    """
    pass

# 2. Status endpoint
@app.get("/api/download/{download_id}")
async def get_download_status(download_id: str):
    """
    Returns: {
        "status": "downloading|completed|failed",
        "title": "Video Title",
        "progress": 45,
        "speed": "5.2 MB/s",
        "file_url": "/files/xxx.mp4"
    }
    """
    pass

# 3. Metadata endpoint
@app.get("/api/metadata")
async def get_metadata(url: str):
    """
    Returns video info without downloading
    """
    pass
```

---

## Files Created

Here are all the files that have been created for your UI:

### Main Files
1. **/Users/silvio/Documents/GitHub/railway-yt-dlp-service/static/index.html** - Desktop-optimized main interface
2. **/Users/silvio/Documents/GitHub/railway-yt-dlp-service/static/mobile.html** - Mobile-optimized interface
3. **/Users/silvio/Documents/GitHub/railway-yt-dlp-service/static/playlist.html** - Playlist browser with grid/list views
4. **/Users/silvio/Documents/GitHub/railway-yt-dlp-service/static/manifest.json** - PWA manifest for installability

### Documentation Files
5. **/Users/silvio/Documents/GitHub/railway-yt-dlp-service/DESIGN_SYSTEM.md** - Complete design system documentation
6. **/Users/silvio/Documents/GitHub/railway-yt-dlp-service/UI_MOCKUPS.md** - ASCII mockups and layout specifications

---

## Quick Start Commands

```bash
# 1. Navigate to your project
cd /Users/silvio/Documents/GitHub/railway-yt-dlp-service

# 2. Install dependencies (if not already)
pip install fastapi uvicorn python-multipart

# 3. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Open browser
open http://localhost:8000
```

---

## Testing Your UI

1. **Desktop**: Open http://localhost:8000
2. **Mobile**: Open http://localhost:8000/mobile
3. **Playlist**: Open http://localhost:8000/playlist

---

## Next Steps

1. Connect your existing download API endpoints
2. Test all features end-to-end
3. Deploy to Railway
4. Share with users!

---

**Estimated Implementation Time**: 1-2 days for full integration
