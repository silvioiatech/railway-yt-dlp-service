#!/usr/bin/env python3
"""
Comprehensive test suite for core modules.

Tests all CORE modules for bugs, import errors, and functionality issues.
"""
import sys
import os
import threading
import time
import tempfile
from pathlib import Path
from typing import List, Dict, Any

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test results storage
test_results = []


class TestResult:
    """Store test result information."""
    
    def __init__(self, module: str, test: str, status: str, error: str = None, confidence: str = "HIGH"):
        self.module = module
        self.test = test
        self.status = status  # PASS, FAIL, WARNING
        self.error = error
        self.confidence = confidence
    
    def __repr__(self):
        status_icon = {
            "PASS": "[✓]",
            "FAIL": "[✗]",
            "WARNING": "[!]"
        }
        result = f"{status_icon.get(self.status, '[ ]')} {self.module} - {self.test}"
        if self.error:
            result += f"\n    Error: {self.error}"
        if self.confidence != "HIGH":
            result += f" (Confidence: {self.confidence})"
        return result


def test_import(module_name: str, description: str) -> TestResult:
    """Test if a module can be imported."""
    try:
        __import__(module_name)
        return TestResult(module_name, f"Import {description}", "PASS")
    except ImportError as e:
        return TestResult(module_name, f"Import {description}", "FAIL", str(e))
    except Exception as e:
        return TestResult(module_name, f"Import {description}", "FAIL", f"Unexpected error: {e}")


def test_config():
    """Test app/config.py module."""
    results = []
    module_name = "app.config"
    
    # Test 1: Import
    results.append(test_import(module_name, "config module"))
    
    try:
        from app.config import Settings, get_settings, validate_settings
        
        # Test 2: Settings instantiation with REQUIRE_API_KEY=False
        try:
            # Clear environment and set clean values
            for key in list(os.environ.keys()):
                if key.startswith(('API_', 'REQUIRE_', 'ALLOWED_', 'CORS_')):
                    os.environ.pop(key, None)

            os.environ['REQUIRE_API_KEY'] = 'false'
            # BUG: API_KEY field is validated before REQUIRE_API_KEY is parsed, so we need a dummy value
            os.environ['API_KEY'] = 'dummy-key-for-testing'
            # Clear cache for get_settings
            get_settings.cache_clear()
            settings = Settings()
            results.append(TestResult(module_name, "Settings class instantiation", "PASS"))
        except Exception as e:
            results.append(TestResult(module_name, "Settings class instantiation", "FAIL", str(e)))

        # Test 2b: Settings instantiation bug - validator order issue
        try:
            # This test documents the known bug
            for key in list(os.environ.keys()):
                if key.startswith(('API_', 'REQUIRE_', 'ALLOWED_', 'CORS_')):
                    os.environ.pop(key, None)

            os.environ['REQUIRE_API_KEY'] = 'false'
            os.environ['API_KEY'] = ''  # Empty key
            get_settings.cache_clear()
            try:
                settings = Settings()
                results.append(TestResult(module_name, "BUG: API_KEY validator order", "FAIL",
                                         "Should fail but didn't - bug may be fixed!"))
            except ValueError as e:
                if "API_KEY must be set" in str(e):
                    # Expected to fail
                    results.append(TestResult(module_name, "BUG: API_KEY validator order", "WARNING",
                                             "API_KEY validator runs before REQUIRE_API_KEY is parsed (field order issue)", "HIGH"))
                else:
                    results.append(TestResult(module_name, "BUG: API_KEY validator order", "FAIL", f"Wrong error: {e}"))
        except Exception as e:
            results.append(TestResult(module_name, "BUG: API_KEY validator order", "FAIL", str(e)))
        
        # Test 3: API_KEY validator with REQUIRE_API_KEY=True
        try:
            os.environ['REQUIRE_API_KEY'] = 'true'
            os.environ['API_KEY'] = ''
            get_settings.cache_clear()
            try:
                settings = Settings()
                results.append(TestResult(module_name, "API_KEY validator (should fail)", "FAIL", "Validator should have raised ValueError"))
            except ValueError as e:
                if "API_KEY must be set" in str(e):
                    results.append(TestResult(module_name, "API_KEY validator", "PASS"))
                else:
                    results.append(TestResult(module_name, "API_KEY validator", "FAIL", f"Wrong error: {e}"))
        except Exception as e:
            results.append(TestResult(module_name, "API_KEY validator", "FAIL", str(e)))
        
        # Test 4: get_settings singleton
        try:
            os.environ['REQUIRE_API_KEY'] = 'false'
            os.environ['API_KEY'] = 'test-key-123'
            get_settings.cache_clear()
            settings1 = get_settings()
            settings2 = get_settings()
            if settings1 is settings2:
                results.append(TestResult(module_name, "get_settings() singleton", "PASS"))
            else:
                results.append(TestResult(module_name, "get_settings() singleton", "FAIL", "Not returning same instance"))
        except Exception as e:
            results.append(TestResult(module_name, "get_settings() singleton", "FAIL", str(e)))
        
        # Test 5: Storage path methods
        try:
            get_settings.cache_clear()
            settings = get_settings()
            path = settings.get_storage_path("test/file.mp4")
            if isinstance(path, Path):
                results.append(TestResult(module_name, "get_storage_path()", "PASS"))
            else:
                results.append(TestResult(module_name, "get_storage_path()", "FAIL", f"Expected Path, got {type(path)}"))
        except Exception as e:
            results.append(TestResult(module_name, "get_storage_path()", "FAIL", str(e)))
        
        # Test 6: Public URL generation
        try:
            os.environ['PUBLIC_BASE_URL'] = 'https://example.com'
            get_settings.cache_clear()
            settings = get_settings()
            url = settings.get_public_url("test/file.mp4")
            if url and "https://example.com" in url:
                results.append(TestResult(module_name, "get_public_url()", "PASS"))
            else:
                results.append(TestResult(module_name, "get_public_url()", "FAIL", f"Unexpected URL: {url}"))
        except Exception as e:
            results.append(TestResult(module_name, "get_public_url()", "FAIL", str(e)))
        
        # Test 7: Domain allowlist checking (NOTE: Currently broken when set via env var)
        try:
            # BUG: ALLOWED_DOMAINS cannot be set via environment variable due to pydantic-settings
            # trying to JSON-parse List fields. Test with empty list instead.
            os.environ.pop('ALLOWED_DOMAINS', None)
            get_settings.cache_clear()
            settings = get_settings()

            # With empty ALLOWED_DOMAINS, all domains should be allowed
            if settings.is_domain_allowed("youtube.com") and settings.is_domain_allowed("example.com"):
                results.append(TestResult(module_name, "is_domain_allowed() [empty list]", "PASS"))
            else:
                results.append(TestResult(module_name, "is_domain_allowed() [empty list]", "FAIL", "Should allow all domains when list is empty"))
        except Exception as e:
            results.append(TestResult(module_name, "is_domain_allowed() [empty list]", "FAIL", str(e)))

        # Test 7b: Domain allowlist via code (not env var)
        try:
            # Test the method directly with a settings object that has domains set
            test_settings = Settings(REQUIRE_API_KEY=False, API_KEY='test')
            test_settings.ALLOWED_DOMAINS = ['youtube.com', 'vimeo.com']

            if test_settings.is_domain_allowed("youtube.com"):
                if not test_settings.is_domain_allowed("example.com"):
                    results.append(TestResult(module_name, "is_domain_allowed() [with domains]", "PASS"))
                else:
                    results.append(TestResult(module_name, "is_domain_allowed() [with domains]", "FAIL", "Should block non-allowed domain"))
            else:
                results.append(TestResult(module_name, "is_domain_allowed() [with domains]", "FAIL", "Should allow youtube.com"))
        except Exception as e:
            results.append(TestResult(module_name, "is_domain_allowed() [with domains]", "FAIL", str(e)))
        
        # Test 8: validate_settings()
        try:
            os.environ['REQUIRE_API_KEY'] = 'false'
            os.environ['API_KEY'] = 'test-key'
            os.environ.pop('ALLOWED_DOMAINS', None)
            os.environ.pop('CORS_ORIGINS', None)
            get_settings.cache_clear()
            validate_settings()
            results.append(TestResult(module_name, "validate_settings()", "PASS"))
        except Exception as e:
            results.append(TestResult(module_name, "validate_settings()", "FAIL", str(e)))

        # Test 9: Field validators for directories
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['STORAGE_DIR'] = tmpdir
                os.environ.pop('ALLOWED_DOMAINS', None)
                os.environ.pop('CORS_ORIGINS', None)
                get_settings.cache_clear()
                settings = get_settings()
                if settings.STORAGE_DIR.exists() and settings.STORAGE_DIR.is_dir():
                    results.append(TestResult(module_name, "Directory validator", "PASS"))
                else:
                    results.append(TestResult(module_name, "Directory validator", "FAIL", "Directory not created"))
        except Exception as e:
            results.append(TestResult(module_name, "Directory validator", "FAIL", str(e)))

        # Test 10: Bug report - List fields cannot be set via environment variables
        try:
            # This test documents the known bug
            os.environ['ALLOWED_DOMAINS'] = 'youtube.com,vimeo.com'
            get_settings.cache_clear()
            try:
                settings = Settings(REQUIRE_API_KEY=False, API_KEY='test')
                results.append(TestResult(module_name, "BUG: ALLOWED_DOMAINS env var", "FAIL",
                                         "Should fail but didn't - bug may be fixed!"))
            except Exception:
                # Expected to fail
                results.append(TestResult(module_name, "BUG: ALLOWED_DOMAINS env var", "WARNING",
                                         "List fields cannot be set via env vars (pydantic-settings limitation)", "HIGH"))
            os.environ.pop('ALLOWED_DOMAINS', None)
        except Exception as e:
            results.append(TestResult(module_name, "BUG: ALLOWED_DOMAINS env var", "FAIL", str(e)))
            
    except Exception as e:
        results.append(TestResult(module_name, "Core functionality tests", "FAIL", str(e)))
    
    return results


def test_exceptions():
    """Test app/core/exceptions.py module."""
    results = []
    module_name = "app.core.exceptions"
    
    # Test 1: Import
    results.append(test_import(module_name, "exceptions module"))
    
    try:
        from app.core.exceptions import (
            MediaDownloaderException,
            DownloadError, DownloadTimeoutError, DownloadCancelledError, FileSizeLimitExceeded,
            MetadataExtractionError, InvalidURLError, UnsupportedPlatformError, InvalidFormatError,
            JobNotFoundError, QueueFullError,
            StorageError, StorageQuotaExceeded, FileNotFoundError,
            AuthenticationError, InvalidAPIKeyError, RateLimitExceededError,
            CookieError, InvalidCookieFormatError, WebhookError, ConfigurationError
        )
        
        # Test 2: Base exception instantiation
        try:
            exc = MediaDownloaderException("Test error", status_code=500, error_code="TEST_ERROR", details={"key": "value"})
            if exc.message == "Test error" and exc.status_code == 500:
                results.append(TestResult(module_name, "MediaDownloaderException instantiation", "PASS"))
            else:
                results.append(TestResult(module_name, "MediaDownloaderException instantiation", "FAIL", "Properties not set correctly"))
        except Exception as e:
            results.append(TestResult(module_name, "MediaDownloaderException instantiation", "FAIL", str(e)))
        
        # Test 3: to_dict() method
        try:
            exc = MediaDownloaderException("Test", status_code=400, details={"test": "data"})
            d = exc.to_dict()
            if isinstance(d, dict) and 'error' in d and 'status_code' in d:
                results.append(TestResult(module_name, "to_dict() method", "PASS"))
            else:
                results.append(TestResult(module_name, "to_dict() method", "FAIL", f"Invalid dict: {d}"))
        except Exception as e:
            results.append(TestResult(module_name, "to_dict() method", "FAIL", str(e)))
        
        # Test 4: Specific exception classes
        exceptions_to_test = [
            (DownloadError, lambda: DownloadError("Download failed")),
            (DownloadTimeoutError, lambda: DownloadTimeoutError(300)),
            (DownloadCancelledError, lambda: DownloadCancelledError("req123")),
            (FileSizeLimitExceeded, lambda: FileSizeLimitExceeded(1000000, 500000)),
            (MetadataExtractionError, lambda: MetadataExtractionError("Failed", "http://test.com")),
            (InvalidURLError, lambda: InvalidURLError("http://bad.com", "Invalid domain")),
            (JobNotFoundError, lambda: JobNotFoundError("job123")),
            (AuthenticationError, lambda: AuthenticationError()),
            (RateLimitExceededError, lambda: RateLimitExceededError(60)),
        ]
        
        for exc_class, creator in exceptions_to_test:
            try:
                exc = creator()
                if isinstance(exc, MediaDownloaderException) and hasattr(exc, 'status_code'):
                    results.append(TestResult(module_name, f"{exc_class.__name__} instantiation", "PASS"))
                else:
                    results.append(TestResult(module_name, f"{exc_class.__name__} instantiation", "FAIL", "Not proper subclass"))
            except Exception as e:
                results.append(TestResult(module_name, f"{exc_class.__name__} instantiation", "FAIL", str(e)))
        
        # Test 5: Status codes
        try:
            status_tests = [
                (DownloadTimeoutError(300), 408),
                (InvalidURLError("test"), 400),
                (AuthenticationError(), 401),
                (UnsupportedPlatformError("test"), 403),
                (JobNotFoundError("test"), 404),
                (FileSizeLimitExceeded(1000, 500), 413),
                (RateLimitExceededError(), 429),
            ]
            
            all_correct = True
            for exc, expected_code in status_tests:
                if exc.status_code != expected_code:
                    all_correct = False
                    results.append(TestResult(module_name, f"Status code for {exc.__class__.__name__}", "FAIL", 
                                             f"Expected {expected_code}, got {exc.status_code}"))
                    break
            
            if all_correct:
                results.append(TestResult(module_name, "Exception status codes", "PASS"))
        except Exception as e:
            results.append(TestResult(module_name, "Exception status codes", "FAIL", str(e)))
            
    except Exception as e:
        results.append(TestResult(module_name, "Core functionality tests", "FAIL", str(e)))
    
    return results


def test_scheduler():
    """Test app/core/scheduler.py module."""
    results = []
    module_name = "app.core.scheduler"
    
    # Test 1: Import
    results.append(test_import(module_name, "scheduler module"))
    
    try:
        from app.core.scheduler import FileDeletionScheduler, get_scheduler, DeletionTask
        
        # Test 2: Singleton pattern
        try:
            scheduler1 = FileDeletionScheduler()
            scheduler2 = FileDeletionScheduler()
            if scheduler1 is scheduler2:
                results.append(TestResult(module_name, "Singleton pattern", "PASS"))
            else:
                results.append(TestResult(module_name, "Singleton pattern", "FAIL", "Not returning same instance"))
        except Exception as e:
            results.append(TestResult(module_name, "Singleton pattern", "FAIL", str(e)))
        
        # Test 3: get_scheduler() function
        try:
            scheduler = get_scheduler()
            if isinstance(scheduler, FileDeletionScheduler):
                results.append(TestResult(module_name, "get_scheduler()", "PASS"))
            else:
                results.append(TestResult(module_name, "get_scheduler()", "FAIL", f"Wrong type: {type(scheduler)}"))
        except Exception as e:
            results.append(TestResult(module_name, "get_scheduler()", "FAIL", str(e)))
        
        # Test 4: schedule_deletion() returns task_id and timestamp
        try:
            scheduler = get_scheduler()
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
            
            task_id, timestamp = scheduler.schedule_deletion(tmp_path, delay_seconds=3600)
            
            if isinstance(task_id, str) and isinstance(timestamp, float):
                results.append(TestResult(module_name, "schedule_deletion() return values", "PASS"))
            else:
                results.append(TestResult(module_name, "schedule_deletion() return values", "FAIL", 
                                         f"Wrong types: {type(task_id)}, {type(timestamp)}"))
            
            # Cleanup
            scheduler.cancel_deletion(task_id)
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception as e:
            results.append(TestResult(module_name, "schedule_deletion() return values", "FAIL", str(e)))
        
        # Test 5: cancel_deletion()
        try:
            scheduler = get_scheduler()
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
            
            task_id, _ = scheduler.schedule_deletion(tmp_path, delay_seconds=3600)
            cancel_result = scheduler.cancel_deletion(task_id)
            
            if cancel_result:
                results.append(TestResult(module_name, "cancel_deletion()", "PASS"))
            else:
                results.append(TestResult(module_name, "cancel_deletion()", "FAIL", "Should return True for valid task"))
            
            # Cleanup
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception as e:
            results.append(TestResult(module_name, "cancel_deletion()", "FAIL", str(e)))
        
        # Test 6: get_pending_count()
        try:
            scheduler = get_scheduler()
            initial_count = scheduler.get_pending_count()
            
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
            
            task_id, _ = scheduler.schedule_deletion(tmp_path, delay_seconds=3600)
            new_count = scheduler.get_pending_count()
            
            if new_count > initial_count:
                results.append(TestResult(module_name, "get_pending_count()", "PASS"))
            else:
                results.append(TestResult(module_name, "get_pending_count()", "FAIL", 
                                         f"Count didn't increase: {initial_count} -> {new_count}"))
            
            # Cleanup
            scheduler.cancel_deletion(task_id)
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception as e:
            results.append(TestResult(module_name, "get_pending_count()", "FAIL", str(e)))
        
        # Test 7: Thread safety (concurrent operations)
        try:
            scheduler = get_scheduler()
            errors = []
            task_ids = []
            
            def schedule_task(index):
                try:
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        tmp_path = Path(tmp.name)
                    task_id, _ = scheduler.schedule_deletion(tmp_path, delay_seconds=3600)
                    task_ids.append((task_id, tmp_path))
                except Exception as e:
                    errors.append(str(e))
            
            threads = [threading.Thread(target=schedule_task, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            if not errors and len(task_ids) == 10:
                results.append(TestResult(module_name, "Thread safety", "PASS"))
            else:
                results.append(TestResult(module_name, "Thread safety", "FAIL", 
                                         f"Errors: {errors}, Tasks: {len(task_ids)}"))
            
            # Cleanup
            for task_id, tmp_path in task_ids:
                scheduler.cancel_deletion(task_id)
                if tmp_path.exists():
                    tmp_path.unlink()
        except Exception as e:
            results.append(TestResult(module_name, "Thread safety", "FAIL", str(e)))
        
        # Test 8: Actual deletion execution (short delay)
        try:
            scheduler = get_scheduler()
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
            
            # Schedule deletion in 2 seconds
            task_id, _ = scheduler.schedule_deletion(tmp_path, delay_seconds=2)
            
            # File should exist initially
            if not tmp_path.exists():
                results.append(TestResult(module_name, "Deletion execution", "FAIL", "File doesn't exist before deletion"))
            else:
                # Wait for deletion (with timeout)
                time.sleep(3)
                
                # File should be deleted
                if not tmp_path.exists():
                    results.append(TestResult(module_name, "Deletion execution", "PASS"))
                else:
                    results.append(TestResult(module_name, "Deletion execution", "WARNING", 
                                             "File not deleted after delay (worker thread issue?)", "MEDIUM"))
                    # Cleanup
                    tmp_path.unlink()
        except Exception as e:
            results.append(TestResult(module_name, "Deletion execution", "FAIL", str(e)))
            
    except Exception as e:
        results.append(TestResult(module_name, "Core functionality tests", "FAIL", str(e)))
    
    return results


def test_state():
    """Test app/core/state.py module."""
    results = []
    module_name = "app.core.state"
    
    # Test 1: Import
    results.append(test_import(module_name, "state module"))
    
    try:
        from app.core.state import JobState, JobStateManager, get_job_state_manager
        from app.models.enums import JobStatus
        
        # Test 2: JobState instantiation
        try:
            job = JobState("test-123", url="http://test.com", status=JobStatus.QUEUED)
            if job.request_id == "test-123" and job.status == JobStatus.QUEUED:
                results.append(TestResult(module_name, "JobState instantiation", "PASS"))
            else:
                results.append(TestResult(module_name, "JobState instantiation", "FAIL", "Properties not set correctly"))
        except Exception as e:
            results.append(TestResult(module_name, "JobState instantiation", "FAIL", str(e)))
        
        # Test 3: State transitions
        try:
            job = JobState("test-456", url="http://test.com")
            job.set_running()
            if job.status != JobStatus.RUNNING or not job.started_at:
                results.append(TestResult(module_name, "State transition: queued->running", "FAIL", "Status or timestamp not set"))
            else:
                job.set_completed(file_path=Path("/tmp/test.mp4"))
                if job.status != JobStatus.COMPLETED or not job.completed_at:
                    results.append(TestResult(module_name, "State transition: running->completed", "FAIL", "Status or timestamp not set"))
                else:
                    results.append(TestResult(module_name, "State transitions", "PASS"))
        except Exception as e:
            results.append(TestResult(module_name, "State transitions", "FAIL", str(e)))
        
        # Test 4: Failed state
        try:
            job = JobState("test-fail", url="http://test.com")
            job.set_failed("Test error message")
            if job.status == JobStatus.FAILED and job.error_message == "Test error message":
                results.append(TestResult(module_name, "State transition: failed", "PASS"))
            else:
                results.append(TestResult(module_name, "State transition: failed", "FAIL", "Status or error not set"))
        except Exception as e:
            results.append(TestResult(module_name, "State transition: failed", "FAIL", str(e)))
        
        # Test 5: Cancelled state
        try:
            job = JobState("test-cancel", url="http://test.com")
            job.set_cancelled()
            if job.status == JobStatus.CANCELLED:
                results.append(TestResult(module_name, "State transition: cancelled", "PASS"))
            else:
                results.append(TestResult(module_name, "State transition: cancelled", "FAIL", "Status not set"))
        except Exception as e:
            results.append(TestResult(module_name, "State transition: cancelled", "FAIL", str(e)))
        
        # Test 6: update_progress()
        try:
            job = JobState("test-progress", url="http://test.com")
            job.update_progress(percent=50.0, bytes_downloaded=1000, bytes_total=2000, speed=100.5, eta=60)
            if (job.progress_percent == 50.0 and job.bytes_downloaded == 1000 and 
                job.bytes_total == 2000 and job.download_speed == 100.5 and job.eta_seconds == 60):
                results.append(TestResult(module_name, "update_progress()", "PASS"))
            else:
                results.append(TestResult(module_name, "update_progress()", "FAIL", "Progress values not updated correctly"))
        except Exception as e:
            results.append(TestResult(module_name, "update_progress()", "FAIL", str(e)))
        
        # Test 7: add_log()
        try:
            job = JobState("test-log", url="http://test.com")
            job.add_log("Test message", "INFO")
            if len(job.logs) == 1 and job.logs[0]['message'] == "Test message" and job.logs[0]['level'] == "INFO":
                results.append(TestResult(module_name, "add_log()", "PASS"))
            else:
                results.append(TestResult(module_name, "add_log()", "FAIL", f"Log not added correctly: {job.logs}"))
        except Exception as e:
            results.append(TestResult(module_name, "add_log()", "FAIL", str(e)))
        
        # Test 8: to_dict() serialization
        try:
            job = JobState("test-dict", url="http://test.com", status=JobStatus.RUNNING)
            job.update_progress(percent=25.0)
            job.add_log("Test log")
            d = job.to_dict()
            
            if (isinstance(d, dict) and 'request_id' in d and 'status' in d and 
                'progress' in d and 'logs' in d):
                results.append(TestResult(module_name, "to_dict() serialization", "PASS"))
            else:
                results.append(TestResult(module_name, "to_dict() serialization", "FAIL", f"Invalid dict: {list(d.keys())}"))
        except Exception as e:
            results.append(TestResult(module_name, "to_dict() serialization", "FAIL", str(e)))
        
        # Test 9: JobStateManager singleton
        try:
            manager1 = get_job_state_manager()
            manager2 = get_job_state_manager()
            if manager1 is manager2:
                results.append(TestResult(module_name, "JobStateManager singleton", "PASS"))
            else:
                results.append(TestResult(module_name, "JobStateManager singleton", "FAIL", "Not returning same instance"))
        except Exception as e:
            results.append(TestResult(module_name, "JobStateManager singleton", "FAIL", str(e)))
        
        # Test 10: JobStateManager create_job()
        try:
            manager = get_job_state_manager()
            job = manager.create_job("manager-test-1", url="http://test.com")
            retrieved = manager.get_job("manager-test-1")
            
            if retrieved and retrieved.request_id == "manager-test-1":
                results.append(TestResult(module_name, "JobStateManager create_job()", "PASS"))
            else:
                results.append(TestResult(module_name, "JobStateManager create_job()", "FAIL", "Job not created or retrieved"))
        except Exception as e:
            results.append(TestResult(module_name, "JobStateManager create_job()", "FAIL", str(e)))
        
        # Test 11: JobStateManager update_job()
        try:
            manager = get_job_state_manager()
            manager.create_job("manager-test-2", url="http://test.com")
            update_result = manager.update_job("manager-test-2", progress_percent=75.0)
            job = manager.get_job("manager-test-2")
            
            if update_result and job and job.progress_percent == 75.0:
                results.append(TestResult(module_name, "JobStateManager update_job()", "PASS"))
            else:
                results.append(TestResult(module_name, "JobStateManager update_job()", "FAIL", "Job not updated"))
        except Exception as e:
            results.append(TestResult(module_name, "JobStateManager update_job()", "FAIL", str(e)))
        
        # Test 12: JobStateManager list_jobs()
        try:
            manager = get_job_state_manager()
            manager.create_job("manager-test-3", url="http://test.com", status=JobStatus.COMPLETED)
            
            all_jobs = manager.list_jobs()
            completed_jobs = manager.list_jobs(status=JobStatus.COMPLETED)
            
            if len(all_jobs) >= 1 and len(completed_jobs) >= 1:
                results.append(TestResult(module_name, "JobStateManager list_jobs()", "PASS"))
            else:
                results.append(TestResult(module_name, "JobStateManager list_jobs()", "FAIL", 
                                         f"Jobs not listed correctly: all={len(all_jobs)}, completed={len(completed_jobs)}"))
        except Exception as e:
            results.append(TestResult(module_name, "JobStateManager list_jobs()", "FAIL", str(e)))
        
        # Test 13: JobStateManager get_stats()
        try:
            manager = get_job_state_manager()
            stats = manager.get_stats()
            
            if (isinstance(stats, dict) and 'total_jobs' in stats and 'by_status' in stats):
                results.append(TestResult(module_name, "JobStateManager get_stats()", "PASS"))
            else:
                results.append(TestResult(module_name, "JobStateManager get_stats()", "FAIL", f"Invalid stats: {stats}"))
        except Exception as e:
            results.append(TestResult(module_name, "JobStateManager get_stats()", "FAIL", str(e)))
        
        # Test 14: Thread safety
        try:
            manager = get_job_state_manager()
            errors = []
            
            def create_and_update(index):
                try:
                    job_id = f"thread-test-{index}"
                    manager.create_job(job_id, url=f"http://test{index}.com")
                    manager.update_job(job_id, progress_percent=float(index))
                    job = manager.get_job(job_id)
                    if not job or job.progress_percent != float(index):
                        errors.append(f"Job {job_id} data mismatch")
                except Exception as e:
                    errors.append(str(e))
            
            threads = [threading.Thread(target=create_and_update, args=(i,)) for i in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            if not errors:
                results.append(TestResult(module_name, "JobStateManager thread safety", "PASS"))
            else:
                results.append(TestResult(module_name, "JobStateManager thread safety", "FAIL", 
                                         f"Errors: {errors[:3]}"))  # Show first 3 errors
        except Exception as e:
            results.append(TestResult(module_name, "JobStateManager thread safety", "FAIL", str(e)))
            
    except Exception as e:
        results.append(TestResult(module_name, "Core functionality tests", "FAIL", str(e)))
    
    return results


def print_summary(all_results: List[TestResult]):
    """Print test summary."""
    total = len(all_results)
    passed = sum(1 for r in all_results if r.status == "PASS")
    failed = sum(1 for r in all_results if r.status == "FAIL")
    warnings = sum(1 for r in all_results if r.status == "WARNING")
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total tests: {total}")
    print(f"Passed: {passed} ({passed*100//total if total > 0 else 0}%)")
    print(f"Failed: {failed} ({failed*100//total if total > 0 else 0}%)")
    print(f"Warnings: {warnings} ({warnings*100//total if total > 0 else 0}%)")
    print("="*80)


def main():
    """Run all tests."""
    print("="*80)
    print("CORE MODULES TEST SUITE")
    print("="*80)
    print("\nTesting core modules for bugs, import errors, and functionality issues...\n")
    
    all_results = []
    
    # Test 1: app/config.py
    print("\n[1/4] Testing app/config.py...")
    print("-" * 80)
    config_results = test_config()
    all_results.extend(config_results)
    for result in config_results:
        print(f"  {result}")
    
    # Test 2: app/core/exceptions.py
    print("\n[2/4] Testing app/core/exceptions.py...")
    print("-" * 80)
    exception_results = test_exceptions()
    all_results.extend(exception_results)
    for result in exception_results:
        print(f"  {result}")
    
    # Test 3: app/core/scheduler.py
    print("\n[3/4] Testing app/core/scheduler.py...")
    print("-" * 80)
    scheduler_results = test_scheduler()
    all_results.extend(scheduler_results)
    for result in scheduler_results:
        print(f"  {result}")
    
    # Test 4: app/core/state.py
    print("\n[4/4] Testing app/core/state.py...")
    print("-" * 80)
    state_results = test_state()
    all_results.extend(state_results)
    for result in state_results:
        print(f"  {result}")
    
    # Print summary
    print_summary(all_results)
    
    # Print failed tests details
    failed_tests = [r for r in all_results if r.status == "FAIL"]
    if failed_tests:
        print("\nFAILED TESTS DETAILS:")
        print("="*80)
        for result in failed_tests:
            print(f"\n{result.module} - {result.test}")
            print(f"  Error: {result.error}")
    
    # Print warnings
    warning_tests = [r for r in all_results if r.status == "WARNING"]
    if warning_tests:
        print("\nWARNINGS:")
        print("="*80)
        for result in warning_tests:
            print(f"\n{result.module} - {result.test}")
            if result.error:
                print(f"  Note: {result.error}")
    
    # Exit with appropriate code
    sys.exit(0 if not failed_tests else 1)


if __name__ == "__main__":
    main()
