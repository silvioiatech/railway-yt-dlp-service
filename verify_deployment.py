#!/usr/bin/env python3
"""
Deployment Verification Script for Ultimate Media Downloader
Run this to check if your deployment will work correctly.
"""

import os
import sys
from pathlib import Path

def check_color(passed: bool) -> str:
    """Return colored check mark or X."""
    if passed:
        return "✓"
    return "✗"

def main():
    print("=" * 70)
    print("Ultimate Media Downloader - Deployment Verification")
    print("=" * 70)
    print()

    issues = []
    warnings = []

    # Check 1: Python version
    print("1. Checking Python version...")
    py_version = sys.version_info
    if py_version >= (3, 11):
        print(f"   {check_color(True)} Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    else:
        print(f"   {check_color(False)} Python {py_version.major}.{py_version.minor} (requires 3.11+)")
        issues.append("Python version must be 3.11 or higher")
    print()

    # Check 2: Required files
    print("2. Checking required files...")
    required_files = [
        "app/main.py",
        "app/config.py",
        "requirements.txt",
        "Dockerfile",
        "static/index.html",
        ".env.example"
    ]

    for file in required_files:
        path = Path(file)
        exists = path.exists()
        print(f"   {check_color(exists)} {file}")
        if not exists:
            issues.append(f"Missing required file: {file}")
    print()

    # Check 3: Environment variables
    print("3. Checking environment variables...")
    env_vars = {
        "REQUIRE_API_KEY": os.getenv("REQUIRE_API_KEY", "NOT_SET"),
        "API_KEY": "***" if os.getenv("API_KEY") else "NOT_SET",
        "STORAGE_DIR": os.getenv("STORAGE_DIR", "NOT_SET"),
        "PUBLIC_BASE_URL": os.getenv("PUBLIC_BASE_URL", "NOT_SET"),
    }

    for key, value in env_vars.items():
        if value == "NOT_SET":
            print(f"   {check_color(False)} {key}: {value}")
            warnings.append(f"Environment variable {key} not set")
        else:
            print(f"   {check_color(True)} {key}: {value}")
    print()

    # Check 4: Dependencies
    print("4. Checking Python dependencies...")
    try:
        import fastapi
        print(f"   {check_color(True)} fastapi ({fastapi.__version__})")
    except ImportError:
        print(f"   {check_color(False)} fastapi (not installed)")
        issues.append("fastapi not installed")

    try:
        import uvicorn
        print(f"   {check_color(True)} uvicorn ({uvicorn.__version__})")
    except ImportError:
        print(f"   {check_color(False)} uvicorn (not installed)")
        issues.append("uvicorn not installed")

    try:
        import pydantic
        print(f"   {check_color(True)} pydantic ({pydantic.__version__})")
    except ImportError:
        print(f"   {check_color(False)} pydantic (not installed)")
        issues.append("pydantic not installed")

    try:
        import yt_dlp
        print(f"   {check_color(True)} yt-dlp ({yt_dlp.version.__version__})")
    except ImportError:
        print(f"   {check_color(False)} yt-dlp (not installed)")
        issues.append("yt-dlp not installed")

    try:
        from cryptography.fernet import Fernet
        print(f"   {check_color(True)} cryptography")
    except ImportError:
        print(f"   {check_color(False)} cryptography (not installed)")
        issues.append("cryptography not installed")
    print()

    # Check 5: Import test
    print("5. Testing application imports...")
    try:
        # Set minimal env for import test
        if not os.getenv("REQUIRE_API_KEY"):
            os.environ["REQUIRE_API_KEY"] = "false"
        if not os.getenv("API_KEY"):
            os.environ["API_KEY"] = "test"

        from app.config import get_settings
        print(f"   {check_color(True)} app.config imports successfully")

        settings = get_settings()
        print(f"   {check_color(True)} Config loads successfully")
        print(f"       Version: {settings.VERSION}")
        print(f"       API Key required: {settings.REQUIRE_API_KEY}")

        from app.main import app as fastapi_app
        print(f"   {check_color(True)} app.main imports successfully")
        print(f"       App title: {fastapi_app.title}")
        print(f"       Routes: {len(fastapi_app.routes)}")

    except Exception as e:
        print(f"   {check_color(False)} Import failed: {e}")
        issues.append(f"Application import failed: {str(e)}")
    print()

    # Check 6: Dockerfile
    print("6. Checking Dockerfile...")
    dockerfile_path = Path("Dockerfile")
    if dockerfile_path.exists():
        content = dockerfile_path.read_text()

        # Check for correct CMD
        has_uvicorn = "uvicorn" in content and "app.main:app" in content
        print(f"   {check_color(has_uvicorn)} Using uvicorn with app.main:app")
        if not has_uvicorn:
            issues.append("Dockerfile should use: CMD ['uvicorn', 'app.main:app', ...]")

        # Check for correct health check
        has_health = "/api/v1/health" in content
        print(f"   {check_color(has_health)} Health check endpoint: /api/v1/health")
        if not has_health:
            warnings.append("Health check should use /api/v1/health")

    else:
        print(f"   {check_color(False)} Dockerfile not found")
        issues.append("Dockerfile missing")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if not issues and not warnings:
        print(f"{check_color(True)} All checks passed! Ready to deploy.")
        print()
        print("Next steps:")
        print("  1. Set environment variables in Railway:")
        print("     - REQUIRE_API_KEY=false (or true with API_KEY set)")
        print("     - API_KEY=your-secret-key")
        print("     - STORAGE_DIR=/app/data")
        print("     - PUBLIC_BASE_URL=https://your-app.railway.app")
        print()
        print("  2. Add Railway volume:")
        print("     - Mount path: /app/data")
        print("     - Size: 10GB+")
        print()
        print("  3. Deploy and verify:")
        print("     - Visit: https://your-app.railway.app/")
        print("     - API docs: https://your-app.railway.app/docs")
        print("     - Health: https://your-app.railway.app/api/v1/health")
        return 0

    if warnings:
        print(f"\n{check_color(False)} WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"   - {warning}")
        print()

    if issues:
        print(f"\n{check_color(False)} ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"   - {issue}")
        print()
        print("Fix these issues before deploying.")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
