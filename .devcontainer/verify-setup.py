#!/usr/bin/env python3
"""
Dev Container Setup Verification Script

This script verifies that the dev container is properly configured
and all dependencies are working correctly.
"""

import sys
import importlib
from pathlib import Path
from typing import List, Tuple


def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is 3.11+"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        return True, f"✓ Python {version.major}.{version.minor}.{version.micro}"
    return False, f"✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.11+)"


def check_import(module_name: str) -> Tuple[bool, str]:
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        return True, f"✓ {module_name}"
    except ImportError as e:
        return False, f"✗ {module_name}: {e}"


def check_file_exists(file_path: str) -> Tuple[bool, str]:
    """Check if a file exists"""
    path = Path(file_path)
    if path.exists():
        return True, f"✓ {file_path}"
    return False, f"✗ {file_path} not found"


def check_directory_writable(dir_path: str) -> Tuple[bool, str]:
    """Check if a directory is writable"""
    path = Path(dir_path)
    
    # Create directory if it doesn't exist
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"✗ Cannot create {dir_path}: {e}"
    
    # Test write permission
    test_file = path / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
        return True, f"✓ {dir_path} is writable"
    except Exception as e:
        return False, f"✗ {dir_path} not writable: {e}"


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("Dev Container Setup Verification")
    print("=" * 60)
    print()
    
    all_checks_passed = True
    
    # Check Python version
    print("Python Environment:")
    print("-" * 60)
    passed, msg = check_python_version()
    print(msg)
    all_checks_passed &= passed
    print()
    
    # Check required Python packages
    print("Required Dependencies:")
    print("-" * 60)
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "httpx",
        "yt_dlp",
        "pytest",
        "pytest_asyncio",
        "pytest_cov",
    ]
    
    for package in required_packages:
        passed, msg = check_import(package)
        print(msg)
        all_checks_passed &= passed
    print()
    
    # Check application structure
    print("Application Structure:")
    print("-" * 60)
    
    required_files = [
        "app/__init__.py",
        "app/main.py",
        "app/config.py",
        "requirements.txt",
        "requirements-test.txt",
    ]
    
    for file_path in required_files:
        passed, msg = check_file_exists(file_path)
        print(msg)
        all_checks_passed &= passed
    print()
    
    # Check directory permissions
    print("Directory Permissions:")
    print("-" * 60)
    
    required_dirs = [
        "/app/data",
        "/workspace/logs",
    ]
    
    for dir_path in required_dirs:
        passed, msg = check_directory_writable(dir_path)
        print(msg)
        all_checks_passed &= passed
    print()
    
    # Check application can be imported
    print("Application Import:")
    print("-" * 60)
    try:
        from app.main import app
        print("✓ FastAPI app can be imported")
        print(f"✓ App title: {app.title}")
    except Exception as e:
        print(f"✗ Failed to import app: {e}")
        all_checks_passed = False
    print()
    
    # Final summary
    print("=" * 60)
    if all_checks_passed:
        print("✓ All checks passed! Dev container is ready.")
        print()
        print("Next steps:")
        print("  1. Run tests: pytest")
        print("  2. Start app: uvicorn app.main:app --reload")
        print("  3. Visit: http://localhost:8080/docs")
        return 0
    else:
        print("✗ Some checks failed. Please review the errors above.")
        print()
        print("Try running:")
        print("  pip install -r requirements.txt -r requirements-test.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
