#!/usr/bin/env python3
"""
Quick verification script to test core functionality
"""

import os
import sys

def test_environment():
    """Test environment setup"""
    print("🔧 Testing environment...")
    
    # Set required environment variables
    os.environ['API_KEY'] = 'test-key-12345'
    os.environ['RCLONE_REMOTE_DEFAULT'] = 'test-remote'
    os.environ['ALLOW_YT_DOWNLOADS'] = 'false'
    
    print("✅ Environment variables set")

def test_imports():
    """Test that all imports work"""
    print("📦 Testing imports...")
    
    try:
        import app
        import process
        print("✅ All imports successful")
        return app
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

def test_app_creation(app_module):
    """Test FastAPI app creation"""
    print("🚀 Testing app creation...")
    
    try:
        app = app_module.app
        assert app.title == "yt-dlp Streaming Service"
        assert app.version == "2.0.0"
        print("✅ FastAPI app created successfully")
        return app
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        sys.exit(1)

def test_path_templating():
    """Test path templating functionality"""
    print("🔤 Testing path templating...")
    
    try:
        from app import expand_path_template, sanitize_filename
        
        # Test sanitization
        assert "bad_file_name" in sanitize_filename("bad/file\\name")
        print("✅ Filename sanitization works")
        
        # Test template expansion
        metadata = {
            'id': 'abc123',
            'title': 'Test Video',
            'ext': 'mp4',
            'uploader': 'TestUser'
        }
        
        result = expand_path_template("videos/{safe_title}-{id}.{ext}", metadata)
        assert "Test_Video" in result
        assert "abc123" in result
        assert "mp4" in result
        print("✅ Path templating works")
        
    except Exception as e:
        print(f"❌ Path templating failed: {e}")
        sys.exit(1)

def test_job_management():
    """Test job management functions"""
    print("📋 Testing job management...")
    
    try:
        from app import create_job, update_job, get_job, DownloadRequest
        
        # Create a test job
        payload = DownloadRequest(
            url="https://example.com/test",
            remote="test-remote",
            path="test/{id}.{ext}"
        )
        
        job = create_job("test-123", payload)
        assert job['status'] == 'QUEUED'
        assert job['request_id'] == 'test-123'
        print("✅ Job creation works")
        
        # Update job
        updated = update_job("test-123", status="RUNNING", bytes=1000)
        assert updated['status'] == 'RUNNING'
        assert updated['bytes'] == 1000
        print("✅ Job updates work")
        
        # Get job
        retrieved = get_job("test-123")
        assert retrieved['status'] == 'RUNNING'
        print("✅ Job retrieval works")
        
    except Exception as e:
        print(f"❌ Job management failed: {e}")
        sys.exit(1)

def main():
    """Run all tests"""
    print("🧪 Starting yt-dlp Streaming Service verification...")
    print("=" * 50)
    
    test_environment()
    app_module = test_imports()
    test_app_creation(app_module)
    test_path_templating()
    test_job_management()
    
    print("=" * 50)
    print("🎉 All tests passed! Service is ready for deployment.")
    print("\n📋 Next steps:")
    print("1. Configure your rclone remotes: `rclone config`")
    print("2. Set your environment variables in .env")
    print("3. Run with Docker: `make dev`")
    print("4. Test the API endpoints with curl or Postman")

if __name__ == "__main__":
    main()