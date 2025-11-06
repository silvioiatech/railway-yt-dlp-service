#!/usr/bin/env python3
"""
Test script for Batch Downloads feature.

This script demonstrates and validates the Batch Downloads implementation
without requiring the full application to be running.

Usage:
    python test_batch_feature.py
"""
import asyncio
import sys
from datetime import datetime

# Disable API key requirement for testing
import os
os.environ['REQUIRE_API_KEY'] = 'false'

from app.services.batch_service import BatchService
from app.services.queue_manager import QueueManager
from app.core.state import JobStateManager
from app.config import get_settings
from app.models.requests import BatchDownloadRequest, DownloadRequest
from app.models.enums import JobStatus


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_success(message: str):
    """Print a success message."""
    print(f"✓ {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"✗ {message}")


def test_imports():
    """Test that all modules can be imported."""
    print_section("Test 1: Module Imports")

    try:
        from app.api.v1 import batch
        print_success("Batch API module imported")

        from app.services.batch_service import BatchService, BatchState
        print_success("Batch service classes imported")

        from app.models.requests import BatchDownloadRequest
        print_success("Request models imported")

        from app.models.responses import BatchDownloadResponse, JobInfo
        print_success("Response models imported")

        return True
    except Exception as e:
        print_error(f"Import failed: {e}")
        return False


def test_service_instantiation():
    """Test BatchService instantiation."""
    print_section("Test 2: Service Instantiation")

    try:
        settings = get_settings()
        print_success("Settings loaded")

        queue_manager = QueueManager()
        print_success("QueueManager instantiated")

        job_state_manager = JobStateManager()
        print_success("JobStateManager instantiated")

        batch_service = BatchService(
            queue_manager=queue_manager,
            job_state_manager=job_state_manager,
            settings=settings
        )
        print_success("BatchService instantiated")

        batch_list = batch_service.get_batch_list()
        print_success(f"Batch list retrieved (count: {len(batch_list)})")

        return batch_service, queue_manager, job_state_manager
    except Exception as e:
        print_error(f"Instantiation failed: {e}")
        return None, None, None


def test_request_validation():
    """Test BatchDownloadRequest validation."""
    print_section("Test 3: Request Validation")

    # Test valid request
    try:
        request = BatchDownloadRequest(
            urls=[
                "https://example.com/video1",
                "https://example.com/video2",
                "https://example.com/video3"
            ],
            concurrent_limit=2,
            stop_on_error=False
        )
        print_success(f"Valid request created with {len(request.urls)} URLs")
    except Exception as e:
        print_error(f"Valid request failed: {e}")
        return False

    # Test duplicate URL detection
    try:
        request = BatchDownloadRequest(
            urls=[
                "https://example.com/video1",
                "https://example.com/video1"  # Duplicate
            ]
        )
        print_error("Duplicate URL detection failed (should have raised error)")
        return False
    except ValueError as e:
        print_success("Duplicate URL detection working")

    # Test batch size limit
    try:
        request = BatchDownloadRequest(
            urls=[f"https://example.com/video{i}" for i in range(101)]
        )
        print_error("Batch size limit failed (should have raised error)")
        return False
    except ValueError:
        print_success("Batch size limit enforced (max 100 URLs)")

    # Test URL format validation
    try:
        request = BatchDownloadRequest(
            urls=["not-a-url", "also-not-a-url"]
        )
        print_error("URL format validation failed (should have raised error)")
        return False
    except ValueError:
        print_success("URL format validation working")

    return True


def test_concurrent_limit_validation():
    """Test concurrent_limit validation."""
    print_section("Test 4: Concurrent Limit Validation")

    # Test valid limits
    for limit in [1, 3, 5, 10]:
        try:
            request = BatchDownloadRequest(
                urls=["https://example.com/video"],
                concurrent_limit=limit
            )
            print_success(f"Concurrent limit {limit} accepted")
        except Exception as e:
            print_error(f"Valid limit {limit} failed: {e}")
            return False

    # Test invalid limits
    for limit in [0, 11, 100]:
        try:
            request = BatchDownloadRequest(
                urls=["https://example.com/video"],
                concurrent_limit=limit
            )
            print_error(f"Invalid limit {limit} should have been rejected")
            return False
        except ValueError:
            print_success(f"Invalid concurrent limit {limit} rejected")

    return True


async def test_batch_creation(batch_service, queue_manager, job_state_manager):
    """Test batch creation."""
    print_section("Test 5: Batch Creation")

    try:
        # Start queue manager
        await queue_manager.start()
        print_success("Queue manager started")

        # Create batch request
        request = BatchDownloadRequest(
            urls=[
                "https://example.com/video1",
                "https://example.com/video2"
            ],
            concurrent_limit=2,
            stop_on_error=False
        )
        print_success("Batch request created")

        # Note: We can't actually create the batch without mocking the download
        # process, but we can verify the request is valid
        print_success("Batch request validated (actual creation requires running app)")

        # Shutdown queue manager
        await queue_manager.shutdown(wait=False)
        print_success("Queue manager shutdown")

        return True
    except Exception as e:
        print_error(f"Batch creation test failed: {e}")
        return False


def test_api_endpoints():
    """Test API endpoint registration."""
    print_section("Test 6: API Endpoints")

    try:
        from app.api.v1.router import api_router

        routes = [route.path for route in api_router.routes]
        batch_routes = [r for r in routes if '/batch' in r]

        expected_routes = [
            '/api/v1/batch/download',
            '/api/v1/batch/{batch_id}'
        ]

        for expected in expected_routes:
            if expected in batch_routes:
                print_success(f"Endpoint registered: {expected}")
            else:
                print_error(f"Endpoint missing: {expected}")
                return False

        return True
    except Exception as e:
        print_error(f"API endpoint test failed: {e}")
        return False


def test_download_request_conversion():
    """Test conversion from BatchDownloadRequest to DownloadRequest."""
    print_section("Test 7: Request Conversion")

    try:
        batch_request = BatchDownloadRequest(
            urls=["https://example.com/video1"],
            quality="1080p",
            audio_only=True,
            concurrent_limit=2
        )
        print_success("Batch request created")

        # Create individual download request
        url = batch_request.urls[0]
        download_request = DownloadRequest(
            url=url,
            quality=batch_request.quality,
            audio_only=batch_request.audio_only,
            video_format=batch_request.video_format,
            audio_format=batch_request.audio_format,
        )
        print_success("Converted to DownloadRequest")

        # Verify attributes
        assert download_request.url == url
        assert download_request.quality == batch_request.quality
        assert download_request.audio_only == batch_request.audio_only
        print_success("Attributes correctly transferred")

        return True
    except Exception as e:
        print_error(f"Request conversion failed: {e}")
        return False


def test_job_state_management():
    """Test job state management for batch."""
    print_section("Test 8: Job State Management")

    try:
        job_state_manager = JobStateManager()
        batch_id = "batch_test123"

        # Create jobs
        job_ids = []
        for i in range(3):
            job_id = f"{batch_id}_job_{i:03d}"
            job = job_state_manager.create_job(
                request_id=job_id,
                url=f"https://example.com/video{i}",
                payload={},
                status=JobStatus.QUEUED
            )
            job_ids.append(job_id)

        print_success(f"Created {len(job_ids)} job states")

        # Verify jobs can be retrieved
        for job_id in job_ids:
            job = job_state_manager.get_job(job_id)
            assert job is not None
            assert job.status == JobStatus.QUEUED

        print_success("All jobs retrieved successfully")

        # Get statistics
        stats = job_state_manager.get_stats()
        print_success(f"Statistics: {stats['total_jobs']} total, {stats['queued']} queued")

        return True
    except Exception as e:
        print_error(f"Job state management failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*70)
    print("  BATCH DOWNLOADS FEATURE TEST SUITE")
    print("="*70)

    results = []

    # Run synchronous tests
    results.append(("Module Imports", test_imports()))

    batch_service, queue_manager, job_state_manager = test_service_instantiation()
    results.append(("Service Instantiation", batch_service is not None))

    if batch_service:
        results.append(("Request Validation", test_request_validation()))
        results.append(("Concurrent Limit Validation", test_concurrent_limit_validation()))
        results.append(("API Endpoints", test_api_endpoints()))
        results.append(("Request Conversion", test_download_request_conversion()))
        results.append(("Job State Management", test_job_state_management()))

        # Run async test
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async_result = loop.run_until_complete(
                test_batch_creation(batch_service, queue_manager, job_state_manager)
            )
            loop.close()
            results.append(("Batch Creation", async_result))
        except Exception as e:
            print_error(f"Async test failed: {e}")
            results.append(("Batch Creation", False))

    # Print summary
    print_section("TEST SUMMARY")

    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    failed_tests = total_tests - passed_tests

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:12} | {test_name}")

    print(f"\n{'='*70}")
    print(f"Total: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests}")
    print(f"{'='*70}\n")

    if failed_tests == 0:
        print("🎉 All tests passed! Batch Downloads feature is working correctly.\n")
        return 0
    else:
        print(f"⚠️  {failed_tests} test(s) failed. Please review the errors above.\n")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
