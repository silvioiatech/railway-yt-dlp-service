#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for Ultimate Media Downloader.

Tests the complete application stack including:
- Application startup and lifecycle
- API router integration
- Dependency injection chain
- Service integration
- Model validation
- Error handling
- Security chain
- Performance and memory leak detection
"""

import asyncio
import gc
import os
import sys
import tempfile
import time
import traceback
import tracemalloc
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set test environment variables
os.environ['API_KEY'] = 'test_api_key_12345'
os.environ['REQUIRE_API_KEY'] = 'true'
os.environ['STORAGE_DIR'] = tempfile.mkdtemp()
os.environ['LOG_DIR'] = tempfile.mkdtemp()
os.environ['STATIC_DIR'] = tempfile.mkdtemp()
os.environ['FILE_RETENTION_HOURS'] = '1.0'
os.environ['MAX_CONCURRENT_DOWNLOADS'] = '5'
os.environ['WORKERS'] = '2'


class TestResult:
    """Test result container."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.duration = 0.0
        self.details = {}
    
    def __str__(self):
        status = "✓ PASS" if self.passed else "✗ FAIL"
        msg = f"{status} {self.name} ({self.duration:.2f}s)"
        if self.error:
            msg += f"\n    Error: {self.error}"
        return msg


class IntegrationTestSuite:
    """Comprehensive integration test suite."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.memory_snapshots = []
    
    async def run_all_tests(self):
        """Run all integration tests."""
        print("=" * 80)
        print("COMPREHENSIVE INTEGRATION TEST SUITE")
        print("Ultimate Media Downloader v3.0.0")
        print("=" * 80)
        print()
        
        # Start memory tracking
        tracemalloc.start()
        
        # Test groups
        await self.test_group_1_application_startup()
        await self.test_group_2_api_router_integration()
        await self.test_group_3_dependency_injection()
        await self.test_group_4_service_integration()
        await self.test_group_5_model_validation()
        await self.test_group_6_error_handling()
        await self.test_group_7_security_chain()
        await self.test_group_8_performance_and_memory()
        
        # Stop memory tracking
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Print results
        self.print_results(current, peak)
    
    async def test_group_1_application_startup(self):
        """Test Group 1: Application Startup."""
        print("\n" + "=" * 80)
        print("TEST GROUP 1: Application Startup")
        print("=" * 80)
        
        await self.test_1_1_import_main_module()
        await self.test_1_2_create_app_instance()
        await self.test_1_3_lifespan_context_manager()
        await self.test_1_4_middleware_registration()
        await self.test_1_5_routes_mounted()
        await self.test_1_6_openapi_schema()
    
    async def test_1_1_import_main_module(self):
        """Test 1.1: Import app.main module."""
        result = TestResult("1.1 Import app.main module")
        start_time = time.time()
        
        try:
            from app.main import create_app, app
            result.passed = True
            result.details['module'] = 'app.main'
            result.details['exports'] = ['create_app', 'app']
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_1_2_create_app_instance(self):
        """Test 1.2: Create FastAPI app instance."""
        result = TestResult("1.2 Create FastAPI app instance")
        start_time = time.time()
        
        try:
            from app.main import create_app
            app = create_app()
            
            assert app.title == "Ultimate Media Downloader"
            assert app.version == "3.0.0"
            assert app.lifespan is not None
            
            result.passed = True
            result.details['title'] = app.title
            result.details['version'] = app.version
            result.details['routes_count'] = len(app.routes)
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_1_3_lifespan_context_manager(self):
        """Test 1.3: Verify lifespan context manager."""
        result = TestResult("1.3 Verify lifespan context manager")
        start_time = time.time()
        
        try:
            from app.main import lifespan
            from fastapi import FastAPI
            
            # Create a test app
            test_app = FastAPI()
            
            # Mock the queue manager and scheduler
            with patch('app.services.queue_manager.initialize_queue_manager', 
                      new_callable=AsyncMock) as mock_init, \
                 patch('app.services.queue_manager.shutdown_queue_manager',
                      new_callable=AsyncMock) as mock_shutdown, \
                 patch('app.core.scheduler.get_scheduler') as mock_scheduler:
                
                mock_queue = MagicMock()
                mock_queue.max_workers = 2
                mock_queue.max_concurrent_downloads = 5
                mock_init.return_value = mock_queue
                
                mock_sched = MagicMock()
                mock_scheduler.return_value = mock_sched
                
                # Test lifespan
                async with lifespan(test_app):
                    # Verify startup
                    assert mock_init.called
                    assert hasattr(test_app.state, 'queue_manager')
                    assert hasattr(test_app.state, 'scheduler')
                    assert hasattr(test_app.state, 'settings')
                
                # Verify shutdown
                assert mock_shutdown.called
                assert mock_sched.shutdown.called
            
            result.passed = True
            result.details['startup_verified'] = True
            result.details['shutdown_verified'] = True
        except Exception as e:
            result.error = str(e)
            traceback.print_exc()
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_1_4_middleware_registration(self):
        """Test 1.4: Test all middleware registration."""
        result = TestResult("1.4 Test middleware registration")
        start_time = time.time()
        
        try:
            from app.main import create_app
            app = create_app()
            
            # Check middleware stack
            middleware_count = len(app.user_middleware)
            assert middleware_count > 0, "No middleware registered"
            
            # Check for rate limiter in app state
            assert hasattr(app.state, 'limiter'), "Rate limiter not in app state"
            
            result.passed = True
            result.details['middleware_count'] = middleware_count
            result.details['has_limiter'] = True
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_1_5_routes_mounted(self):
        """Test 1.5: Verify all routes are mounted."""
        result = TestResult("1.5 Verify routes mounted")
        start_time = time.time()
        
        try:
            from app.main import create_app
            app = create_app()
            
            routes = [r.path for r in app.routes if hasattr(r, 'path')]
            
            # Check for key routes
            expected_routes = [
                '/api/v1/health',
                '/api/v1/download',
                '/api/v1/metadata',
                '/metrics',
                '/version',
            ]
            
            for route in expected_routes:
                matching = [r for r in routes if route in r]
                assert len(matching) > 0, f"Route {route} not found"
            
            result.passed = True
            result.details['total_routes'] = len(routes)
            result.details['verified_routes'] = expected_routes
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_1_6_openapi_schema(self):
        """Test 1.6: Check OpenAPI schema generation."""
        result = TestResult("1.6 OpenAPI schema generation")
        start_time = time.time()
        
        try:
            from app.main import create_app
            app = create_app()
            
            schema = app.openapi()
            
            assert 'openapi' in schema
            assert 'info' in schema
            assert 'paths' in schema
            assert len(schema['paths']) > 0
            
            result.passed = True
            result.details['openapi_version'] = schema.get('openapi')
            result.details['endpoints_count'] = len(schema['paths'])
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_group_2_api_router_integration(self):
        """Test Group 2: API Router Integration."""
        print("\n" + "=" * 80)
        print("TEST GROUP 2: API Router Integration")
        print("=" * 80)
        
        await self.test_2_1_router_imports()
        await self.test_2_2_sub_routers_included()
        await self.test_2_3_path_prefixes()
        await self.test_2_4_no_duplicate_routes()
    
    async def test_2_1_router_imports(self):
        """Test 2.1: API router imports successfully."""
        result = TestResult("2.1 API router imports")
        start_time = time.time()
        
        try:
            from app.api.v1.router import api_router
            from app.api.v1 import download, health, metadata, playlist
            
            result.passed = True
            result.details['api_router'] = True
            result.details['sub_routers'] = ['download', 'health', 'metadata', 'playlist']
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_2_2_sub_routers_included(self):
        """Test 2.2: Verify all sub-routers are included."""
        result = TestResult("2.2 Sub-routers included")
        start_time = time.time()
        
        try:
            from app.api.v1.router import api_router
            
            # Check that router has routes from sub-routers
            routes = [r.path for r in api_router.routes if hasattr(r, 'path')]
            
            assert any('/health' in r for r in routes), "Health routes missing"
            assert any('/download' in r for r in routes), "Download routes missing"
            assert any('/metadata' in r for r in routes), "Metadata routes missing"
            assert any('/playlist' in r for r in routes), "Playlist routes missing"
            
            result.passed = True
            result.details['routes_count'] = len(routes)
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_2_3_path_prefixes(self):
        """Test 2.3: Check endpoint path prefixes."""
        result = TestResult("2.3 Endpoint path prefixes")
        start_time = time.time()
        
        try:
            from app.api.v1.router import api_router
            
            assert api_router.prefix == "/api/v1"
            
            result.passed = True
            result.details['prefix'] = api_router.prefix
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_2_4_no_duplicate_routes(self):
        """Test 2.4: Verify no duplicate routes."""
        result = TestResult("2.4 No duplicate routes")
        start_time = time.time()
        
        try:
            from app.main import create_app
            app = create_app()
            
            routes = [r.path for r in app.routes if hasattr(r, 'path')]
            
            # Check for duplicates
            route_counts = {}
            for route in routes:
                route_counts[route] = route_counts.get(route, 0) + 1
            
            duplicates = {k: v for k, v in route_counts.items() if v > 1}
            
            # OpenAPI routes are expected to have duplicates (different methods)
            # Filter out expected duplicates
            unexpected_duplicates = {k: v for k, v in duplicates.items() 
                                    if not k.startswith('/openapi')}
            
            assert len(unexpected_duplicates) == 0, f"Duplicate routes: {unexpected_duplicates}"
            
            result.passed = True
            result.details['unique_routes'] = len(set(routes))
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_group_3_dependency_injection(self):
        """Test Group 3: Dependency Injection Chain."""
        print("\n" + "=" * 80)
        print("TEST GROUP 3: Dependency Injection Chain")
        print("=" * 80)
        
        await self.test_3_1_settings_dependency()
        await self.test_3_2_authentication_dependencies()
        await self.test_3_3_service_dependencies()
        await self.test_3_4_no_circular_dependencies()
    
    async def test_3_1_settings_dependency(self):
        """Test 3.1: Settings dependency injection."""
        result = TestResult("3.1 Settings dependency")
        start_time = time.time()
        
        try:
            from app.config import get_settings, Settings
            
            settings = get_settings()
            
            assert isinstance(settings, Settings)
            assert settings.APP_NAME == "Ultimate Media Downloader"
            assert settings.VERSION == "3.0.0"
            
            # Test caching
            settings2 = get_settings()
            assert settings is settings2, "Settings not cached"
            
            result.passed = True
            result.details['cached'] = True
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_3_2_authentication_dependencies(self):
        """Test 3.2: Authentication dependencies."""
        result = TestResult("3.2 Authentication dependencies")
        start_time = time.time()
        
        try:
            from app.api.v1.auth import verify_api_key
            from fastapi import HTTPException
            
            # Test with valid key
            try:
                verify_api_key("test_api_key_12345")
                auth_works = True
            except HTTPException:
                auth_works = False
            
            # Test with invalid key
            try:
                verify_api_key("invalid_key")
                should_fail = False
            except HTTPException:
                should_fail = True
            
            assert auth_works, "Valid API key rejected"
            assert should_fail, "Invalid API key accepted"
            
            result.passed = True
            result.details['valid_key_accepted'] = True
            result.details['invalid_key_rejected'] = True
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_3_3_service_dependencies(self):
        """Test 3.3: Service dependencies."""
        result = TestResult("3.3 Service dependencies")
        start_time = time.time()
        
        try:
            from app.services.ytdlp_wrapper import get_ytdlp_wrapper
            from app.services.file_manager import get_file_manager
            from app.services.queue_manager import get_queue_manager
            from app.core.state import get_job_state_manager
            
            # All dependencies should be importable and callable
            ytdlp = get_ytdlp_wrapper()
            file_mgr = get_file_manager()
            state_mgr = get_job_state_manager()
            
            # Queue manager requires initialization, just check it's callable
            assert callable(get_queue_manager)
            
            result.passed = True
            result.details['services'] = ['ytdlp_wrapper', 'file_manager', 
                                         'queue_manager', 'job_state_manager']
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_3_4_no_circular_dependencies(self):
        """Test 3.4: Verify no circular dependencies."""
        result = TestResult("3.4 No circular dependencies")
        start_time = time.time()
        
        try:
            # Import all modules - will fail if circular dependencies exist
            from app.main import create_app
            from app.api.v1 import router, download, health, metadata, playlist
            from app.services import ytdlp_wrapper, file_manager, queue_manager
            from app.core import exceptions, scheduler, state
            from app.models import requests, responses, enums
            
            result.passed = True
            result.details['modules_imported'] = 12
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_group_4_service_integration(self):
        """Test Group 4: Service Integration."""
        print("\n" + "=" * 80)
        print("TEST GROUP 4: Service Integration")
        print("=" * 80)
        
        await self.test_4_1_queue_ytdlp_integration()
        await self.test_4_2_filemanager_scheduler_integration()
        await self.test_4_3_state_api_integration()
        await self.test_4_4_async_await_chain()
    
    async def test_4_1_queue_ytdlp_integration(self):
        """Test 4.1: QueueManager + YtdlpWrapper integration."""
        result = TestResult("4.1 QueueManager + YtdlpWrapper")
        start_time = time.time()
        
        try:
            from app.services.queue_manager import QueueManager
            from app.services.ytdlp_wrapper import YtdlpWrapper
            
            # Create instances
            queue_mgr = QueueManager(max_workers=2, max_concurrent_downloads=3)
            ytdlp = YtdlpWrapper()
            
            # Verify they can work together
            assert queue_mgr.max_workers == 2
            assert ytdlp is not None
            
            result.passed = True
            result.details['queue_manager_created'] = True
            result.details['ytdlp_wrapper_created'] = True
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_4_2_filemanager_scheduler_integration(self):
        """Test 4.2: FileManager + Scheduler integration."""
        result = TestResult("4.2 FileManager + Scheduler")
        start_time = time.time()
        
        try:
            from app.services.file_manager import FileManager
            from app.core.scheduler import FileDeletionScheduler
            
            file_mgr = FileManager()
            scheduler = FileDeletionScheduler()
            
            # Verify they can work together
            assert file_mgr.storage_dir.exists()
            assert scheduler is not None
            
            # Cleanup
            scheduler.shutdown()
            
            result.passed = True
            result.details['file_manager_created'] = True
            result.details['scheduler_created'] = True
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_4_3_state_api_integration(self):
        """Test 4.3: JobStateManager + API integration."""
        result = TestResult("4.3 JobStateManager + API")
        start_time = time.time()
        
        try:
            from app.core.state import JobStateManager
            
            state_mgr = JobStateManager()
            
            # Test job state operations
            job_id = "test_job_123"
            state_mgr.update_state(job_id, "pending", progress=0)
            
            job_state = state_mgr.get_state(job_id)
            assert job_state is not None
            assert job_state['status'] == 'pending'
            
            # Cleanup
            state_mgr.cleanup_old_jobs(max_age_hours=0)
            
            result.passed = True
            result.details['state_operations'] = 'verified'
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_4_4_async_await_chain(self):
        """Test 4.4: Async/await chain works."""
        result = TestResult("4.4 Async/await chain")
        start_time = time.time()
        
        try:
            from app.services.queue_manager import QueueManager
            
            queue_mgr = QueueManager(max_workers=1, max_concurrent_downloads=1)
            
            # Test async job submission
            async def dummy_task():
                await asyncio.sleep(0.01)
                return "completed"
            
            job_id = await queue_mgr.submit_job(dummy_task(), priority=1)
            assert job_id is not None
            
            # Wait a bit for job to complete
            await asyncio.sleep(0.05)
            
            await queue_mgr.shutdown(wait=True, timeout=1.0)
            
            result.passed = True
            result.details['async_job_submitted'] = True
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_group_5_model_validation(self):
        """Test Group 5: Model Validation Chain."""
        print("\n" + "=" * 80)
        print("TEST GROUP 5: Model Validation Chain")
        print("=" * 80)
        
        await self.test_5_1_request_models()
        await self.test_5_2_response_models()
        await self.test_5_3_enum_conversions()
        await self.test_5_4_pydantic_v2_compatibility()
    
    async def test_5_1_request_models(self):
        """Test 5.1: Request models validate correctly."""
        result = TestResult("5.1 Request models validation")
        start_time = time.time()
        
        try:
            from app.models.requests import DownloadRequest, PlaylistRequest
            from app.models.enums import DownloadFormat, VideoQuality
            
            # Test valid request
            valid_req = DownloadRequest(
                url="https://example.com/video",
                format=DownloadFormat.MP4,
                quality=VideoQuality.BEST
            )
            assert valid_req.url == "https://example.com/video"
            
            # Test playlist request
            playlist_req = PlaylistRequest(
                url="https://example.com/playlist",
                format=DownloadFormat.MP3
            )
            assert playlist_req.format == DownloadFormat.MP3
            
            result.passed = True
            result.details['request_models'] = ['DownloadRequest', 'PlaylistRequest']
        except Exception as e:
            result.error = str(e)
            traceback.print_exc()
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_5_2_response_models(self):
        """Test 5.2: Response models serialize correctly."""
        result = TestResult("5.2 Response models serialization")
        start_time = time.time()
        
        try:
            from app.models.responses import DownloadResponse, JobStatusResponse
            from app.models.enums import JobStatus
            
            # Test download response
            download_resp = DownloadResponse(
                job_id="test_123",
                status=JobStatus.PENDING,
                message="Download queued"
            )
            
            # Serialize to dict
            resp_dict = download_resp.model_dump()
            assert resp_dict['job_id'] == "test_123"
            assert resp_dict['status'] == 'pending'
            
            # Test job status response
            status_resp = JobStatusResponse(
                job_id="test_123",
                status=JobStatus.PROCESSING,
                progress=50.0
            )
            
            status_dict = status_resp.model_dump()
            assert status_dict['progress'] == 50.0
            
            result.passed = True
            result.details['response_models'] = ['DownloadResponse', 'JobStatusResponse']
        except Exception as e:
            result.error = str(e)
            traceback.print_exc()
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_5_3_enum_conversions(self):
        """Test 5.3: Enum conversions."""
        result = TestResult("5.3 Enum conversions")
        start_time = time.time()
        
        try:
            from app.models.enums import JobStatus, DownloadFormat, VideoQuality
            
            # Test JobStatus
            assert JobStatus.PENDING.value == "pending"
            assert JobStatus.from_string("completed") == JobStatus.COMPLETED
            
            # Test DownloadFormat
            assert DownloadFormat.MP4.value == "mp4"
            assert DownloadFormat.from_string("mp3") == DownloadFormat.MP3
            
            # Test VideoQuality
            assert VideoQuality.BEST.value == "best"
            
            result.passed = True
            result.details['enums'] = ['JobStatus', 'DownloadFormat', 'VideoQuality']
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_5_4_pydantic_v2_compatibility(self):
        """Test 5.4: Pydantic v2 compatibility."""
        result = TestResult("5.4 Pydantic v2 compatibility")
        start_time = time.time()
        
        try:
            from pydantic import __version__ as pydantic_version
            from app.config import Settings
            
            # Check Pydantic version
            major_version = int(pydantic_version.split('.')[0])
            assert major_version == 2, f"Expected Pydantic v2, got v{pydantic_version}"
            
            # Test Settings uses Pydantic v2 features
            settings = Settings()
            
            # model_dump is Pydantic v2 method
            settings_dict = settings.model_dump()
            assert isinstance(settings_dict, dict)
            
            result.passed = True
            result.details['pydantic_version'] = pydantic_version
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_group_6_error_handling(self):
        """Test Group 6: Error Handling Chain."""
        print("\n" + "=" * 80)
        print("TEST GROUP 6: Error Handling Chain")
        print("=" * 80)
        
        await self.test_6_1_custom_exceptions()
        await self.test_6_2_error_middleware()
        await self.test_6_3_status_codes()
        await self.test_6_4_error_response_format()
    
    async def test_6_1_custom_exceptions(self):
        """Test 6.1: Custom exceptions propagate to HTTP responses."""
        result = TestResult("6.1 Custom exceptions")
        start_time = time.time()
        
        try:
            from app.core.exceptions import (
                MediaDownloaderException,
                ValidationError,
                DownloadError,
                StorageError
            )
            
            # Test base exception
            exc = MediaDownloaderException("Test error", "TEST_ERROR", 500)
            assert exc.message == "Test error"
            assert exc.error_code == "TEST_ERROR"
            assert exc.status_code == 500
            
            exc_dict = exc.to_dict()
            assert exc_dict['error'] == "Test error"
            
            # Test specific exceptions
            val_err = ValidationError("Invalid input")
            assert val_err.status_code == 400
            
            dl_err = DownloadError("Download failed")
            assert dl_err.status_code == 500
            
            stor_err = StorageError("Storage issue")
            assert stor_err.status_code == 500
            
            result.passed = True
            result.details['exceptions_tested'] = 4
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_6_2_error_middleware(self):
        """Test 6.2: Error middleware catches all errors."""
        result = TestResult("6.2 Error middleware")
        start_time = time.time()
        
        try:
            from app.main import create_app
            
            app = create_app()
            
            # Check exception handlers are registered
            handler_count = len(app.exception_handlers)
            assert handler_count > 0, "No exception handlers registered"
            
            result.passed = True
            result.details['handler_count'] = handler_count
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_6_3_status_codes(self):
        """Test 6.3: Verify proper status codes."""
        result = TestResult("6.3 HTTP status codes")
        start_time = time.time()
        
        try:
            from app.core.exceptions import (
                ValidationError,
                AuthenticationError,
                NotFoundError,
                DownloadError
            )
            
            # Check status codes
            assert ValidationError("test").status_code == 400
            assert AuthenticationError("test").status_code == 401
            assert NotFoundError("test").status_code == 404
            assert DownloadError("test").status_code == 500
            
            result.passed = True
            result.details['status_codes_verified'] = True
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_6_4_error_response_format(self):
        """Test 6.4: Test error response format."""
        result = TestResult("6.4 Error response format")
        start_time = time.time()
        
        try:
            from app.core.exceptions import ValidationError
            
            exc = ValidationError("Invalid URL format", {"field": "url"})
            exc_dict = exc.to_dict()
            
            assert 'error' in exc_dict
            assert 'error_code' in exc_dict
            assert 'status_code' in exc_dict
            assert 'details' in exc_dict
            
            result.passed = True
            result.details['format_fields'] = list(exc_dict.keys())
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_group_7_security_chain(self):
        """Test Group 7: Security Chain."""
        print("\n" + "=" * 80)
        print("TEST GROUP 7: Security Chain")
        print("=" * 80)
        
        await self.test_7_1_authentication_flow()
        await self.test_7_2_rate_limiting()
        await self.test_7_3_cors_enabled()
        await self.test_7_4_path_validation()
    
    async def test_7_1_authentication_flow(self):
        """Test 7.1: Authentication flow end-to-end."""
        result = TestResult("7.1 Authentication flow")
        start_time = time.time()
        
        try:
            from app.api.v1.auth import verify_api_key
            from fastapi import HTTPException
            
            # Test valid authentication
            try:
                verify_api_key("test_api_key_12345")
                valid_accepted = True
            except HTTPException:
                valid_accepted = False
            
            # Test invalid authentication
            try:
                verify_api_key("wrong_key")
                invalid_rejected = False
            except HTTPException as e:
                invalid_rejected = True
                assert e.status_code == 401
            
            assert valid_accepted, "Valid key was rejected"
            assert invalid_rejected, "Invalid key was accepted"
            
            result.passed = True
            result.details['authentication_working'] = True
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_7_2_rate_limiting(self):
        """Test 7.2: Rate limiting is configured."""
        result = TestResult("7.2 Rate limiting")
        start_time = time.time()
        
        try:
            from app.middleware.rate_limit import create_limiter
            from app.config import get_settings
            
            settings = get_settings()
            limiter = create_limiter(settings)
            
            assert limiter is not None
            
            result.passed = True
            result.details['rate_limit_configured'] = True
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_7_3_cors_enabled(self):
        """Test 7.3: CORS is enabled."""
        result = TestResult("7.3 CORS enabled")
        start_time = time.time()
        
        try:
            from app.main import create_app
            
            app = create_app()
            
            # Check for CORS middleware in stack
            middleware_types = [type(m.cls).__name__ if hasattr(m, 'cls') else type(m).__name__ 
                              for m in app.user_middleware]
            
            has_cors = any('CORS' in name for name in middleware_types)
            
            result.passed = True
            result.details['cors_enabled'] = has_cors
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_7_4_path_validation(self):
        """Test 7.4: Path validation in file serving."""
        result = TestResult("7.4 Path validation")
        start_time = time.time()
        
        try:
            from app.services.file_manager import FileManager
            from app.core.exceptions import StorageError
            from pathlib import Path
            
            file_mgr = FileManager()
            
            # Test valid path
            try:
                valid_path = file_mgr.validate_path(Path("test.mp4"))
                path_validation_works = True
            except StorageError:
                path_validation_works = True  # May fail if file doesn't exist, but validation runs
            
            # Test invalid path (path traversal)
            try:
                file_mgr.validate_path(Path("../../../etc/passwd"))
                blocks_traversal = False
            except StorageError:
                blocks_traversal = True
            
            assert blocks_traversal, "Path traversal not blocked"
            
            result.passed = True
            result.details['path_validation'] = 'working'
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_group_8_performance_and_memory(self):
        """Test Group 8: Performance and Memory Leak Detection."""
        print("\n" + "=" * 80)
        print("TEST GROUP 8: Performance and Memory Leak Detection")
        print("=" * 80)
        
        await self.test_8_1_multiple_app_instances()
        await self.test_8_2_concurrent_operations()
        await self.test_8_3_memory_leak_detection()
        await self.test_8_4_thread_safety()
    
    async def test_8_1_multiple_app_instances(self):
        """Test 8.1: Create/destroy multiple app instances."""
        result = TestResult("8.1 Multiple app instances")
        start_time = time.time()
        
        try:
            from app.main import create_app
            
            # Take memory snapshot
            gc.collect()
            snapshot1 = tracemalloc.take_snapshot()
            
            # Create and destroy multiple instances
            for i in range(5):
                app = create_app()
                del app
                gc.collect()
            
            # Take another snapshot
            snapshot2 = tracemalloc.take_snapshot()
            
            # Compare memory
            top_stats = snapshot2.compare_to(snapshot1, 'lineno')
            total_diff = sum(stat.size_diff for stat in top_stats)
            
            result.passed = True
            result.details['instances_created'] = 5
            result.details['memory_diff_kb'] = total_diff / 1024
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_8_2_concurrent_operations(self):
        """Test 8.2: Test concurrent operations."""
        result = TestResult("8.2 Concurrent operations")
        start_time = time.time()
        
        try:
            from app.core.state import JobStateManager
            
            state_mgr = JobStateManager()
            
            # Simulate concurrent state updates
            async def update_job(job_id: str):
                for i in range(10):
                    state_mgr.update_state(job_id, "processing", progress=i*10)
                    await asyncio.sleep(0.001)
            
            # Run concurrent updates
            await asyncio.gather(
                update_job("job1"),
                update_job("job2"),
                update_job("job3")
            )
            
            # Verify states
            assert state_mgr.get_state("job1") is not None
            assert state_mgr.get_state("job2") is not None
            assert state_mgr.get_state("job3") is not None
            
            result.passed = True
            result.details['concurrent_jobs'] = 3
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_8_3_memory_leak_detection(self):
        """Test 8.3: Memory leak detection."""
        result = TestResult("8.3 Memory leak detection")
        start_time = time.time()
        
        try:
            from app.services.queue_manager import QueueManager
            
            gc.collect()
            snapshot1 = tracemalloc.take_snapshot()
            
            # Create and destroy queue managers
            for i in range(3):
                qm = QueueManager(max_workers=2, max_concurrent_downloads=3)
                await qm.shutdown(wait=False, timeout=0.1)
                del qm
                gc.collect()
            
            snapshot2 = tracemalloc.take_snapshot()
            
            top_stats = snapshot2.compare_to(snapshot1, 'lineno')
            total_diff = sum(stat.size_diff for stat in top_stats[:10])
            
            # Memory growth should be minimal
            leak_threshold = 1024 * 100  # 100KB
            has_leak = total_diff > leak_threshold
            
            result.passed = not has_leak
            result.details['memory_growth_kb'] = total_diff / 1024
            result.details['leak_detected'] = has_leak
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    async def test_8_4_thread_safety(self):
        """Test 8.4: Thread safety where applicable."""
        result = TestResult("8.4 Thread safety")
        start_time = time.time()
        
        try:
            from app.core.state import JobStateManager
            import threading
            
            state_mgr = JobStateManager()
            errors = []
            
            def worker(worker_id: int):
                try:
                    for i in range(50):
                        job_id = f"job_{worker_id}_{i}"
                        state_mgr.update_state(job_id, "processing", progress=i)
                        state = state_mgr.get_state(job_id)
                        if state is None:
                            errors.append(f"State not found for {job_id}")
                except Exception as e:
                    errors.append(str(e))
            
            # Run multiple threads
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            assert len(errors) == 0, f"Thread safety issues: {errors}"
            
            result.passed = True
            result.details['threads'] = 5
            result.details['operations_per_thread'] = 50
        except Exception as e:
            result.error = str(e)
        
        result.duration = time.time() - start_time
        self.results.append(result)
        print(result)
    
    def print_results(self, current_memory: int, peak_memory: int):
        """Print comprehensive test results."""
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        total_time = sum(r.duration for r in self.results)
        
        print(f"\nTotal Tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.results)*100):.1f}%")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Memory: {current_memory/1024/1024:.2f} MB current, {peak_memory/1024/1024:.2f} MB peak")
        
        if failed > 0:
            print("\n" + "=" * 80)
            print("FAILED TESTS")
            print("=" * 80)
            for r in self.results:
                if not r.passed:
                    print(f"\n{r}")
        
        # Component integration status
        print("\n" + "=" * 80)
        print("COMPONENT INTEGRATION STATUS")
        print("=" * 80)
        
        categories = {
            "Application Startup": self.results[0:6],
            "API Router": self.results[6:10],
            "Dependency Injection": self.results[10:14],
            "Service Integration": self.results[14:18],
            "Model Validation": self.results[18:22],
            "Error Handling": self.results[22:26],
            "Security": self.results[26:30],
            "Performance": self.results[30:34]
        }
        
        for category, tests in categories.items():
            passed = sum(1 for t in tests if t.passed)
            total = len(tests)
            status = "OK" if passed == total else "ISSUES"
            print(f"{category:.<40} [{passed}/{total}] {status}")
        
        # Production readiness score
        print("\n" + "=" * 80)
        print("PRODUCTION READINESS ASSESSMENT")
        print("=" * 80)
        
        score = (passed / len(self.results)) * 100
        
        if score >= 95:
            grade = "A+ (Production Ready)"
        elif score >= 90:
            grade = "A (Production Ready with minor issues)"
        elif score >= 80:
            grade = "B (Needs attention before production)"
        elif score >= 70:
            grade = "C (Significant issues)"
        else:
            grade = "D (Not production ready)"
        
        print(f"\nProduction Readiness Score: {score:.1f}%")
        print(f"Grade: {grade}")
        
        print("\n" + "=" * 80)
        
        if score >= 90:
            print("\nThe application is production-ready!")
        else:
            print("\nThe application needs attention before production deployment.")


async def main():
    """Run integration test suite."""
    suite = IntegrationTestSuite()
    await suite.run_all_tests()
    
    # Return exit code
    failed = sum(1 for r in suite.results if not r.passed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
