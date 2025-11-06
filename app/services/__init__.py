"""
Service layer for Ultimate Media Downloader.

This package provides high-level services for media downloading, file management,
queue management, and yt-dlp integration with comprehensive error handling and
async support.
"""

from app.services.file_manager import FileManager, get_file_manager
from app.services.queue_manager import (
    QueueManager,
    get_queue_manager,
    initialize_queue_manager,
    shutdown_queue_manager,
)
from app.services.ytdlp_options import YtdlpOptionsBuilder
from app.services.ytdlp_wrapper import ProgressTracker, YtdlpWrapper

__all__ = [
    # yt-dlp wrapper
    'YtdlpWrapper',
    'ProgressTracker',
    # Options builder
    'YtdlpOptionsBuilder',
    # File management
    'FileManager',
    'get_file_manager',
    # Queue management
    'QueueManager',
    'get_queue_manager',
    'initialize_queue_manager',
    'shutdown_queue_manager',
]
