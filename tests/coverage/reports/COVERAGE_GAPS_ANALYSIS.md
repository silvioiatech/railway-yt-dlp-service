# Code Coverage Gaps Analysis - Untested Code Paths

## Summary

**Overall Coverage:** 54% (1,294 / 2,381 statements covered)  
**Untested Statements:** 1,087 (46%)

This document details all untested code paths identified during comprehensive coverage testing.

---

## Critical Gaps (High Priority for Testing)

### 1. API Layer - Complete Gap (475 statements, 0% covered)

All API endpoints are untested. These handle HTTP requests and are critical for production.

**app/api/v1/auth.py** (27 statements)
```
Untested code paths:
- API key validation middleware
- require_api_key dependency
- optional_api_key dependency
- Authentication error responses
```

**app/api/v1/download.py** (125 statements)
```
Untested code paths:
- POST /download - Single video download
- GET /download/{request_id} - Get download status
- DELETE /download/{request_id} - Cancel download
- POST /batch - Batch download
- GET /batch/{batch_id} - Batch status
- Error handling for all endpoints
- Background task initiation
- Job queue integration
```

**app/api/v1/health.py** (114 statements)
```
Untested code paths:
- GET /health - Basic health check
- GET /health/detailed - Detailed health status
- GET /stats - Service statistics
- Storage space checks
- yt-dlp version detection
- Active job counting
- System metrics collection
```

**app/api/v1/metadata.py** (96 statements)
```
Untested code paths:
- POST /metadata - Extract video metadata
- POST /formats - Get available formats
- Error handling for invalid URLs
- ytdlp_wrapper integration
- Response formatting
```

**app/api/v1/playlist.py** (105 statements)
```
Untested code paths:
- POST /playlist/preview - Preview playlist items
- POST /playlist/download - Download playlist
- Pagination logic
- Item filtering
- Error handling
```

**Recommendation:** Create API integration test suite using FastAPI TestClient

---

### 2. ytdlp_wrapper Execution - Critical Gap (159 statements, 14% covered)

**app/services/ytdlp_wrapper.py**

```
Tested (14%):
- Class initialization
- Basic structure

Untested (86%):
- ProgressTracker callback mechanism (lines 51-149)
  - Progress updates during download
  - Status transitions
  - Callback error handling (3 retry limit)
  
- YtdlpWrapper.extract_info (lines 171-224)
  - Actual metadata extraction
  - Timeout handling
  - Cookie authentication
  - Error conversion to MetadataExtractionError
  
- YtdlpWrapper.get_formats (lines 241-308)
  - Format categorization (combined, video-only, audio-only)
  - Best format recommendation
  - Format sorting by quality
  
- YtdlpWrapper.download (lines 352-418)
  - Actual download execution
  - Progress hook integration
  - Timeout handling
  - Result extraction from yt-dlp
  
- YtdlpWrapper.download_playlist (lines 451-534)
  - Playlist download
  - Entry counting
  - Error aggregation
  
- YtdlpWrapper.download_channel (lines 536-620)
  - Channel download
  - Entry filtering
```

**Why untested:** Requires mocking yt-dlp library (YoutubeDL class)

**Recommendation:** Create mock YoutubeDL with controlled responses

---

### 3. Application Lifecycle - Complete Gap (159 statements, 0% covered)

**app/main.py**

```
Untested code paths:
- FastAPI app initialization
- Startup event handlers:
  - Settings validation
  - Queue manager initialization
  - Static file mounting
  - CORS middleware setup
  
- Shutdown event handlers:
  - Queue manager cleanup
  - Scheduler cleanup
  - Graceful shutdown
  
- Exception handlers:
  - MediaDownloaderException handler
  - Validation error handler
  - General exception handler
  
- Route registration:
  - API v1 routes
  - File serving routes
  - Health check routes
  
- Signal handling (SIGTERM, SIGINT)
- Logging configuration
- Version endpoint
```

**Recommendation:** Test with uvicorn or hypercorn test server

---

## Moderate Gaps (Should Be Tested)

### 4. Middleware - Complete Gap (35 statements, 0% covered)

**app/middleware/rate_limit.py**

```
Untested code paths:
- RateLimitMiddleware initialization
- SlowAPI integration
- Rate limit enforcement
- X-RateLimit headers
- 429 Too Many Requests responses
- Exempted paths handling
```

**Recommendation:** Integration test with test requests

---

### 5. Queue Manager Error Paths (51 statements untested)

**app/services/queue_manager.py**

```
Tested (68%):
- Basic start/shutdown
- Job submission
- Job status tracking
- Health check

Untested (32%):
- Double start protection (lines 61-62, 66)
- Shutdown when not started (lines 97-98)
- Queue at capacity error (lines 153-154)
- Coroutine execution errors (line 192, 205-206)
- Job status with exception (lines 250-255)
- Cancel non-existent job (lines 272-273)
- Cancel completed job (lines 276-277)
- Executor shutdown attribute error (lines 325-329)
- wait_for_capacity timeout (lines 343-352)
- Global manager initialization (lines 374-378, 388-391, 403-405)
```

**Recommendation:** Add error injection tests

---

### 6. Scheduler Worker Loop (31 statements untested)

**app/core/scheduler.py**

```
Tested (73%):
- Singleton pattern
- Basic scheduling
- Cancellation
- Thread safety

Untested (27%):
- Worker loop shutdown condition (line 75)
- Cancelled task removal (lines 82-84, 87)
- Task execution outside lock (lines 93-106)
- File deletion errors (lines 116-132)
- Shutdown timeout warning (line 197)
```

**Recommendation:** Add worker loop lifecycle tests

---

### 7. File Manager Error Handling (29 statements untested)

**app/services/file_manager.py**

```
Tested (82%):
- Core operations
- Path security
- Filename sanitization

Untested (18%):
- Upload date parsing error (lines 89-92)
- Filename truncation edge case (line 159)
- validate_path exception cases (line 205)
- get_file_info directory error (line 230)
- delete_file error handling (lines 268, 277-280)
- schedule_deletion validation (line 308)
- cleanup iteration errors (lines 358-359, 369-371, 399-400, 405-407)
- get_relative_path exception (lines 425-426)
- get_public_url validation (lines 445-446)
```

**Recommendation:** Add error injection tests

---

### 8. Config Validation Function (17 statements untested)

**app/config.py**

```
Tested (84%):
- Settings class
- All validators
- Properties

Untested (16%):
- validate_settings() function (lines 234-260)
  - Directory existence checks
  - API key requirement check
  - YouTube download warning
  - Configuration summary output
```

**Recommendation:** Add validate_settings() unit tests

---

### 9. Request Model Edge Cases (40 statements untested)

**app/models/requests.py**

```
Tested (87%):
- Core validation
- Main error paths

Untested (13%):
- Some error message formatting (lines 88, 121, 189, 193)
- Range validation edge cases (lines 210, 214-216, 222)
- Date validation corner cases (lines 316, 320, 337, 341, 348-352, 368-372)
- URL validation specifics (lines 437, 443, 445, 449)
- Cookie validation details (lines 487, 492, 500, 508)
- Browser validation (lines 519-529)
- Name validation (lines 538, 541, 545)
```

**Recommendation:** Add more edge case tests

---

### 10. Exception Detail Formatting (18 statements untested)

**app/core/exceptions.py**

```
Tested (82%):
- All exception types
- Basic to_dict()

Untested (18%):
- Some detail formatting (lines 35, 93, 121-124, 136-139, 189-194, 252, 264-268, 276, 289)
```

**Recommendation:** Test with various detail combinations

---

### 11. yt-dlp Options Edge Cases (17 statements untested)

**app/services/ytdlp_options.py**

```
Tested (87%):
- Core option building
- Format selection
- Postprocessors

Untested (13%):
- Custom format fallback (line 108)
- Format string default (line 127)
- Auto subtitles conditional (line 145)
- Write info json conditional (line 189)
- Playlist range edge cases (lines 298-301)
- Date filter edge cases (lines 360, 368, 371, 373)
- Batch template edge cases (lines 418-428)
```

**Recommendation:** Add format selection edge case tests

---

## Low Priority Gaps

### 12. Utils Module (45 statements, 0% covered)

**app/utils/logger.py** (40 statements)
```
Untested:
- Logging configuration
- Rotating file handlers
- Console handlers
- Format setup
```

**app/utils/__init__.py** (5 statements)
```
Untested:
- Module exports
```

**Recommendation:** Lower priority, utility functions

---

### 13. Init Files (12 statements, mixed coverage)

**app/api/v1/__init__.py** (2 statements, 0%)
```
Untested:
- Module imports
```

**app/middleware/__init__.py** (2 statements, 0%)
```
Untested:
- Module imports
```

**Recommendation:** Integration tests will cover these

---

## Testing Strategy for Gaps

### Phase 1: Critical (High Impact)
1. **API Integration Tests** (~6 hours)
   - Use FastAPI TestClient
   - Test all endpoints
   - Expected coverage gain: +475 statements (~20%)

2. **ytdlp_wrapper Mocking** (~3 hours)
   - Mock YoutubeDL responses
   - Test download execution
   - Expected coverage gain: +159 statements (~7%)

3. **Application Lifecycle** (~2 hours)
   - Test startup/shutdown
   - Test signal handling
   - Expected coverage gain: +159 statements (~7%)

### Phase 2: Important (Medium Impact)
4. **Middleware Tests** (~1 hour)
   - Test rate limiting
   - Expected coverage gain: +35 statements (~1%)

5. **Error Recovery** (~2 hours)
   - Queue manager errors
   - Scheduler errors
   - File manager errors
   - Expected coverage gain: +111 statements (~5%)

### Phase 3: Polish (Low Impact)
6. **Edge Cases** (~2 hours)
   - Config validation
   - Request model corners
   - Exception details
   - Expected coverage gain: +75 statements (~3%)

7. **Utils** (~1 hour)
   - Logger configuration
   - Expected coverage gain: +45 statements (~2%)

### Total Estimated Effort
- **17 hours of testing work**
- **Expected final coverage: 97%** (2,312 / 2,381 statements)

---

## Code Paths Never Exercised

### Critical Paths
1. HTTP request handling
2. Actual yt-dlp download execution
3. Metadata extraction with real URLs
4. Format detection and recommendation
5. Progress callback mechanism
6. Application startup/shutdown

### Error Paths
1. Rate limit exceeded (429 response)
2. Queue full error (503 response)
3. ytdlp timeout with progress stall
4. Callback error after 3 retries
5. Worker thread shutdown timeout
6. Directory permission denied on startup

### Edge Cases
1. Empty playlist handling
2. Invalid cookie file format
3. Malformed date in channel filter
4. Negative duration in filter
5. Queue submission during shutdown
6. Concurrent job cancellation

---

## Recommendations Summary

### Must Have Before Production
1. ✗ API endpoint integration tests
2. ✗ Download execution with mocked yt-dlp
3. ✗ Application lifecycle tests

### Should Have Before Production
4. ✗ Error recovery path tests
5. ✗ Middleware integration tests

### Nice to Have
6. ✗ Edge case coverage improvements
7. ✗ Utils module tests

### Current State
- **Ready for Production:** Core services, models, state management (54% covered)
- **Not Ready:** API layer, download execution, application lifecycle (0% covered)

**Overall Assessment:** 54% coverage is **good for business logic** but **insufficient for API service** deployment. Need integration tests before production.

---

**Generated:** November 5, 2025  
**Analysis Tool:** pytest-cov 7.0.0  
**Source:** test_comprehensive_coverage.py (91 tests)

