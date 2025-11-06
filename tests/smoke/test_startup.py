#!/usr/bin/env python3
"""
Test script to verify the FastAPI application can be instantiated.

This script checks that all imports work and the app can be created
without runtime errors. It does NOT start the server.

Usage:
    python test_startup.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        from app.config import get_settings, validate_settings
        print("  [OK] app.config")
    except ImportError as e:
        print(f"  [FAIL] app.config: {e}")
        return False

    try:
        from app.core.exceptions import MediaDownloaderException
        print("  [OK] app.core.exceptions")
    except ImportError as e:
        print(f"  [FAIL] app.core.exceptions: {e}")
        return False

    try:
        from app.core.scheduler import FileDeletionScheduler, get_scheduler
        print("  [OK] app.core.scheduler")
    except ImportError as e:
        print(f"  [FAIL] app.core.scheduler: {e}")
        return False

    try:
        from app.services.queue_manager import QueueManager, get_queue_manager
        print("  [OK] app.services.queue_manager")
    except ImportError as e:
        print(f"  [FAIL] app.services.queue_manager: {e}")
        return False

    try:
        from app.middleware.rate_limit import create_limiter
        print("  [OK] app.middleware.rate_limit")
    except ImportError as e:
        print(f"  [FAIL] app.middleware.rate_limit: {e}")
        return False

    try:
        from app.api.v1.router import api_router
        print("  [OK] app.api.v1.router")
    except ImportError as e:
        print(f"  [FAIL] app.api.v1.router: {e}")
        return False

    return True


def test_config():
    """Test that configuration can be loaded."""
    print("\nTesting configuration...")

    try:
        from app.config import get_settings
        settings = get_settings()
        print(f"  [OK] Settings loaded")
        print(f"       - APP_NAME: {settings.APP_NAME}")
        print(f"       - VERSION: {settings.VERSION}")
        print(f"       - STORAGE_DIR: {settings.STORAGE_DIR}")
        print(f"       - WORKERS: {settings.WORKERS}")
        print(f"       - REQUIRE_API_KEY: {settings.REQUIRE_API_KEY}")
        return True
    except Exception as e:
        print(f"  [FAIL] Configuration error: {e}")
        return False


def test_app_creation():
    """Test that the FastAPI app can be created."""
    print("\nTesting FastAPI app creation...")

    try:
        from app.main import create_app
        app = create_app()
        print(f"  [OK] App created successfully")
        print(f"       - Title: {app.title}")
        print(f"       - Version: {app.version}")
        print(f"       - Routes: {len(app.routes)}")

        # List some key routes
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        print(f"       - Key routes:")
        for route in sorted(routes)[:10]:
            print(f"         * {route}")

        return True
    except Exception as e:
        print(f"  [FAIL] App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_middleware():
    """Test that middleware is properly configured."""
    print("\nTesting middleware configuration...")

    try:
        from app.main import create_app
        app = create_app()

        # Check for rate limiter
        if hasattr(app.state, 'limiter'):
            print(f"  [OK] Rate limiter configured")
        else:
            print(f"  [WARN] Rate limiter not found in app state")

        # Check middleware stack
        middleware_count = len(app.user_middleware)
        print(f"  [OK] Middleware stack configured ({middleware_count} middleware)")

        return True
    except Exception as e:
        print(f"  [FAIL] Middleware test failed: {e}")
        return False


def test_exception_handlers():
    """Test that exception handlers are registered."""
    print("\nTesting exception handlers...")

    try:
        from app.main import create_app
        app = create_app()

        handler_count = len(app.exception_handlers)
        print(f"  [OK] Exception handlers registered ({handler_count} handlers)")

        return True
    except Exception as e:
        print(f"  [FAIL] Exception handler test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("FastAPI Application Startup Test")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("App Creation", test_app_creation()))
    results.append(("Middleware", test_middleware()))
    results.append(("Exception Handlers", test_exception_handlers()))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\nAll tests passed! The application is ready to run.")
        print("\nTo start the server, run:")
        print("  uvicorn app.main:app --host 0.0.0.0 --port 8080")
        return 0
    else:
        print("\nSome tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Set API_KEY in .env if REQUIRE_API_KEY=true")
        print("  - Ensure directories are writable")
        return 1


if __name__ == "__main__":
    sys.exit(main())
