#!/usr/bin/env python3
"""
Test script for Railway storage functionality
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from process import RailwayStoragePipeline

async def test_pipeline():
    """Test the Railway storage pipeline with a simple download."""
    
    print("🧪 Testing Railway Storage Pipeline")
    print("=" * 50)
    
    # Create temporary storage directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"📁 Using temporary storage: {temp_path}")
        
        # Test metadata extraction
        print("\n1️⃣ Testing metadata extraction...")
        
        pipeline = RailwayStoragePipeline(
            request_id="test-123",
            source_url="https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-mp4-file.mp4",  # Sample video
            storage_dir=str(temp_path),
            path_template="test/{safe_title}.{ext}",
            yt_dlp_format="best",
            timeout_sec=120,
            log_callback=lambda msg, level: print(f"[{level}] {msg}")
        )
        
        try:
            # Test metadata extraction
            metadata = await pipeline._get_metadata()
            print(f"✅ Metadata extracted successfully")
            print(f"   Title: {metadata.get('title', 'Unknown')}")
            print(f"   ID: {metadata.get('id', 'Unknown')}")
            print(f"   Ext: {metadata.get('ext', 'Unknown')}")
            
            # Test file path building
            file_path = pipeline._build_file_path(metadata)
            print(f"✅ File path built: {file_path}")
            
            # Test path template expansion
            from app import expand_path_template
            expanded = expand_path_template("test/{safe_title}-{id}.{ext}", metadata)
            print(f"✅ Path template expanded: {expanded}")
            
            print("\n🎉 All tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def test_imports():
    """Test that all imports work correctly."""
    print("📦 Testing imports...")
    
    try:
        from app import (
            # RailwayStoragePipeline,  # Already imported from process
            expand_path_template, 
            sanitize_filename,
            DownloadRequest,
            DownloadResponse
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_path_templating():
    """Test path templating functions."""
    print("\n🔧 Testing path templating...")
    
    try:
        from app import expand_path_template, sanitize_filename
        
        # Test sanitize_filename
        test_cases = [
            "Hello World!",
            "Special/Chars\\Here?",
            "Multiple___Underscores",
            "Émojis🎵AndUnicode",
            ""
        ]
        
        for test_case in test_cases:
            result = sanitize_filename(test_case)
            print(f"   '{test_case}' → '{result}'")
        
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
            "downloads/{random}/{id}.{ext}"
        ]
        
        for template in templates:
            result = expand_path_template(template, metadata)
            print(f"   '{template}' → '{result}'")
        
        print("✅ Path templating tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Path templating test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Railway Storage Service Tests")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Path Templating", test_path_templating),
        ("Pipeline", test_pipeline)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔄 Running {test_name} test...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All tests passed! Railway storage is ready.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)