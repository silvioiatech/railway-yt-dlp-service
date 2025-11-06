# Railway Deployment Guide - Ultimate Media Downloader v3.1.0

## Quick Deploy to Railway

### Prerequisites
- Railway account (https://railway.app)
- GitHub account (to connect your repository)

---

## Step-by-Step Deployment

### 1. Fork/Clone Repository
```bash
git clone https://github.com/yourusername/railway-yt-dlp-service.git
cd railway-yt-dlp-service
```

### 2. Create Railway Project

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your repository
5. Railway will auto-detect the Dockerfile

### 3. Add Railway Volume (IMPORTANT!)

**Before deploying, add a volume for persistent storage:**

1. In Railway dashboard, click on your service
2. Go to "Variables" tab
3. Click "New Volume"
4. **Mount Path:** `/app/data`
5. **Size:** At least 10GB (recommended 50GB+)
6. Click "Add Volume"

### 4. Configure Environment Variables

In Railway dashboard, go to "Variables" and add these:

#### Required Variables
```bash
# Authentication (IMPORTANT: Set this first!)
REQUIRE_API_KEY=false
API_KEY=your-secret-key-here-change-this

# Storage (MUST match volume mount path)
STORAGE_DIR=/app/data

# Public URL (Railway will provide this after first deploy)
PUBLIC_BASE_URL=https://your-app.up.railway.app
```

#### Recommended Variables
```bash
# Enable YouTube downloads
ALLOW_YT_DOWNLOADS=true

# Concurrency
WORKERS=2
MAX_CONCURRENT_DOWNLOADS=3

# Webhooks
WEBHOOK_ENABLE=true
WEBHOOK_TIMEOUT_SEC=10
WEBHOOK_MAX_RETRIES=3

# Rate Limiting
RATE_LIMIT_RPS=2
RATE_LIMIT_BURST=5

# Logging
LOG_LEVEL=INFO
```

#### Optional Variables
```bash
# Cookie Encryption (auto-generated if not set)
# COOKIE_ENCRYPTION_KEY=your-64-char-hex-key

# CORS (if you have a separate frontend)
# CORS_ORIGINS=https://your-frontend.com

# Domain whitelist (empty = allow all)
# ALLOWED_DOMAINS=youtube.com,vimeo.com

# File retention (hours)
FILE_RETENTION_HOURS=48
```

### 5. Deploy

Railway will automatically:
1. Build the Docker image
2. Deploy the application
3. Provide a public URL

**Note:** First deployment may take 3-5 minutes.

### 6. Get Your Public URL

After deployment:
1. Go to "Settings" tab
2. Find "Public Networking" section
3. Click "Generate Domain"
4. Copy the URL (e.g., `https://your-app.up.railway.app`)
5. **Update the `PUBLIC_BASE_URL` variable with this URL**

### 7. Verify Deployment

Visit your Railway URL:
- **Homepage:** `https://your-app.up.railway.app/` (should show web UI)
- **API Docs:** `https://your-app.up.railway.app/docs`
- **Health Check:** `https://your-app.up.railway.app/api/v1/health`

Expected health check response:
```json
{
  "status": "healthy",
  "version": "3.1.0",
  "uptime_seconds": 123,
  "workers": 2,
  "active_jobs": 0
}
```

---

## Configuration Details

### Storage Volume

**Why it's needed:**
- Downloaded files are stored here
- Auto-cleanup runs after configured retention period
- Without volume, files are lost on redeploy

**Volume Configuration:**
- **Mount Path:** `/app/data` (must match `STORAGE_DIR`)
- **Recommended Size:** 50GB+ for heavy usage
- **Backup:** Railway volumes are persistent but consider backups

### Authentication Modes

#### Mode 1: Open Access (Development/Internal Use)
```bash
REQUIRE_API_KEY=false
# API_KEY can be anything, it won't be checked
```

#### Mode 2: API Key Required (Production)
```bash
REQUIRE_API_KEY=true
API_KEY=your-strong-secret-key
```

Generate a strong API key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Cookie Encryption

**Auto-generation (Recommended):**
```bash
# Leave COOKIE_ENCRYPTION_KEY unset
# System will auto-generate and persist in /app/data/cookies/.encryption_key
```

**Manual key (Optional):**
```bash
# Generate key
python -c "import secrets; print(secrets.token_hex(32))"

# Set in Railway
COOKIE_ENCRYPTION_KEY=your-64-char-hex-key
```

---

## Troubleshooting

### Issue: 502 Bad Gateway

**Causes:**
1. **Missing API_KEY** - If `REQUIRE_API_KEY=true` but `API_KEY` is empty
2. **Missing Volume** - No persistent storage configured
3. **Wrong startup command** - Using old `app.py` instead of `app.main:app`

**Solutions:**

1. **Check Logs:**
   ```
   Railway Dashboard → Your Service → Deployments → Click latest → View Logs
   ```

2. **Verify Environment Variables:**
   - `REQUIRE_API_KEY` is set (true or false)
   - `API_KEY` is set (even if `REQUIRE_API_KEY=false`)
   - `STORAGE_DIR=/app/data`

3. **Verify Volume:**
   - Volume is created
   - Mount path is `/app/data`

4. **Check Dockerfile:**
   - Should use: `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]`
   - Not: `CMD ["python", "app.py"]`

### Issue: Frontend Not Loading

**Check:**
1. Visit `https://your-app.up.railway.app/` (root URL)
2. Check browser console for errors (F12)
3. Verify `PUBLIC_BASE_URL` is set correctly

**If API works but frontend doesn't:**
```bash
# Check static files exist
ls -la static/

# Should see:
# index.html
# js/app.js
# css/custom.css
# manifest.json
```

### Issue: Downloads Failing

**Check:**
1. **Storage permissions:**
   ```
   # In Railway logs, look for:
   "Created storage directory: /app/data"
   ```

2. **yt-dlp installation:**
   ```
   # Should be in Dockerfile
   RUN pip install --no-cache-dir yt-dlp
   ```

3. **YouTube ToS compliance:**
   ```
   # If downloading from YouTube, must enable:
   ALLOW_YT_DOWNLOADS=true
   ```

### Issue: Cookies Not Working

**Check:**
1. Cookie encryption key is set or auto-generated
2. Cookies directory exists: `/app/data/cookies/`
3. Check logs for cookie-related errors

**Manual fix:**
```bash
# Generate encryption key
python -c "import secrets; print(secrets.token_hex(32))"

# Set in Railway variables
COOKIE_ENCRYPTION_KEY=<generated-key>
```

### Issue: Webhooks Not Delivering

**Check:**
1. `WEBHOOK_ENABLE=true`
2. Webhook URL is accessible from Railway
3. Check webhook endpoint logs
4. Verify HMAC signature if implemented

---

## Monitoring

### Railway Dashboard

**Metrics Available:**
- CPU usage
- Memory usage
- Network traffic
- Request count
- Error rate

**Logs:**
- Real-time log streaming
- Search and filter
- Download logs

### Application Endpoints

**Health Check:**
```bash
curl https://your-app.up.railway.app/api/v1/health
```

**Prometheus Metrics:**
```bash
curl https://your-app.up.railway.app/metrics
```

**Version Info:**
```bash
curl https://your-app.up.railway.app/version
```

---

## Scaling

### Vertical Scaling
Railway automatically scales resources based on usage.

### Horizontal Scaling
Not currently supported (stateful app with local storage).

**For high traffic:**
1. Increase `WORKERS` (default: 2, max: 8)
2. Increase `MAX_CONCURRENT_DOWNLOADS` (default: 3, max: 10)
3. Increase Railway volume size

---

## Cost Estimation

**Railway Pricing (as of 2024):**
- **Hobby Plan:** $5/month (limited hours)
- **Developer Plan:** $20/month (500 hours)
- **Pro Plan:** $20/month (usage-based)

**Storage:**
- Railway volumes are billed separately
- ~$0.25/GB/month

**Example Monthly Cost:**
- Small deployment: $20 (Pro) + $12.50 (50GB volume) = $32.50/month
- Medium deployment: $20 (Pro) + $25 (100GB volume) = $45/month

---

## Security Best Practices

### 1. Set Strong API Key
```bash
# Generate 256-bit key
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Enable Authentication
```bash
REQUIRE_API_KEY=true
API_KEY=your-strong-key
```

### 3. Restrict CORS (if needed)
```bash
CORS_ORIGINS=https://your-frontend.com,https://your-app.com
```

### 4. Domain Whitelist (optional)
```bash
ALLOWED_DOMAINS=youtube.com,vimeo.com,dailymotion.com
```

### 5. Rate Limiting
```bash
RATE_LIMIT_RPS=2      # Requests per second
RATE_LIMIT_BURST=5    # Burst allowance
```

### 6. Keep Dependencies Updated
```bash
# Rebuild periodically to get latest yt-dlp
Railway Dashboard → Deployments → Redeploy
```

---

## Maintenance

### Update Application

**Method 1: Git Push (Automatic)**
```bash
git add .
git commit -m "Update"
git push origin main
# Railway auto-deploys
```

**Method 2: Manual Redeploy**
1. Railway Dashboard → Your Service
2. Deployments → Latest
3. Click "Redeploy"

### Update yt-dlp

Railway rebuilds the Docker image on each deploy, automatically installing the latest yt-dlp version.

**Force update:**
```bash
# Trigger rebuild without code changes
git commit --allow-empty -m "Force rebuild for yt-dlp update"
git push
```

### Backup Volume Data

**Important:** Railway volumes are persistent but consider backups.

**Backup strategy:**
1. Download files via API before auto-deletion
2. Use Railway CLI to backup volume
3. Implement cloud storage integration (future)

---

## Support

### Resources
- **Railway Docs:** https://docs.railway.app
- **Application Docs:** See `docs/` directory
- **API Reference:** `/docs` endpoint
- **Issues:** GitHub repository issues

### Getting Help

1. Check Railway logs first
2. Review this troubleshooting guide
3. Check application documentation
4. Open GitHub issue with:
   - Railway logs
   - Environment variables (redact API_KEY)
   - Steps to reproduce

---

## Quick Reference

### Essential URLs
- **Homepage:** `https://your-app.up.railway.app/`
- **API Docs:** `https://your-app.up.railway.app/docs`
- **Health:** `https://your-app.up.railway.app/api/v1/health`
- **Metrics:** `https://your-app.up.railway.app/metrics`

### Essential Variables
```bash
REQUIRE_API_KEY=false
API_KEY=your-key
STORAGE_DIR=/app/data
PUBLIC_BASE_URL=https://your-app.up.railway.app
ALLOW_YT_DOWNLOADS=true
```

### Common Commands
```bash
# Test API
curl https://your-app.up.railway.app/api/v1/health

# Create download
curl -X POST https://your-app.up.railway.app/api/v1/download \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/video"}'

# Check logs
railway logs
```

---

**Your app should now be successfully deployed on Railway!** 🎉

Access it at: `https://your-app.up.railway.app`
