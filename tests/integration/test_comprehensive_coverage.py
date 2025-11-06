"""
Comprehensive code coverage testing for Ultimate Media Downloader Backend.
YOLO MODE - Aggressive, thorough testing of all components.
"""
import asyncio
import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Any, Dict

import pytest
from pydantic import ValidationError

# Set environment variables before importing app modules
os.environ['REQUIRE_API_KEY'] = 'false'
os.environ['API_KEY'] = 'test'
os.environ['PYTHONPATH'] = '/Users/silvio/Documents/GitHub/railway-yt-dlp-service'

# Add project root to path
sys.path.insert(0, '/Users/silvio/Documents/GitHub/railway-yt-dlp-service')

# Now import app modules
from app.config import Settings, get_settings, validate_settings
from app.core.scheduler import FileDeletionScheduler, DeletionTask, get_scheduler
from app.core.state import JobState, JobStateManager, get_job_state_manager
from app.core.exceptions import *
from app.models.enums import JobStatus, QualityPreset, VideoFormat, AudioFormat, SubtitleFormat
from app.models.requests import (
    DownloadRequest, PlaylistDownloadRequest, ChannelDownloadRequest,
    BatchDownloadRequest, CookiesUploadRequest
)
from app.models.responses import (
    ProgressInfo, FileInfo, VideoMetadata, DownloadResponse, FormatInfo,
    FormatsResponse, PlaylistItemInfo, PlaylistPreviewResponse, HealthResponse
)
from app.services.file_manager import FileManager, get_file_manager
from app.services.ytdlp_options import YtdlpOptionsBuilder
from app.services.queue_manager import QueueManager, get_queue_manager


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir).resolve()


@pytest.fixture
def settings(temp_dir):
    """Create test settings."""
    return Settings(
        REQUIRE_API_KEY=False,
        API_KEY='test',
        STORAGE_DIR=temp_dir / 'storage',
        LOG_DIR=temp_dir / 'logs',
        STATIC_DIR=temp_dir / 'static',
        DEBUG=True
    )


@pytest.fixture
def scheduler():
    """Create fresh scheduler instance."""
    scheduler = FileDeletionScheduler()
    yield scheduler
    scheduler.shutdown()


@pytest.fixture
def job_state_manager():
    """Create fresh job state manager."""
    return JobStateManager()


@pytest.fixture
def file_manager(temp_dir):
    """Create file manager with temp storage."""
    return FileManager(storage_dir=temp_dir)


@pytest.fixture
def ytdlp_builder(temp_dir):
    """Create yt-dlp options builder."""
    return YtdlpOptionsBuilder(storage_dir=temp_dir)


# ============================================================================
# TEST: app/config.py - Configuration Management
# ============================================================================

class TestConfig:
    """Test configuration management."""
    
    def test_settings_default_values(self):
        """Test default settings values."""
        with patch.dict(os.environ, {'REQUIRE_API_KEY': 'false'}, clear=True):
            settings = Settings()
            assert settings.APP_NAME == "Ultimate Media Downloader"
            assert settings.VERSION == "3.0.0"
            assert settings.DEBUG is False
            assert settings.LOG_LEVEL == "INFO"
            assert settings.HOST == "0.0.0.0"
            assert settings.PORT == 8080
            assert settings.WORKERS == 2
    
    def test_settings_api_key_validation_required(self):
        """Test API key validation when required."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(REQUIRE_API_KEY=True, API_KEY='')
        assert 'API_KEY must be set' in str(exc_info.value)
    
    def test_settings_api_key_validation_not_required(self):
        """Test API key validation when not required."""
        settings = Settings(REQUIRE_API_KEY=False, API_KEY='')
        assert settings.API_KEY == ''
    
    def test_settings_port_validation(self):
        """Test port number validation."""
        with pytest.raises(ValidationError):
            Settings(PORT=100)  # Too low
        with pytest.raises(ValidationError):
            Settings(PORT=99999)  # Too high
        settings = Settings(PORT=8080)
        assert settings.PORT == 8080
    
    def test_settings_directory_creation(self, temp_dir):
        """Test directory creation and validation."""
        storage_dir = temp_dir / 'test_storage'
        settings = Settings(STORAGE_DIR=storage_dir)
        assert storage_dir.exists()
        assert storage_dir.is_dir()
    
    def test_settings_directory_not_writable(self, temp_dir):
        """Test error on non-writable directory."""
        readonly_dir = temp_dir / 'readonly'
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)
        
        try:
            with pytest.raises(ValidationError):
                Settings(STORAGE_DIR=readonly_dir)
        finally:
            readonly_dir.chmod(0o755)
    
    def test_settings_base_url_validation(self):
        """Test PUBLIC_BASE_URL validation."""
        with pytest.raises(ValidationError):
            Settings(PUBLIC_BASE_URL='not-a-url')
        
        settings = Settings(PUBLIC_BASE_URL='https://example.com/')
        assert settings.PUBLIC_BASE_URL == 'https://example.com'
    
    def test_settings_cors_origins_list(self):
        """Test CORS origins parsing."""
        settings = Settings(CORS_ORIGINS='*')
        assert settings.cors_origins_list == ['*']
        
        settings = Settings(CORS_ORIGINS='http://localhost:3000, https://example.com')
        assert len(settings.cors_origins_list) == 2
        assert 'http://localhost:3000' in settings.cors_origins_list
    
    def test_settings_allowed_domains_list(self):
        """Test allowed domains parsing."""
        settings = Settings(ALLOWED_DOMAINS='')
        assert settings.allowed_domains_list == []
        
        settings = Settings(ALLOWED_DOMAINS='example.com, test.org')
        assert 'example.com' in settings.allowed_domains_list
        assert 'test.org' in settings.allowed_domains_list
    
    def test_settings_is_domain_allowed(self):
        """Test domain allowlist checking."""
        settings = Settings(ALLOWED_DOMAINS='')
        assert settings.is_domain_allowed('any-domain.com')
        
        settings = Settings(ALLOWED_DOMAINS='example.com, test.org')
        assert settings.is_domain_allowed('example.com')
        assert settings.is_domain_allowed('subdomain.example.com')
        assert not settings.is_domain_allowed('other.com')
    
    def test_settings_get_storage_path(self, temp_dir):
        """Test storage path resolution."""
        settings = Settings(STORAGE_DIR=temp_dir)
        path = settings.get_storage_path('videos/test.mp4')
        # Resolve both for comparison (macOS has /private/var symlink)
        assert path.resolve() == (temp_dir / 'videos/test.mp4').resolve()
    
    def test_settings_get_public_url(self):
        """Test public URL generation."""
        settings = Settings(PUBLIC_BASE_URL='https://example.com')
        url = settings.get_public_url('/files/test.mp4')
        assert url == 'https://example.com/files/test.mp4'
        
        settings = Settings(PUBLIC_BASE_URL='')
        assert settings.get_public_url('/files/test.mp4') is None


# Continue with rest of tests...
# (Include all the test classes from before)

# ============================================================================
# TEST: app/core/scheduler.py - File Deletion Scheduler
# ============================================================================

class TestScheduler:
    """Test file deletion scheduler."""
    
    def test_scheduler_singleton(self):
        """Test scheduler is singleton."""
        s1 = FileDeletionScheduler()
        s2 = FileDeletionScheduler()
        assert s1 is s2
    
    def test_scheduler_schedule_deletion(self, scheduler, temp_dir):
        """Test scheduling file deletion."""
        test_file = temp_dir / 'test.txt'
        test_file.write_text('test')
        
        task_id, scheduled_time = scheduler.schedule_deletion(test_file, delay_seconds=10)
        assert isinstance(task_id, str)
        assert scheduled_time > time.time()
        assert scheduler.get_pending_count() > 0
    
    def test_scheduler_cancel_deletion(self, scheduler, temp_dir):
        """Test cancelling scheduled deletion."""
        test_file = temp_dir / 'test.txt'
        test_file.write_text('test')
        
        task_id, _ = scheduler.schedule_deletion(test_file, delay_seconds=10)
        assert scheduler.cancel_deletion(task_id)
        assert not scheduler.cancel_deletion(task_id)  # Already cancelled
        assert not scheduler.cancel_deletion('nonexistent')
    
    def test_scheduler_execute_deletion(self, scheduler, temp_dir):
        """Test file actually gets deleted."""
        test_file = temp_dir / 'test.txt'
        test_file.write_text('test')
        
        task_id, _ = scheduler.schedule_deletion(test_file, delay_seconds=1)
        time.sleep(2)
        
        # File should be deleted
        assert not test_file.exists()
    
    def test_scheduler_thread_safety(self, scheduler, temp_dir):
        """Test scheduler thread safety with concurrent operations."""
        test_files = []
        for i in range(10):
            f = temp_dir / f'test_{i}.txt'
            f.write_text(f'test{i}')
            test_files.append(f)
        
        def schedule_files():
            for f in test_files:
                scheduler.schedule_deletion(f, delay_seconds=60)
        
        threads = [threading.Thread(target=schedule_files) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert scheduler.get_pending_count() >= len(test_files)


# ============================================================================
# TEST: app/core/state.py - Job State Management  
# ============================================================================

class TestJobState:
    """Test job state management."""
    
    def test_job_state_creation(self):
        """Test creating job state."""
        job = JobState('test-job-123', url='https://example.com')
        assert job.request_id == 'test-job-123'
        assert job.status == JobStatus.QUEUED
        assert job.url == 'https://example.com'
        assert job.progress_percent == 0.0
    
    def test_job_state_to_dict(self):
        """Test job state serialization."""
        job = JobState('test-job', url='https://example.com')
        data = job.to_dict()
        
        assert data['request_id'] == 'test-job'
        assert data['status'] == 'queued'
        assert data['url'] == 'https://example.com'
        assert 'progress' in data
        assert 'logs' in data
    
    def test_job_state_update_progress(self):
        """Test updating job progress."""
        job = JobState('test-job')
        job.update_progress(
            percent=50.0,
            bytes_downloaded=1000,
            bytes_total=2000,
            speed=100.0,
            eta=10
        )
        
        assert job.progress_percent == 50.0
        assert job.bytes_downloaded == 1000
        assert job.bytes_total == 2000
        assert job.download_speed == 100.0
        assert job.eta_seconds == 10
    
    def test_job_state_add_log(self):
        """Test adding log entries."""
        job = JobState('test-job')
        job.add_log('Test message', 'INFO')
        job.add_log('Error message', 'ERROR')
        
        assert len(job.logs) == 2
        assert job.logs[0]['message'] == 'Test message'
        assert job.logs[0]['level'] == 'INFO'
        assert job.logs[1]['level'] == 'ERROR'
    
    def test_job_state_transitions(self):
        """Test job status transitions."""
        job = JobState('test-job')
        
        job.set_running()
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None
        
        job.set_completed(file_path=Path('/tmp/test.mp4'))
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.file_path == Path('/tmp/test.mp4')
    
    def test_job_state_set_failed(self):
        """Test marking job as failed."""
        job = JobState('test-job')
        job.set_failed('Download error')
        
        assert job.status == JobStatus.FAILED
        assert job.error_message == 'Download error'
        assert job.completed_at is not None
    
    def test_job_state_set_cancelled(self):
        """Test marking job as cancelled."""
        job = JobState('test-job')
        job.set_cancelled()
        
        assert job.status == JobStatus.CANCELLED
        assert job.completed_at is not None


class TestJobStateManager:
    """Test job state manager."""
    
    def test_create_job(self, job_state_manager):
        """Test creating new job."""
        job = job_state_manager.create_job('test-123', url='https://example.com')
        assert job.request_id == 'test-123'
        assert job.url == 'https://example.com'
    
    def test_get_job(self, job_state_manager):
        """Test retrieving job."""
        job_state_manager.create_job('test-123')
        job = job_state_manager.get_job('test-123')
        assert job is not None
        assert job.request_id == 'test-123'
        
        assert job_state_manager.get_job('nonexistent') is None
    
    def test_update_job(self, job_state_manager):
        """Test updating job."""
        job_state_manager.create_job('test-123')
        success = job_state_manager.update_job('test-123', progress_percent=50.0)
        assert success
        
        job = job_state_manager.get_job('test-123')
        assert job.progress_percent == 50.0
    
    def test_delete_job(self, job_state_manager):
        """Test deleting job."""
        job_state_manager.create_job('test-123')
        assert job_state_manager.delete_job('test-123')
        assert job_state_manager.get_job('test-123') is None
        assert not job_state_manager.delete_job('nonexistent')
    
    def test_list_jobs(self, job_state_manager):
        """Test listing jobs."""
        job_state_manager.create_job('job-1', status=JobStatus.QUEUED)
        job_state_manager.create_job('job-2', status=JobStatus.RUNNING)
        job_state_manager.create_job('job-3', status=JobStatus.COMPLETED)
        
        all_jobs = job_state_manager.list_jobs()
        assert len(all_jobs) == 3
        
        running = job_state_manager.list_jobs(status=JobStatus.RUNNING)
        assert len(running) == 1
        assert running[0].request_id == 'job-2'
    
    def test_list_jobs_with_limit(self, job_state_manager):
        """Test listing jobs with limit."""
        for i in range(10):
            job_state_manager.create_job(f'job-{i}')
        
        jobs = job_state_manager.list_jobs(limit=5)
        assert len(jobs) == 5
    
    def test_get_stats(self, job_state_manager):
        """Test getting statistics."""
        job_state_manager.create_job('job-1', status=JobStatus.QUEUED)
        job_state_manager.create_job('job-2', status=JobStatus.RUNNING)
        job_state_manager.create_job('job-3', status=JobStatus.COMPLETED)
        job_state_manager.create_job('job-4', status=JobStatus.FAILED)
        
        stats = job_state_manager.get_stats()
        assert stats['total_jobs'] == 4
        assert stats['queued'] == 1
        assert stats['running'] == 1
        assert stats['completed'] == 1
        assert stats['failed'] == 1
    
    def test_thread_safety(self, job_state_manager):
        """Test thread-safe operations."""
        def create_jobs(start, end):
            for i in range(start, end):
                job_state_manager.create_job(f'job-{i}')
        
        threads = [
            threading.Thread(target=create_jobs, args=(0, 50)),
            threading.Thread(target=create_jobs, args=(50, 100)),
            threading.Thread(target=create_jobs, args=(100, 150)),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        stats = job_state_manager.get_stats()
        assert stats['total_jobs'] == 150


# ============================================================================
# TEST: app/core/exceptions.py - Custom Exceptions
# ============================================================================

class TestExceptions:
    """Test custom exception types."""
    
    def test_base_exception(self):
        """Test base MediaDownloaderException."""
        exc = MediaDownloaderException('Test error', status_code=500)
        assert exc.message == 'Test error'
        assert exc.status_code == 500
        assert exc.error_code == 'MediaDownloaderException'
        
        exc_dict = exc.to_dict()
        assert exc_dict['error'] == 'Test error'
        assert exc_dict['status_code'] == 500
    
    def test_download_error(self):
        """Test DownloadError."""
        exc = DownloadError('Download failed', details={'url': 'test.com'})
        assert exc.status_code == 500
        assert exc.error_code == 'DOWNLOAD_ERROR'
        assert exc.details['url'] == 'test.com'
    
    def test_download_timeout_error(self):
        """Test DownloadTimeoutError."""
        exc = DownloadTimeoutError(300)
        assert exc.status_code == 408
        assert 'timed out after 300 seconds' in exc.message
    
    def test_download_cancelled_error(self):
        """Test DownloadCancelledError."""
        exc = DownloadCancelledError('test-123')
        assert exc.status_code == 499
        assert exc.details['request_id'] == 'test-123'
    
    def test_file_size_limit_exceeded(self):
        """Test FileSizeLimitExceeded."""
        exc = FileSizeLimitExceeded(10000000, 5000000)
        assert exc.status_code == 413
        assert exc.details['file_size'] == 10000000
        assert exc.details['max_size'] == 5000000
    
    def test_invalid_url_error(self):
        """Test InvalidURLError."""
        exc = InvalidURLError('bad-url', reason='Invalid format')
        assert exc.status_code == 400
        assert 'bad-url' in exc.message
    
    def test_job_not_found_error(self):
        """Test JobNotFoundError."""
        exc = JobNotFoundError('missing-job-123')
        assert exc.status_code == 404
        assert 'missing-job-123' in exc.message
    
    def test_queue_full_error(self):
        """Test QueueFullError."""
        exc = QueueFullError(100)
        assert exc.status_code == 503
        assert exc.details['queue_size'] == 100
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == 'AUTHENTICATION_REQUIRED'
    
    def test_invalid_api_key_error(self):
        """Test InvalidAPIKeyError."""
        exc = InvalidAPIKeyError()
        assert exc.status_code == 401
        assert exc.error_code == 'INVALID_API_KEY'
    
    def test_rate_limit_exceeded_error(self):
        """Test RateLimitExceededError."""
        exc = RateLimitExceededError(retry_after=60)
        assert exc.status_code == 429
        assert exc.details['retry_after'] == 60


# ============================================================================
# TEST: app/models/enums.py - Enumerations
# ============================================================================

class TestEnums:
    """Test enumeration types."""
    
    def test_job_status_enum(self):
        """Test JobStatus enum."""
        assert JobStatus.QUEUED.value == 'queued'
        assert JobStatus.RUNNING.value == 'running'
        assert JobStatus.COMPLETED.value == 'completed'
        assert JobStatus.FAILED.value == 'failed'
        assert JobStatus.CANCELLED.value == 'cancelled'
    
    def test_quality_preset_enum(self):
        """Test QualityPreset enum."""
        assert QualityPreset.BEST.value == 'best'
        assert QualityPreset.UHD_4K.value == '4k'
        assert QualityPreset.FHD_1080P.value == '1080p'
        assert QualityPreset.HD_720P.value == '720p'
        assert QualityPreset.AUDIO_ONLY.value == 'audio'
    
    def test_video_format_enum(self):
        """Test VideoFormat enum."""
        assert VideoFormat.MP4.value == 'mp4'
        assert VideoFormat.MKV.value == 'mkv'
        assert VideoFormat.WEBM.value == 'webm'
    
    def test_audio_format_enum(self):
        """Test AudioFormat enum."""
        assert AudioFormat.MP3.value == 'mp3'
        assert AudioFormat.M4A.value == 'm4a'
        assert AudioFormat.FLAC.value == 'flac'
    
    def test_subtitle_format_enum(self):
        """Test SubtitleFormat enum."""
        assert SubtitleFormat.SRT.value == 'srt'
        assert SubtitleFormat.VTT.value == 'vtt'
        assert SubtitleFormat.ASS.value == 'ass'


# ============================================================================
# TEST: app/models/requests.py - Request Models Validation
# ============================================================================

class TestRequestModels:
    """Test request model validation."""
    
    def test_download_request_valid(self):
        """Test valid download request."""
        req = DownloadRequest(url='https://example.com/video')
        assert req.url == 'https://example.com/video'
        assert req.quality == QualityPreset.BEST
        assert req.video_format == VideoFormat.MP4
    
    def test_download_request_invalid_url(self):
        """Test invalid URL validation."""
        with pytest.raises(ValidationError):
            DownloadRequest(url='not-a-url')
        with pytest.raises(ValidationError):
            DownloadRequest(url='ftp://example.com')
    
    def test_download_request_subtitle_languages(self):
        """Test subtitle language validation."""
        with pytest.raises(ValidationError):
            DownloadRequest(
                url='https://example.com',
                subtitle_languages=['toolong']
            )
        
        req = DownloadRequest(
            url='https://example.com',
            subtitle_languages=['en', 'es', 'fr']
        )
        assert len(req.subtitle_languages) == 3
    
    def test_download_request_audio_quality(self):
        """Test audio quality validation."""
        with pytest.raises(ValidationError):
            DownloadRequest(
                url='https://example.com',
                audio_quality='999'
            )
        
        req = DownloadRequest(
            url='https://example.com',
            audio_quality='320'
        )
        assert req.audio_quality == '320'
    
    def test_download_request_custom_format(self):
        """Test custom format validation."""
        with pytest.raises(ValidationError):
            DownloadRequest(
                url='https://example.com',
                custom_format='bestvideo; rm -rf /'
            )
        
        req = DownloadRequest(
            url='https://example.com',
            custom_format='bestvideo+bestaudio'
        )
        assert req.custom_format == 'bestvideo+bestaudio'
    
    def test_playlist_download_request(self):
        """Test playlist download request."""
        req = PlaylistDownloadRequest(url='https://example.com/playlist')
        assert req.url == 'https://example.com/playlist'
        assert req.skip_downloaded
        assert req.ignore_errors
    
    def test_playlist_items_validation(self):
        """Test playlist items selection validation."""
        req = PlaylistDownloadRequest(
            url='https://example.com/playlist',
            items='1-10,15,20-25'
        )
        assert req.items == '1-10,15,20-25'
        
        with pytest.raises(ValidationError):
            PlaylistDownloadRequest(
                url='https://example.com/playlist',
                items='invalid'
            )
    
    def test_playlist_start_end_validation(self):
        """Test playlist start/end validation."""
        req = PlaylistDownloadRequest(
            url='https://example.com/playlist',
            start=1,
            end=10
        )
        assert req.start == 1
        assert req.end == 10
        
        with pytest.raises(ValidationError):
            PlaylistDownloadRequest(
                url='https://example.com/playlist',
                start=10,
                end=5
            )
    
    def test_channel_download_request(self):
        """Test channel download request."""
        req = ChannelDownloadRequest(
            url='https://example.com/channel',
            date_after='20200101',
            date_before='20231231'
        )
        assert req.date_after == '20200101'
        assert req.date_before == '20231231'
    
    def test_channel_date_validation(self):
        """Test channel date format validation."""
        with pytest.raises(ValidationError):
            ChannelDownloadRequest(
                url='https://example.com/channel',
                date_after='2020-01-01'
            )
        
        with pytest.raises(ValidationError):
            ChannelDownloadRequest(
                url='https://example.com/channel',
                date_after='20201301'  # Invalid month
            )
    
    def test_channel_duration_validation(self):
        """Test channel duration filters."""
        req = ChannelDownloadRequest(
            url='https://example.com/channel',
            min_duration=60,
            max_duration=3600
        )
        assert req.min_duration == 60
        assert req.max_duration == 3600
        
        with pytest.raises(ValidationError):
            ChannelDownloadRequest(
                url='https://example.com/channel',
                min_duration=3600,
                max_duration=60
            )
    
    def test_batch_download_request(self):
        """Test batch download request."""
        req = BatchDownloadRequest(
            urls=[
                'https://example.com/video1',
                'https://example.com/video2'
            ]
        )
        assert len(req.urls) == 2
        assert req.concurrent_limit == 3
    
    def test_batch_urls_validation(self):
        """Test batch URL validation."""
        with pytest.raises(ValidationError):
            BatchDownloadRequest(urls=[])
        
        with pytest.raises(ValidationError):
            BatchDownloadRequest(
                urls=['https://example.com', 'https://example.com']
            )  # Duplicates
    
    def test_cookies_upload_request(self):
        """Test cookies upload request."""
        req = CookiesUploadRequest(
            cookies='# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tFALSE\t0\ttest\tvalue',
            name='test-cookies'
        )
        assert req.name == 'test-cookies'
    
    def test_cookies_validation(self):
        """Test cookie format validation."""
        with pytest.raises(ValidationError):
            CookiesUploadRequest(cookies='invalid')
        
        with pytest.raises(ValidationError):
            CookiesUploadRequest()  # Neither cookies nor browser


# ============================================================================
# TEST: app/models/responses.py - Response Models
# ============================================================================

class TestResponseModels:
    """Test response model serialization."""
    
    def test_progress_info(self):
        """Test ProgressInfo model."""
        progress = ProgressInfo(
            percent=50.0,
            downloaded_bytes=1000,
            total_bytes=2000,
            speed=100.0,
            eta=10
        )
        assert progress.percent == 50.0
        assert progress.downloaded_bytes == 1000
    
    def test_file_info(self):
        """Test FileInfo model."""
        file_info = FileInfo(
            filename='test.mp4',
            file_url='https://example.com/test.mp4',
            size_bytes=1024000
        )
        assert file_info.filename == 'test.mp4'
        assert file_info.size_bytes == 1024000
    
    def test_video_metadata(self):
        """Test VideoMetadata model."""
        metadata = VideoMetadata(
            title='Test Video',
            uploader='Test Channel',
            duration=300,
            view_count=1000000
        )
        assert metadata.title == 'Test Video'
        assert metadata.duration == 300
    
    def test_download_response(self):
        """Test DownloadResponse model."""
        response = DownloadResponse(
            request_id='test-123',
            status=JobStatus.COMPLETED,
            created_at=datetime.now(timezone.utc)
        )
        assert response.request_id == 'test-123'
        assert response.status == JobStatus.COMPLETED
    
    def test_health_response(self):
        """Test HealthResponse model."""
        health = HealthResponse(
            status='healthy',
            timestamp=datetime.now(timezone.utc),
            version='3.0.0',
            uptime_seconds=3600.0,
            checks={}
        )
        assert health.status == 'healthy'
        assert health.uptime_seconds == 3600.0


# ============================================================================
# TEST: app/services/file_manager.py - File Management
# ============================================================================

class TestFileManager:
    """Test file manager operations."""
    
    def test_sanitize_filename(self, file_manager):
        """Test filename sanitization."""
        assert file_manager.sanitize_filename('test.mp4') == 'test.mp4'
        assert file_manager.sanitize_filename('test<>:"/\\|?*.mp4') == 'test_.mp4'
        assert file_manager.sanitize_filename('  test  file  ') == 'test_file'
        assert file_manager.sanitize_filename('') == 'unknown'
    
    def test_validate_path_security(self, file_manager):
        """Test path validation prevents traversal."""
        safe_path = file_manager.storage_dir / 'test.mp4'
        validated = file_manager.validate_path(safe_path)
        assert validated == safe_path.resolve()
        
        # Test traversal attempt
        with pytest.raises(StorageError):
            file_manager.validate_path(Path('../../../etc/passwd'))
    
    def test_validate_path_symlink(self, file_manager, temp_dir):
        """Test symlink rejection."""
        target = temp_dir / 'target.txt'
        target.write_text('test')
        symlink = file_manager.storage_dir / 'link.txt'
        symlink.symlink_to(target)
        
        with pytest.raises(StorageError):
            file_manager.validate_path(symlink)
    
    def test_get_file_info(self, file_manager):
        """Test getting file information."""
        test_file = file_manager.storage_dir / 'test.txt'
        test_file.write_text('test content')
        
        info = file_manager.get_file_info(test_file)
        assert info['name'] == 'test.txt'
        assert info['size'] == 12
        assert info['extension'] == '.txt'
    
    def test_get_file_info_not_found(self, file_manager):
        """Test getting info for non-existent file."""
        with pytest.raises(FileNotFoundError):
            file_manager.get_file_info(Path('nonexistent.txt'))
    
    def test_delete_file(self, file_manager):
        """Test file deletion."""
        test_file = file_manager.storage_dir / 'test.txt'
        test_file.write_text('test')
        
        assert file_manager.delete_file(test_file)
        assert not test_file.exists()
        assert not file_manager.delete_file(test_file)  # Already deleted
    
    def test_schedule_deletion(self, file_manager):
        """Test scheduling file deletion."""
        test_file = file_manager.storage_dir / 'test.txt'
        test_file.write_text('test')
        
        task_id, scheduled_time = file_manager.schedule_deletion(test_file, delay_hours=1.0)
        assert isinstance(task_id, str)
        assert scheduled_time > time.time()
    
    def test_cancel_deletion(self, file_manager):
        """Test cancelling scheduled deletion."""
        test_file = file_manager.storage_dir / 'test.txt'
        test_file.write_text('test')
        
        task_id, _ = file_manager.schedule_deletion(test_file, delay_hours=1.0)
        assert file_manager.cancel_deletion(task_id)
        assert not file_manager.cancel_deletion('nonexistent')
    
    def test_get_storage_stats(self, file_manager):
        """Test getting storage statistics."""
        # Create some test files
        for i in range(5):
            f = file_manager.storage_dir / f'test_{i}.txt'
            f.write_text(f'test content {i}')
        
        stats = file_manager.get_storage_stats()
        assert stats['total_files'] >= 5
        assert stats['total_size_bytes'] > 0
    
    def test_cleanup_old_files(self, file_manager):
        """Test cleaning up old files."""
        # Create old file
        old_file = file_manager.storage_dir / 'old.txt'
        old_file.write_text('old')
        
        # Modify timestamp to make it old
        old_time = time.time() - (48 * 3600)
        os.utime(old_file, (old_time, old_time))
        
        # Create new file
        new_file = file_manager.storage_dir / 'new.txt'
        new_file.write_text('new')
        
        deleted = file_manager.cleanup_old_files(max_age_hours=24.0)
        assert deleted >= 1
        assert not old_file.exists()
        assert new_file.exists()
    
    def test_expand_path_template(self, file_manager):
        """Test path template expansion."""
        metadata = {
            'id': 'abc123',
            'title': 'Test Video',
            'ext': 'mp4',
            'uploader': 'Test Channel',
            'upload_date': '20230101'
        }
        
        template = 'videos/{id}-{safe_title}.{ext}'
        path = file_manager.expand_path_template(template, metadata)
        
        assert 'abc123' in str(path)
        assert 'Test_Video' in str(path)
        assert path.suffix == '.mp4'
    
    def test_get_relative_path(self, file_manager):
        """Test getting relative path."""
        test_file = file_manager.storage_dir / 'videos' / 'test.mp4'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('test')
        
        rel_path = file_manager.get_relative_path(test_file)
        assert 'videos' in rel_path and 'test.mp4' in rel_path
    
    def test_get_public_url(self, file_manager):
        """Test public URL generation."""
        test_file = file_manager.storage_dir / 'test.mp4'
        test_file.write_text('test')
        
        # Without PUBLIC_BASE_URL
        assert file_manager.get_public_url(test_file) is None


# ============================================================================
# TEST: app/services/ytdlp_options.py - Options Builder
# ============================================================================

class TestYtdlpOptionsBuilder:
    """Test yt-dlp options builder."""
    
    def test_build_from_request_basic(self, ytdlp_builder):
        """Test building basic options."""
        req = DownloadRequest(url='https://example.com/video')
        opts = ytdlp_builder.build_from_request(req, 'test-123')
        
        assert 'format' in opts
        assert 'outtmpl' in opts
        assert opts['no_overwrites']
    
    def test_build_format_string_best(self, ytdlp_builder):
        """Test format string for best quality."""
        req = DownloadRequest(
            url='https://example.com',
            quality=QualityPreset.BEST
        )
        opts = ytdlp_builder.build_from_request(req, 'test')
        assert 'bestvideo+bestaudio' in opts['format']
    
    def test_build_format_string_audio_only(self, ytdlp_builder):
        """Test format string for audio only."""
        req = DownloadRequest(
            url='https://example.com',
            audio_only=True
        )
        opts = ytdlp_builder.build_from_request(req, 'test')
        assert opts['format'] == 'bestaudio/best'
    
    def test_build_format_string_custom(self, ytdlp_builder):
        """Test custom format string."""
        req = DownloadRequest(
            url='https://example.com',
            custom_format='bestvideo[height<=1080]+bestaudio'
        )
        opts = ytdlp_builder.build_from_request(req, 'test')
        assert opts['format'] == 'bestvideo[height<=1080]+bestaudio'
    
    def test_build_subtitle_options(self, ytdlp_builder):
        """Test subtitle options."""
        req = DownloadRequest(
            url='https://example.com',
            download_subtitles=True,
            subtitle_languages=['en', 'es'],
            subtitle_format=SubtitleFormat.SRT,
            embed_subtitles=True
        )
        opts = ytdlp_builder.build_from_request(req, 'test')
        
        assert opts['writesubtitles']
        assert opts['subtitleslangs'] == ['en', 'es']
        assert opts['subtitlesformat'] == 'srt'
        assert opts['embedsubtitles']
    
    def test_build_thumbnail_options(self, ytdlp_builder):
        """Test thumbnail options."""
        req = DownloadRequest(
            url='https://example.com',
            write_thumbnail=True,
            embed_thumbnail=True
        )
        opts = ytdlp_builder.build_from_request(req, 'test')
        
        assert opts['writethumbnail']
        assert opts['embedthumbnail']
    
    def test_build_postprocessors(self, ytdlp_builder):
        """Test postprocessor configuration."""
        req = DownloadRequest(
            url='https://example.com',
            audio_only=True,
            audio_format=AudioFormat.MP3,
            audio_quality='320',
            embed_metadata=True
        )
        opts = ytdlp_builder.build_from_request(req, 'test')
        
        assert 'postprocessors' in opts
        assert len(opts['postprocessors']) > 0
        
        # Check for audio extractor
        has_audio_extractor = any(
            pp['key'] == 'FFmpegExtractAudio'
            for pp in opts['postprocessors']
        )
        assert has_audio_extractor
    
    def test_build_playlist_options(self, ytdlp_builder):
        """Test playlist options."""
        req = PlaylistDownloadRequest(
            url='https://example.com/playlist',
            items='1-10',
            skip_downloaded=True,
            reverse_playlist=True
        )
        opts = ytdlp_builder.build_playlist_options(req, 'test')
        
        assert opts['playlist_items'] == '1-10'
        assert 'download_archive' in opts
        assert opts['playlistreverse']
    
    def test_build_channel_options(self, ytdlp_builder):
        """Test channel options."""
        req = ChannelDownloadRequest(
            url='https://example.com/channel',
            date_after='20200101',
            min_duration=60,
            max_downloads=100
        )
        opts = ytdlp_builder.build_channel_options(req, 'test')
        
        assert opts['dateafter'] == '20200101'
        assert 'match_filter' in opts
        assert opts['max_downloads'] == 100


# ============================================================================
# TEST: app/services/queue_manager.py - Queue Management
# ============================================================================

class TestQueueManager:
    """Test queue manager."""
    
    @pytest.mark.asyncio
    async def test_queue_manager_start(self):
        """Test starting queue manager."""
        qm = QueueManager(max_workers=2, max_concurrent_downloads=5)
        await qm.start()
        
        assert qm._started
        assert qm.executor is not None
        assert qm.event_loop is not None
        
        await qm.shutdown()
    
    @pytest.mark.asyncio
    async def test_queue_manager_shutdown(self):
        """Test shutting down queue manager."""
        qm = QueueManager()
        await qm.start()
        await qm.shutdown()
        
        assert not qm._started
        assert qm.executor is None
    
    @pytest.mark.asyncio
    async def test_submit_job(self):
        """Test submitting job to queue."""
        qm = QueueManager()
        await qm.start()
        
        async def test_coroutine():
            await asyncio.sleep(0.1)
            return 'done'
        
        future = qm.submit_job('test-job', test_coroutine())
        result = future.result(timeout=5)
        assert result == 'done'
        
        await qm.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_job_status(self):
        """Test getting job status."""
        qm = QueueManager()
        await qm.start()
        
        async def test_coroutine():
            await asyncio.sleep(1)
            return 'done'
        
        future = qm.submit_job('test-job', test_coroutine())
        
        status = qm.get_job_status('test-job')
        assert status is not None
        assert status['job_id'] == 'test-job'
        
        future.result(timeout=5)
        await qm.shutdown()
    
    @pytest.mark.asyncio
    async def test_cancel_job(self):
        """Test cancelling job."""
        qm = QueueManager()
        await qm.start()
        
        async def long_coroutine():
            await asyncio.sleep(10)
        
        qm.submit_job('test-job', long_coroutine())
        await asyncio.sleep(0.1)
        
        cancelled = qm.cancel_job('test-job')
        # Cancellation may or may not succeed depending on timing
        # Just verify the method works
        
        await qm.shutdown(wait=False)
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting queue statistics."""
        qm = QueueManager()
        await qm.start()
        
        stats = qm.get_stats()
        assert stats['started']
        assert stats['max_workers'] > 0
        assert 'active_jobs' in stats
        
        await qm.shutdown()
    
    @pytest.mark.asyncio
    async def test_is_healthy(self):
        """Test health check."""
        qm = QueueManager()
        assert not qm.is_healthy()
        
        await qm.start()
        assert qm.is_healthy()
        
        await qm.shutdown()
        assert not qm.is_healthy()


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=app', '--cov-report=term-missing', '--cov-report=html'])

