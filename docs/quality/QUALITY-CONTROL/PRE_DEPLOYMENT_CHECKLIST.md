# Pre-Deployment Checklist
## Ultimate Media Downloader v3.0.0

**Deployment Target:** Railway Production
**Checklist Date:** November 5, 2025
**Required Completion:** Before production deployment
**Estimated Time:** 2-3 hours

---

## Phase 1: Code Fixes (30 minutes)

### BUG #1: API_KEY Validator Field Order
**Priority:** MEDIUM | **Time:** 5 minutes | **Blocker:** NO

**File:** `app/config.py`
**Lines:** 32-33, 134-144

**Current Code:**
```python
API_KEY: str = Field(default="", description="API authentication key")
REQUIRE_API_KEY: bool = Field(default=True, description="Enforce API key authentication")
```

**Fixed Code:**
```python
REQUIRE_API_KEY: bool = Field(default=True, description="Enforce API key authentication")
API_KEY: str = Field(default="", description="API authentication key")
```

**Steps:**
- [ ] Edit `app/config.py`
- [ ] Move `REQUIRE_API_KEY` field definition to line 32 (before API_KEY)
- [ ] Move `API_KEY` field definition to line 33 (after REQUIRE_API_KEY)
- [ ] Save file

**Verification:**
```bash
cd /Users/silvio/Documents/GitHub/railway-yt-dlp-service
python3 -c "import os; os.environ['REQUIRE_API_KEY']='false'; os.environ['API_KEY']=''; from app.config import Settings; s = Settings(); print('✓ FIXED')"
```

**Expected Output:** `✓ FIXED` (no validation error)

---

### BUG #2: List Field Environment Variable Parsing
**Priority:** HIGH | **Time:** 20 minutes | **Blocker:** NO

**File:** `app/config.py`
**Lines:** 93-106 (fields), 173-191 (validators)

**Add These Imports:**
```python
from typing import Union
from pydantic import BeforeValidator
from typing_extensions import Annotated
```

**Add These Helper Functions (before Settings class):**
```python
def parse_str_or_list(v: Union[str, list[str]]) -> list[str]:
    """Parse comma-separated string or list into list."""
    if isinstance(v, str):
        if not v:
            return []
        return [item.strip() for item in v.split(',') if item.strip()]
    return v if isinstance(v, list) else []

def parse_str_or_list_lower(v: Union[str, list[str]]) -> list[str]:
    """Parse comma-separated string or list into lowercase list."""
    if isinstance(v, str):
        if not v:
            return []
        return [item.strip().lower() for item in v.split(',') if item.strip()]
    return [item.lower() for item in v] if isinstance(v, list) else []
```

**Replace Field Definitions:**
```python
# OLD (remove these)
CORS_ORIGINS: List[str] = Field(
    default_factory=lambda: ["*"],
    description="Allowed CORS origins"
)

ALLOWED_DOMAINS: List[str] = Field(
    default_factory=list,
    description="Whitelist of allowed domains (empty = all allowed)"
)

# NEW (use these)
CORS_ORIGINS: Annotated[list[str], BeforeValidator(parse_str_or_list)] = Field(
    default_factory=lambda: ["*"],
    description="Allowed CORS origins (comma-separated string or JSON array)"
)

ALLOWED_DOMAINS: Annotated[list[str], BeforeValidator(parse_str_or_list_lower)] = Field(
    default_factory=list,
    description="Whitelist of allowed domains (comma-separated string or JSON array, empty = all allowed)"
)
```

**Remove Old Validators (lines 173-191):**
```python
# DELETE these methods:
@field_validator('CORS_ORIGINS', mode='before')
@classmethod
def parse_cors_origins(cls, v) -> List[str]:
    ...

@field_validator('ALLOWED_DOMAINS', mode='before')
@classmethod
def parse_allowed_domains(cls, v) -> List[str]:
    ...
```

**Steps:**
- [ ] Edit `app/config.py`
- [ ] Add imports at top of file
- [ ] Add helper functions before Settings class
- [ ] Replace CORS_ORIGINS field definition
- [ ] Replace ALLOWED_DOMAINS field definition
- [ ] Delete old validator methods
- [ ] Save file

**Verification:**
```bash
cd /Users/silvio/Documents/GitHub/railway-yt-dlp-service
python3 -c "import os; os.environ['ALLOWED_DOMAINS']='youtube.com,vimeo.com'; os.environ['CORS_ORIGINS']='http://localhost:3000,https://example.com'; os.environ['REQUIRE_API_KEY']='false'; os.environ['API_KEY']='test'; from app.config import Settings; s = Settings(); print('ALLOWED_DOMAINS:', s.ALLOWED_DOMAINS); print('CORS_ORIGINS:', s.CORS_ORIGINS); print('✓ FIXED')"
```

**Expected Output:**
```
ALLOWED_DOMAINS: ['youtube.com', 'vimeo.com']
CORS_ORIGINS: ['http://localhost:3000', 'https://example.com']
✓ FIXED
```

---

### Run Full Test Suite
**Priority:** CRITICAL | **Time:** 5 minutes

```bash
cd /Users/silvio/Documents/GitHub/railway-yt-dlp-service
python3 test_core_modules.py
```

**Expected Result:** 47/47 tests passing (100% pass rate)

**If tests fail:**
- Review error messages carefully
- Verify code changes were applied correctly
- Check for typos in field definitions
- Ensure imports are at the top of the file

---

## Phase 2: Railway Configuration (60 minutes)

### Create Railway Project
**Priority:** CRITICAL | **Time:** 10 minutes

- [ ] Log in to Railway dashboard (https://railway.app)
- [ ] Create new project
- [ ] Connect GitHub repository
- [ ] Select main branch
- [ ] Verify Dockerfile detected

### Configure Railway Volume
**Priority:** CRITICAL | **Time:** 10 minutes

**Volume Configuration:**
- [ ] Navigate to project → Storage tab
- [ ] Create new Volume
- [ ] Name: `media-downloads`
- [ ] Size: 10GB (adjust based on needs)
- [ ] Mount path: `/app/data`
- [ ] Attach to service

**Verification:**
- [ ] Confirm mount path is `/app/data`
- [ ] Verify volume is attached to correct service

### Generate Production Credentials
**Priority:** CRITICAL | **Time:** 5 minutes

**Generate API Key:**
```bash
openssl rand -hex 32
```

**Example output:** `a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456`

- [ ] Copy API key to secure location (password manager)
- [ ] Save for Railway environment variable setup

**Security Note:**
- Use 32-byte (64 character) hex string minimum
- Never commit to git
- Rotate every 90 days in production

### Configure Environment Variables
**Priority:** CRITICAL | **Time:** 20 minutes

**Railway Dashboard → Variables:**

**Required Variables:**
```bash
# Authentication (CRITICAL)
API_KEY=<your-generated-api-key-from-above>
REQUIRE_API_KEY=true

# Storage (CRITICAL)
STORAGE_DIR=/app/data
PUBLIC_BASE_URL=https://your-app-name.up.railway.app

# Security (RECOMMENDED)
ALLOW_YT_DOWNLOADS=false
ALLOWED_DOMAINS=

# Performance (RECOMMENDED)
WORKERS=2
MAX_CONCURRENT_DOWNLOADS=10
RATE_LIMIT_RPS=2
RATE_LIMIT_BURST=5

# Timeouts (RECOMMENDED)
DEFAULT_TIMEOUT_SEC=1800
PROGRESS_TIMEOUT_SEC=300
MAX_CONTENT_LENGTH=10737418240

# Logging (RECOMMENDED)
LOG_LEVEL=INFO
LOG_DIR=/app/logs

# Server (RECOMMENDED)
PORT=8080
HOST=0.0.0.0

# CORS (OPTIONAL - default is *)
# CORS_ORIGINS=https://yourdomain.com,https://anotherdomain.com
```

**Steps:**
- [ ] Open Railway project → Variables tab
- [ ] Add each variable above
- [ ] Replace `<your-generated-api-key-from-above>` with actual key
- [ ] Replace `https://your-app-name.up.railway.app` with actual Railway URL
- [ ] Click "Save" after each variable
- [ ] Verify all variables are set

**Important Notes:**
- PUBLIC_BASE_URL: Use Railway's generated URL (check Deployments tab)
- STORAGE_DIR: Must match volume mount path (`/app/data`)
- API_KEY: Never share or commit this value

### Configure Custom Domain (Optional)
**Priority:** OPTIONAL | **Time:** 15 minutes

**If using custom domain:**
- [ ] Navigate to project → Settings → Domains
- [ ] Add custom domain
- [ ] Update DNS records (CNAME or A record)
- [ ] Wait for SSL certificate provisioning (5-10 minutes)
- [ ] Update `PUBLIC_BASE_URL` environment variable to custom domain
- [ ] Redeploy service

---

## Phase 3: Deployment Verification (45 minutes)

### Initial Deployment
**Priority:** CRITICAL | **Time:** 10 minutes

- [ ] Trigger deployment (push to main or manual deploy)
- [ ] Monitor Railway build logs
- [ ] Wait for build to complete (3-5 minutes)
- [ ] Verify service status: "Running"

**Watch for errors:**
- Configuration validation errors
- Volume mount failures
- Port binding issues
- Health check failures

### Health Check Verification
**Priority:** CRITICAL | **Time:** 5 minutes

**Test Health Endpoint:**
```bash
curl -s https://your-app-name.up.railway.app/api/v1/health | jq
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-05T12:00:00Z",
  "version": "3.0.0",
  "checks": {
    "application": "healthy",
    "queue_manager": "healthy",
    "storage": "healthy",
    "scheduler": "healthy"
  },
  "uptime_seconds": 42.5
}
```

**Verify each check:**
- [ ] `status: "healthy"`
- [ ] `application: "healthy"`
- [ ] `queue_manager: "healthy"`
- [ ] `storage: "healthy"`
- [ ] `scheduler: "healthy"`

**If unhealthy:**
- Check Railway logs for errors
- Verify environment variables are set
- Verify volume is mounted correctly
- Check application startup logs

### API Endpoint Testing
**Priority:** CRITICAL | **Time:** 20 minutes

**Save your API key:**
```bash
export API_KEY="your-api-key-from-railway"
export BASE_URL="https://your-app-name.up.railway.app"
```

**Test 1: Root Endpoint**
```bash
curl -s $BASE_URL/ | jq
```

**Expected:** Service information JSON

**Test 2: Version Endpoint**
```bash
curl -s $BASE_URL/version | jq
```

**Expected:**
```json
{
  "version": "3.0.0",
  "app_name": "Ultimate Media Downloader",
  "build_date": "2025-11-05",
  "features": ["yt-dlp", "railway-storage", "auto-deletion", "playlist-support", "metadata-extraction"]
}
```

**Test 3: Authentication (Should Fail)**
```bash
curl -s -X POST $BASE_URL/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/video"}' | jq
```

**Expected:** 401 Unauthorized (authentication required)

**Test 4: Authentication (Should Succeed)**
```bash
curl -s -X POST $BASE_URL/api/v1/download \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"}' | jq
```

**Expected:** 202 Accepted with job details

**Test 5: Metadata Extraction**
```bash
curl -s "$BASE_URL/api/v1/metadata?url=https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4" \
  -H "X-API-Key: $API_KEY" | jq
```

**Expected:** Video metadata JSON

**Test 6: Rate Limiting**
```bash
for i in {1..10}; do
  curl -s -X POST $BASE_URL/api/v1/download \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://example.com/video"}' | jq -r '.error // .status'
done
```

**Expected:** First few succeed, then "Rate limit exceeded"

**Test 7: Metrics Endpoint**
```bash
curl -s $BASE_URL/metrics | head -20
```

**Expected:** Prometheus metrics format

**Checklist:**
- [ ] Root endpoint responds
- [ ] Version endpoint shows correct version
- [ ] Authentication blocks unauthenticated requests
- [ ] Authentication allows valid API key
- [ ] Metadata extraction works
- [ ] Rate limiting triggers after threshold
- [ ] Metrics endpoint returns data

### Monitoring Setup
**Priority:** HIGH | **Time:** 10 minutes

**Railway Dashboard:**
- [ ] Navigate to Observability tab
- [ ] Verify metrics are being collected
- [ ] Check CPU usage (should be low at idle)
- [ ] Check memory usage (should be <100MB at idle)
- [ ] Monitor logs for errors

**Set Up Alerts (Optional):**
- [ ] CPU usage >80%
- [ ] Memory usage >500MB
- [ ] Error rate >5%
- [ ] Disk usage >80%

---

## Phase 4: Smoke Testing (30 minutes)

### Test Download Flow
**Priority:** CRITICAL | **Time:** 15 minutes

**Test with safe, small video file:**
```bash
# 1. Create download job
RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/download \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
    "quality": "best",
    "timeout_sec": 300
  }')

echo "Response: $RESPONSE"

# 2. Extract request ID
REQUEST_ID=$(echo $RESPONSE | jq -r '.request_id')
echo "Request ID: $REQUEST_ID"

# 3. Check status (wait 10 seconds for download)
sleep 10
curl -s $BASE_URL/api/v1/download/$REQUEST_ID \
  -H "X-API-Key: $API_KEY" | jq

# 4. Get logs
curl -s $BASE_URL/api/v1/download/$REQUEST_ID/logs \
  -H "X-API-Key: $API_KEY" | jq

# 5. Download file (if status is COMPLETED)
FILE_URL=$(curl -s $BASE_URL/api/v1/download/$REQUEST_ID \
  -H "X-API-Key: $API_KEY" | jq -r '.file_info.file_url // empty')

if [ -n "$FILE_URL" ]; then
  echo "Downloading file from: $FILE_URL"
  curl -o test_download.mp4 "$FILE_URL"
  ls -lh test_download.mp4
  echo "✓ Download flow works!"
else
  echo "✗ Download failed - check logs"
fi
```

**Verify:**
- [ ] Job created successfully (202 response)
- [ ] Job transitioned to RUNNING status
- [ ] Job completed with COMPLETED status
- [ ] File URL is generated
- [ ] File can be downloaded
- [ ] File size matches expected (~1MB)
- [ ] Logs show download progress

**If download fails:**
- Check Railway logs for yt-dlp errors
- Verify storage volume is writable
- Check network connectivity
- Try with different test URL

### Test File Cleanup
**Priority:** HIGH | **Time:** 10 minutes

**Verify auto-deletion scheduler:**
```bash
# Check scheduler status in logs
curl -s $BASE_URL/api/v1/health | jq '.checks.scheduler'
```

**Expected:** `"healthy"`

**Manual verification (after 1 hour):**
- [ ] Downloaded files are automatically deleted
- [ ] Storage directory is cleaned up
- [ ] No orphaned files remain

**Immediate verification:**
- [ ] Scheduler is running (health check)
- [ ] Deletion tasks are logged in application logs
- [ ] Storage stats show file count and size

### Test Error Handling
**Priority:** MEDIUM | **Time:** 5 minutes

**Test 1: Invalid URL**
```bash
curl -s -X POST $BASE_URL/api/v1/download \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "not-a-valid-url"}' | jq
```

**Expected:** 422 Unprocessable Entity (validation error)

**Test 2: Unsupported URL**
```bash
curl -s -X POST $BASE_URL/api/v1/download \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://unsupported-platform-12345.com/video"}' | jq
```

**Expected:** Job created, then fails with error message

**Test 3: Invalid API Key**
```bash
curl -s -X POST $BASE_URL/api/v1/download \
  -H "X-API-Key: invalid-key-123" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/video"}' | jq
```

**Expected:** 401 Unauthorized

**Checklist:**
- [ ] Invalid URLs are rejected with 422
- [ ] Unsupported URLs fail gracefully
- [ ] Invalid API keys are rejected with 401
- [ ] Error messages are clear and helpful
- [ ] No stack traces exposed in errors

---

## Phase 5: Security Validation (30 minutes)

### Path Traversal Testing
**Priority:** CRITICAL | **Time:** 10 minutes

**Test path traversal protection:**
```bash
# These should all fail with 400 or 404
curl -s "$BASE_URL/files/../../../etc/passwd"
curl -s "$BASE_URL/files/..%2F..%2F..%2Fetc%2Fpasswd"
curl -s "$BASE_URL/files/%252e%252e%252fetc%252fpasswd"
```

**Expected:** 400 Bad Request or 404 Not Found (NOT file contents)

**Verification:**
- [ ] Cannot access files outside storage directory
- [ ] Path validation blocks traversal attempts
- [ ] No error message reveals file system structure

### Rate Limit Verification
**Priority:** HIGH | **Time:** 10 minutes

**Test rate limiting:**
```bash
# Rapid-fire 20 requests
for i in {1..20}; do
  STATUS=$(curl -s -w "%{http_code}" -o /dev/null \
    -H "X-API-Key: $API_KEY" \
    $BASE_URL/api/v1/health)
  echo "Request $i: HTTP $STATUS"
done
```

**Expected:**
- First 5-7 requests: HTTP 200 (within burst)
- Subsequent requests: HTTP 429 (rate limited)
- After ~1 second: HTTP 200 (limit reset)

**Verify:**
- [ ] Rate limiting triggers after threshold
- [ ] Retry-After header present in 429 responses
- [ ] Rate limit resets after time window
- [ ] Different API keys have independent limits

### Authentication Verification
**Priority:** CRITICAL | **Time:** 5 minutes

**Test authentication bypass attempts:**
```bash
# No header
curl -s -X POST $BASE_URL/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' | jq -r '.error'

# Empty header
curl -s -X POST $BASE_URL/api/v1/download \
  -H "X-API-Key: " \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' | jq -r '.error'

# Wrong header name
curl -s -X POST $BASE_URL/api/v1/download \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' | jq -r '.error'
```

**Expected:** All return 401 Unauthorized

**Verify:**
- [ ] Cannot bypass authentication
- [ ] All protected endpoints require X-API-Key header
- [ ] Invalid keys are rejected
- [ ] Error messages don't leak information

### CORS Verification
**Priority:** MEDIUM | **Time:** 5 minutes

**Test CORS headers:**
```bash
curl -s -X OPTIONS $BASE_URL/api/v1/health \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: GET" \
  -v 2>&1 | grep -i "access-control"
```

**Expected CORS headers:**
- `Access-Control-Allow-Origin: *` (or configured origins)
- `Access-Control-Allow-Methods: *`
- `Access-Control-Allow-Headers: *`

**Verify:**
- [ ] CORS headers present in responses
- [ ] OPTIONS requests handled correctly
- [ ] Rate limit headers exposed

---

## Phase 6: Performance Validation (20 minutes)

### Load Testing
**Priority:** MEDIUM | **Time:** 10 minutes

**Test concurrent requests:**
```bash
# Install hey (HTTP load testing tool) if needed
# brew install hey  # macOS
# apt-get install hey  # Ubuntu

# Run load test (50 requests, 10 concurrent)
hey -n 50 -c 10 \
  -H "X-API-Key: $API_KEY" \
  $BASE_URL/api/v1/health
```

**Analyze results:**
- [ ] Success rate >95%
- [ ] Average response time <200ms
- [ ] P95 response time <500ms
- [ ] No errors or timeouts

**Monitor Railway dashboard during load test:**
- [ ] CPU usage stays <80%
- [ ] Memory usage stays <500MB
- [ ] No service restarts
- [ ] No error spikes in logs

### Memory Leak Check
**Priority:** MEDIUM | **Time:** 5 minutes

**Monitor memory over time:**
1. [ ] Note initial memory usage (Railway dashboard)
2. [ ] Run 100 health check requests
3. [ ] Wait 2 minutes
4. [ ] Note final memory usage
5. [ ] Verify memory returned to baseline (<10% increase acceptable)

**Expected:** Memory usage should stabilize, no continuous growth

### Response Time Baseline
**Priority:** MEDIUM | **Time:** 5 minutes

**Measure baseline response times:**
```bash
# Health endpoint
for i in {1..10}; do
  curl -s -w "Time: %{time_total}s\n" -o /dev/null \
    -H "X-API-Key: $API_KEY" \
    $BASE_URL/api/v1/health
done
```

**Baseline targets:**
- Health endpoint: <50ms
- Metadata endpoint: <500ms
- Download creation: <200ms

**Document baselines for monitoring:**
- [ ] Record P50, P95, P99 response times
- [ ] Set up alerts for degradation (>2x baseline)

---

## Phase 7: Documentation & Handoff (15 minutes)

### Update Documentation
**Priority:** HIGH | **Time:** 10 minutes

- [ ] Update README with deployed URL
- [ ] Document API key for authorized users
- [ ] Add production configuration notes
- [ ] Document monitoring dashboard access
- [ ] Update troubleshooting section

### Create Runbook
**Priority:** HIGH | **Time:** 5 minutes

**Document in Railway or wiki:**
- [ ] Deployment procedure
- [ ] Rollback procedure
- [ ] Common issues and solutions
- [ ] Monitoring dashboard links
- [ ] On-call escalation contacts

---

## Final Checklist Summary

### Code & Configuration
- [ ] BUG #1 fixed (API_KEY validator)
- [ ] BUG #2 fixed (list field parsing)
- [ ] Test suite passes (47/47 tests)
- [ ] Railway volume created and mounted
- [ ] All environment variables set
- [ ] API key generated and secured

### Deployment
- [ ] Application deployed successfully
- [ ] Health checks passing
- [ ] All API endpoints responding
- [ ] Authentication working correctly
- [ ] Rate limiting enforced
- [ ] Metrics endpoint accessible

### Testing
- [ ] Full download flow verified
- [ ] File cleanup scheduler working
- [ ] Error handling tested
- [ ] Security validation passed
- [ ] Performance baselines established
- [ ] Load testing completed

### Security
- [ ] Path traversal blocked
- [ ] Authentication cannot be bypassed
- [ ] Rate limiting active
- [ ] CORS configured correctly
- [ ] No secrets exposed in logs
- [ ] API key secured

### Monitoring
- [ ] Railway dashboard configured
- [ ] Metrics collection verified
- [ ] Logs accessible and structured
- [ ] Alerts configured (optional)
- [ ] Baseline metrics documented

### Documentation
- [ ] README updated
- [ ] API documentation accessible
- [ ] Runbook created
- [ ] Known issues documented
- [ ] Support contacts listed

---

## Go/No-Go Decision

**Review all checkboxes above. Deployment is approved when:**
- ✓ All CRITICAL items completed (Code Fixes, Configuration, Core Testing)
- ✓ All HIGH items completed (Security, Monitoring Setup)
- ✓ At least 80% of MEDIUM items completed

**If any CRITICAL items are incomplete: DO NOT DEPLOY**

**Deployment Sign-Off:**
- Prepared by: _____________________
- Reviewed by: _____________________
- Approved by: _____________________
- Date: _____________________

---

## Post-Deployment Monitoring (First 48 Hours)

### Hour 1
- [ ] Monitor Railway logs continuously
- [ ] Verify no errors in application logs
- [ ] Check health endpoint every 5 minutes
- [ ] Monitor memory/CPU usage

### Hours 2-8
- [ ] Check health endpoint every 30 minutes
- [ ] Review logs for errors hourly
- [ ] Monitor file cleanup scheduler
- [ ] Track download success rate

### Hours 9-24
- [ ] Check health endpoint every hour
- [ ] Review error logs twice
- [ ] Verify auto-deletion working
- [ ] Monitor storage usage

### Hours 25-48
- [ ] Daily health check review
- [ ] Daily log review
- [ ] Storage usage trends
- [ ] Performance metrics review

**After 48 hours: Move to standard monitoring cadence**

---

## Emergency Rollback Procedure

**If critical issues are discovered:**

1. **Immediately:**
   - [ ] Stop accepting new downloads (via environment variable)
   - [ ] Notify stakeholders

2. **Assess:**
   - [ ] Check Railway logs for root cause
   - [ ] Determine if fixable with environment variable change
   - [ ] Decide: Fix forward or rollback

3. **Rollback (if needed):**
   ```bash
   # Railway CLI or Dashboard
   railway rollback <previous-deployment-id>
   ```

4. **Verify:**
   - [ ] Previous version deployed
   - [ ] Service healthy
   - [ ] Issue resolved

5. **Post-Mortem:**
   - [ ] Document what went wrong
   - [ ] Identify root cause
   - [ ] Plan fix and re-deployment

---

**END OF PRE-DEPLOYMENT CHECKLIST**

**Next Steps After Completion:**
1. File this checklist in project documentation
2. Begin 48-hour monitoring period
3. Schedule 7-day post-deployment review
4. Plan next iteration improvements
