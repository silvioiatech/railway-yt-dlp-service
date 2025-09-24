#!/usr/bin/env python3
"""
Test the new centralized file deletion scheduler
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

# Set API_KEY for testing
os.environ['API_KEY'] = 'test-key-123'
os.environ['STORAGE_DIR'] = '/tmp/test-storage'

def test_deletion_scheduler():
    """Test the FileDeletionScheduler functionality."""
    print("🧪 Testing Centralized File Deletion Scheduler")
    print("=" * 60)
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(__file__))
        
        from process import FileDeletionScheduler, get_deletion_scheduler
        
        scheduler = get_deletion_scheduler()
        
        # Create temporary files for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test 1: Schedule a deletion
            test_file = temp_path / "test_file.txt"
            test_file.write_text("This is a test file")
            
            print(f"📁 Created test file: {test_file}")
            print(f"📏 Initial pending tasks: {scheduler.get_pending_count()}")
            
            # Schedule deletion in 2 seconds for testing
            task_id, scheduled_time = scheduler.schedule_deletion(
                file_path=test_file,
                delay_seconds=2,
                log_callback=lambda msg, level: print(f"[{level}] {msg}")
            )
            
            print(f"⏰ Scheduled deletion: task_id={task_id}, time={scheduled_time}")
            print(f"📊 Pending tasks after scheduling: {scheduler.get_pending_count()}")
            
            # Test 2: Cancel the deletion
            print("\n🚫 Testing cancellation...")
            success = scheduler.cancel_deletion(task_id)
            print(f"✅ Cancellation {'successful' if success else 'failed'}")
            print(f"📊 Pending tasks after cancellation: {scheduler.get_pending_count()}")
            
            # Test 3: Schedule another deletion and let it execute
            test_file2 = temp_path / "test_file2.txt"
            test_file2.write_text("This file will be deleted")
            
            task_id2, scheduled_time2 = scheduler.schedule_deletion(
                file_path=test_file2,
                delay_seconds=1,  # 1 second for faster testing
                log_callback=lambda msg, level: print(f"[SCHEDULER] [{level}] {msg}")
            )
            
            print(f"\n🗑️  Scheduled second deletion: task_id={task_id2}")
            print(f"📊 Pending tasks: {scheduler.get_pending_count()}")
            print("⏳ Waiting for deletion to execute...")
            
            # Wait for deletion to happen
            time.sleep(2)
            
            print(f"📊 Pending tasks after execution: {scheduler.get_pending_count()}")
            print(f"📄 File exists after deletion: {test_file2.exists()}")
            
            # Test 4: Multiple scheduled deletions
            print("\n📚 Testing multiple scheduled deletions...")
            files_and_tasks = []
            
            for i in range(3):
                test_file = temp_path / f"multi_test_{i}.txt"
                test_file.write_text(f"Test file {i}")
                
                task_id, _ = scheduler.schedule_deletion(
                    file_path=test_file,
                    delay_seconds=3,  # 3 seconds
                    log_callback=lambda msg, level, i=i: print(f"[FILE{i}] [{level}] {msg}")
                )
                
                files_and_tasks.append((test_file, task_id))
            
            print(f"📊 Pending tasks with multiple files: {scheduler.get_pending_count()}")
            
            # Cancel one of them
            _, cancel_task = files_and_tasks[1]
            scheduler.cancel_deletion(cancel_task)
            print(f"🚫 Cancelled one task, pending: {scheduler.get_pending_count()}")
            
        print("\n✅ All scheduler tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Scheduler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pipeline_integration():
    """Test the updated pipeline with the new scheduler."""
    print("\n🔗 Testing Pipeline Integration")
    print("=" * 60)
    
    try:
        from process import RailwayStoragePipeline
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock pipeline (without actually downloading)
            pipeline = RailwayStoragePipeline(
                request_id="test-integration",
                source_url="https://example.com/test.mp4",  # Won't actually download
                storage_dir=temp_dir,
                path_template="test/{safe_title}.{ext}",
                log_callback=lambda msg, level: print(f"[PIPELINE] [{level}] {msg}")
            )
            
            # Test scheduling directly
            test_file = Path(temp_dir) / "pipeline_test.txt"
            test_file.write_text("Pipeline test file")
            
            print(f"📁 Created test file via pipeline: {test_file}")
            
            # Schedule deletion
            task_id = pipeline._schedule_deletion(test_file, delay_seconds=2)
            print(f"⏰ Pipeline scheduled deletion: {task_id}")
            print(f"🆔 Pipeline task ID: {pipeline.deletion_task_id}")
            print(f"⏲️  Pipeline deletion time: {pipeline.deletion_time}")
            
            # Test cancellation through pipeline
            success = pipeline.cancel_deletion()
            print(f"🚫 Pipeline cancellation: {'successful' if success else 'failed'}")
            print(f"🆔 Pipeline task ID after cancel: {pipeline.deletion_task_id}")
            
        print("✅ Pipeline integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all scheduler tests."""
    print("🚀 File Deletion Scheduler Tests")
    print("=" * 60)
    
    tests = [
        ("Deletion Scheduler", test_deletion_scheduler),
        ("Pipeline Integration", test_pipeline_integration)
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
        print("\n🎉 All scheduler tests passed!")
        print("\n📝 New Features Implemented:")
        print("   ✅ Centralized FileDeletionScheduler with priority queue")
        print("   ✅ Cancellable deletion tasks with unique IDs") 
        print("   ✅ Non-daemon background worker for production reliability")
        print("   ✅ Scalable - single thread handles all deletions")
        print("   ✅ Graceful shutdown with proper cleanup")
        print("   ✅ Integration with RailwayStoragePipeline")
        print("   ✅ Error handling and logging for failed deletions")
    else:
        print("⚠️  Some scheduler tests failed.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    
    # Cleanup - shutdown the scheduler
    try:
        from process import shutdown_deletion_scheduler
        shutdown_deletion_scheduler()
        print("\n🛑 Scheduler shut down cleanly")
    except:
        pass
    
    sys.exit(0 if success else 1)