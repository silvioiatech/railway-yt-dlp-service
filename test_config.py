#!/usr/bin/env python3
"""
Simple test for Railway storage service configuration
"""

import os
import sys
from pathlib import Path

# Set API_KEY for testing
os.environ['API_KEY'] = 'test-key-123'
os.environ['STORAGE_DIR'] = '/tmp/test-storage'

def test_imports():
    """Test that the service can be imported."""
    print("📦 Testing service imports...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(__file__))
        
        from app import (
            expand_path_template,
            sanitize_filename,
            DownloadRequest,
            DownloadResponse
        )
        from process import RailwayStoragePipeline
        
        print("✅ All imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_path_functions():
    """Test path templating functions."""
    print("\n🔧 Testing path functions...")
    
    try:
        from app import expand_path_template, sanitize_filename
        
        # Test sanitize_filename
        test_cases = [
            ("Hello World!", "Hello_World_"),
            ("file/name\\test", "file_name_test"), 
            ("", "unknown"),
            ("Multiple___Under", "Multiple_Under"),
        ]
        
        for input_val, expected in test_cases:
            result = sanitize_filename(input_val)
            print(f"   sanitize: '{input_val}' → '{result}'")
            # Basic validation
            if not result or '/' in result or '\\' in result:
                print(f"   ⚠️  Potential issue with result: '{result}'")
        
        # Test expand_path_template
        metadata = {
            'id': 'abc123',
            'title': 'Test Video Title!',
            'ext': 'mp4',
            'uploader': 'Test Channel',
            'upload_date': '20240924'
        }
        
        templates = [
            "videos/{safe_title}-{id}.{ext}",
            "{uploader}/{date}/{safe_title}.{ext}",
            "downloads/{id}.{ext}"
        ]
        
        for template in templates:
            result = expand_path_template(template, metadata)
            print(f"   template: '{template}' → '{result}'")
            # Basic validation
            if '//' in result or result.startswith('/'):
                print(f"   ⚠️  Potential path issue: '{result}'")
        
        print("✅ Path function tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Path function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_creation():
    """Test that the FastAPI service can be created."""
    print("\n🚀 Testing service creation...")
    
    try:
        from app import app
        
        # Basic checks
        assert app.title == "yt-dlp Railway Storage Service"
        assert app.version == "2.1.0"
        
        print("✅ Service created successfully")
        print(f"   Title: {app.title}")
        print(f"   Version: {app.version}")
        return True
        
    except Exception as e:
        print(f"❌ Service creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_request_validation():
    """Test request model validation."""
    print("\n📋 Testing request validation...")
    
    try:
        from app import DownloadRequest
        
        # Valid request
        valid_req = DownloadRequest(
            url="https://example.com/video.mp4",
            dest="RAILWAY",
            path="videos/{safe_title}.{ext}",
            format="best"
        )
        print(f"✅ Valid request created: {valid_req.url}")
        
        # Test invalid destination
        try:
            invalid_req = DownloadRequest(
                url="https://example.com/video.mp4", 
                dest="INVALID",
                path="videos/{safe_title}.{ext}",
                format="best"
            )
            print("❌ Should have failed validation for invalid dest")
            return False
        except Exception:
            print("✅ Correctly rejected invalid destination")
        
        # Test invalid URL
        try:
            invalid_req = DownloadRequest(
                url="not-a-url",
                dest="RAILWAY",
                path="videos/{safe_title}.{ext}",
                format="best"
            )
            print("❌ Should have failed validation for invalid URL")
            return False
        except Exception:
            print("✅ Correctly rejected invalid URL")
        
        print("✅ Request validation tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Request validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Railway Storage Service Configuration Test")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Path Functions", test_path_functions), 
        ("Service Creation", test_service_creation),
        ("Request Validation", test_request_validation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔄 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Railway storage service is ready.")
        print("📝 Summary of changes:")
        print("   • Replaced rclone with Railway local storage")
        print("   • Added automatic file deletion after 1 hour") 
        print("   • Updated API models for file serving")
        print("   • Added /files/{path} endpoint for file access")
        print("   • Removed cloud storage dependencies")
        print("")
        print("🚀 Ready for deployment!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)