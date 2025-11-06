# 502 Error Fix - Railway Deployment

## What Was Wrong

The 502 Bad Gateway error was caused by **3 critical issues**:

### 1. ❌ Wrong Startup Command in Dockerfile
**Problem:**
```dockerfile
CMD ["python", "app.py"]  # ← This file doesn't exist anymore!
```

**Fixed:**
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 2. ❌ Wrong Health Check Endpoint
**Problem:**
```dockerfile
HEALTHCHECK ... CMD curl -fsS http://127.0.0.1:8080/healthz || exit 1
```
The `/healthz` endpoint doesn't exist in v3.1.0.

**Fixed:**
```dockerfile
HEALTHCHECK ... CMD curl -fsS http://127.0.0.1:8080/api/v1/health || exit 1
```

### 3. ⚠️ Missing Environment Variables
Railway needs these environment variables set:

**Required:**
```bash
REQUIRE_API_KEY=false        # Set to false for easy testing
API_KEY=test                 # Any value works if REQUIRE_API_KEY=false
STORAGE_DIR=/app/data        # Must match Railway volume mount path
PUBLIC_BASE_URL=https://your-app.up.railway.app  # Your Railway URL
```

---

## Files Fixed

### ✅ Dockerfile
- Changed CMD to use `uvicorn app.main:app`
- Fixed health check to `/api/v1/health`

### ✅ app/config.py
- Updated VERSION to "3.1.0"

### ✅ New Files Created
- `railway.json` - Railway deployment configuration
- `RAILWAY_DEPLOYMENT.md` - Complete deployment guide
- `verify_deployment.py` - Pre-deployment verification script

---

## How to Deploy to Railway Now

### Step 1: Set Environment Variables in Railway

Go to your Railway project → Variables tab → Add these:

```bash
# Essential (copy-paste these)
REQUIRE_API_KEY=false
API_KEY=your-secret-key-here-change-me
STORAGE_DIR=/app/data
PUBLIC_BASE_URL=https://your-app.up.railway.app

# Optional but recommended
ALLOW_YT_DOWNLOADS=true
WORKERS=2
MAX_CONCURRENT_DOWNLOADS=3
WEBHOOK_ENABLE=true
LOG_LEVEL=INFO
```

### Step 2: Add Railway Volume

1. In Railway dashboard, go to your service
2. Click "Variables" tab
3. Click "New Volume" button
4. Set:
   - **Mount Path:** `/app/data`
   - **Size:** 10GB (or more)
5. Save

### Step 3: Commit and Push

```bash
git add .
git commit -m "Fix 502 error - update Dockerfile and config"
git push origin main
```

Railway will automatically:
- Build the new Docker image
- Deploy with correct startup command
- Health checks will pass
- Your app will be accessible!

### Step 4: Verify Deployment

After Railway finishes deploying (2-3 minutes):

**1. Check Health:**
```bash
curl https://your-app.up.railway.app/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "3.1.0",
  "uptime_seconds": 45,
  "workers": 2
}
```

**2. Open Web UI:**
Visit: `https://your-app.up.railway.app/`

You should see the Ultimate Media Downloader interface!

**3. Check API Docs:**
Visit: `https://your-app.up.railway.app/docs`

You should see the Swagger UI with 30+ endpoints.

---

## Troubleshooting

### Still Getting 502?

**1. Check Railway Logs:**
```
Railway Dashboard → Your Service → Deployments → Latest → View Logs
```

Look for:
- ✓ "Starting Ultimate Media Downloader Service..."
- ✓ "Queue manager started"
- ✓ "File deletion scheduler started"
- ✓ "Service started with X workers"

**2. Verify Environment Variables:**
```
Railway Dashboard → Your Service → Variables
```

Make sure you have:
- ✓ REQUIRE_API_KEY (set to "false" or "true")
- ✓ API_KEY (any value if REQUIRE_API_KEY=false)
- ✓ STORAGE_DIR=/app/data
- ✓ PUBLIC_BASE_URL (your Railway URL)

**3. Verify Volume is Mounted:**
```
Railway Dashboard → Your Service → Variables → Volumes
```

Should see:
- ✓ Mount Path: /app/data
- ✓ Status: Mounted

**4. Check Build Logs:**
Look for these successful steps:
- ✓ Installing Python dependencies
- ✓ Installing yt-dlp
- ✓ Copying application code
- ✓ Build completed successfully

### Frontend Not Loading?

**Check:**
1. Visit root URL: `https://your-app.up.railway.app/`
2. Open browser console (F12) and check for errors
3. Verify `PUBLIC_BASE_URL` is set to your Railway URL
4. Make sure `/static/index.html` exists in your repository

### Downloads Not Working?

**Check:**
1. Volume is mounted at `/app/data`
2. `ALLOW_YT_DOWNLOADS=true` (if downloading from YouTube)
3. Check logs for permission errors
4. Verify storage directory is writable

---

## Quick Test Commands

Once deployed, test with these commands:

### 1. Health Check
```bash
curl https://your-app.up.railway.app/api/v1/health
```

### 2. Version Info
```bash
curl https://your-app.up.railway.app/version
```

### 3. Create Test Download
```bash
curl -X POST https://your-app.up.railway.app/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
  }'
```

### 4. Check Download Status
```bash
# Use request_id from previous response
curl https://your-app.up.railway.app/api/v1/downloads/{request_id}
```

---

## What's Different from v3.0.0?

### Application Structure
- **Old:** Monolithic `app.py` file
- **New:** Modular structure with `app.main:app`

### Startup Command
- **Old:** `python app.py`
- **New:** `uvicorn app.main:app --host 0.0.0.0 --port 8080`

### Health Check
- **Old:** `/healthz` (non-standard)
- **New:** `/api/v1/health` (RESTful)

### Features Added in v3.1.0
- ✨ Channel downloads with filtering
- ✨ Batch downloads (up to 100 URLs)
- ✨ Webhook notifications
- ✨ Cookie management with encryption
- ✨ Complete frontend web UI
- ✨ 18 new API endpoints

---

## Pre-Deployment Checklist

Run this before deploying:

```bash
python3 verify_deployment.py
```

This will check:
- ✓ Python version
- ✓ Required files
- ✓ Dependencies
- ✓ Dockerfile configuration
- ✓ Application imports

All checks should pass!

---

## Success Criteria

Your deployment is successful when:

1. ✅ No 502 errors
2. ✅ Health check returns `{"status": "healthy"}`
3. ✅ Web UI loads at root URL
4. ✅ API docs accessible at `/docs`
5. ✅ Can create and track downloads
6. ✅ Files are stored in `/app/data`

---

## Summary

**Fixed Files:**
- ✅ `Dockerfile` - Correct startup and health check
- ✅ `app/config.py` - Version updated to 3.1.0

**New Files:**
- ✅ `railway.json` - Railway config
- ✅ `RAILWAY_DEPLOYMENT.md` - Full deployment guide
- ✅ `verify_deployment.py` - Pre-deployment verification
- ✅ `FIXED_502_ERROR.md` - This file

**Next Action:**
```bash
# 1. Commit the fixes
git add .
git commit -m "Fix 502 error: update Dockerfile and Railway config"
git push origin main

# 2. Set Railway environment variables (see Step 1 above)

# 3. Add Railway volume (see Step 2 above)

# 4. Wait for deployment (2-3 minutes)

# 5. Test your app!
```

**Your app should now work perfectly on Railway!** 🎉

---

Need help? Check:
- `RAILWAY_DEPLOYMENT.md` for detailed deployment guide
- Railway logs for specific errors
- Run `verify_deployment.py` to diagnose issues
