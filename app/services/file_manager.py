"""
File management service for storage operations and path templating.

This module provides secure file operations including path template expansion,
directory traversal prevention, file size tracking, and cleanup operations.
"""
import logging
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import get_settings
from app.core.exceptions import FileNotFoundError, StorageError
from app.core.scheduler import get_scheduler

logger = logging.getLogger(__name__)


class FileManager:
    """
    Secure file manager with path templating and cleanup.

    Provides methods for path template expansion, file operations,
    and automatic cleanup scheduling.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize file manager.

        Args:
            storage_dir: Optional storage directory override
        """
        settings = get_settings()
        self.storage_dir = storage_dir or settings.STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.scheduler = get_scheduler()

    def expand_path_template(
        self,
        template: str,
        metadata: Dict[str, Any]
    ) -> Path:
        """
        Expand path template with metadata tokens.

        Supports tokens:
        - {id}: Video ID
        - {title}: Video title
        - {safe_title}: Sanitized video title
        - {ext}: File extension
        - {uploader}: Uploader name
        - {upload_date}: Upload date (YYYY-MM-DD)
        - {date}: Current date (YYYY-MM-DD)
        - {random}: Random hex string
        - {playlist}: Playlist name
        - {playlist_index}: Playlist index (zero-padded)
        - {channel}: Channel name
        - {channel_id}: Channel ID

        Args:
            template: Path template string
            metadata: Video metadata dictionary

        Returns:
            Expanded absolute path
        """
        # Extract common metadata with fallbacks
        video_id = metadata.get('id', 'unknown')
        title = metadata.get('title', 'Unknown Title')
        safe_title = self.sanitize_filename(title)
        ext = metadata.get('ext', 'mp4')
        uploader = self.sanitize_filename(metadata.get('uploader', 'unknown'))
        channel = self.sanitize_filename(metadata.get('channel', metadata.get('uploader', 'unknown')))
        channel_id = metadata.get('channel_id', metadata.get('uploader_id', 'unknown'))

        # Playlist information
        playlist = self.sanitize_filename(metadata.get('playlist', 'unknown'))
        playlist_index = metadata.get('playlist_index', 0)

        # Generate date strings
        upload_date = metadata.get('upload_date')
        if upload_date:
            try:
                date_obj = datetime.strptime(str(upload_date), '%Y%m%d')
                date_str = date_obj.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        else:
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Generate random component
        random_str = secrets.token_hex(4)

        # Template expansion
        replacements = {
            '{id}': str(video_id),
            '{title}': title,
            '{safe_title}': safe_title,
            '{ext}': ext,
            '{uploader}': uploader,
            '{channel}': channel,
            '{channel_id}': str(channel_id),
            '{upload_date}': date_str,
            '{date}': current_date,
            '{random}': random_str,
            '{playlist}': playlist,
            '{playlist_index}': str(playlist_index),
            '{playlist_index:03d}': f"{playlist_index:03d}",
        }

        expanded = template
        for token, value in replacements.items():
            expanded = expanded.replace(token, str(value))

        # Final sanitization and normalization
        expanded = re.sub(r'/+', '/', expanded.strip('/'))

        # Build absolute path
        full_path = self.storage_dir / expanded

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        return full_path

    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize filename for safe filesystem usage.

        Removes or replaces problematic characters while maintaining
        readability.

        Args:
            name: Original filename

        Returns:
            Sanitized filename
        """
        if not name:
            return "unknown"

        # Replace problematic characters with underscores
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)

        # Replace multiple spaces/underscores with single underscore
        safe = re.sub(r'[\s_]+', '_', safe)

        # Remove leading/trailing underscores and dots
        safe = safe.strip('_.')

        # Limit length (accounting for potential file extension)
        max_length = 200
        if len(safe) > max_length:
            safe = safe[:max_length]

        return safe if safe else "unknown"

    def validate_path(self, file_path: Path) -> Path:
        """
        Validate and resolve path, preventing directory traversal.

        Args:
            file_path: Path to validate

        Returns:
            Validated absolute path

        Raises:
            StorageError: If path is invalid or attempts traversal
        """
        try:
            # Convert to absolute path
            if not file_path.is_absolute():
                file_path = self.storage_dir / file_path

            # Security: Don't allow symlinks to escape storage directory
            if file_path.is_symlink():
                raise StorageError(
                    "Symlinks not allowed for security",
                    details={'path': str(file_path)}
                )

            # Resolve path (normalizes path)
            resolved = file_path.resolve(strict=False)

            # Ensure path is within storage directory
            try:
                resolved.relative_to(self.storage_dir.resolve())
            except ValueError:
                raise StorageError(
                    "Path traversal detected",
                    details={'path': str(file_path)}
                )

            return resolved

        except Exception as e:
            if isinstance(e, StorageError):
                raise
            raise StorageError(
                f"Invalid path: {str(e)}",
                details={'path': str(file_path)}
            )

    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get file information.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file information

        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If path is invalid
        """
        validated_path = self.validate_path(file_path)

        if not validated_path.exists():
            raise FileNotFoundError(str(file_path))

        if not validated_path.is_file():
            raise StorageError(
                "Path is not a file",
                details={'path': str(file_path)}
            )

        stat = validated_path.stat()

        return {
            'path': str(validated_path),
            'relative_path': str(validated_path.relative_to(self.storage_dir)),
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            'extension': validated_path.suffix,
            'name': validated_path.name,
        }

    def delete_file(self, file_path: Path) -> bool:
        """
        Delete a file.

        Args:
            file_path: Path to file to delete

        Returns:
            True if file was deleted, False if it didn't exist

        Raises:
            StorageError: If deletion fails
        """
        try:
            validated_path = self.validate_path(file_path)

            if not validated_path.exists():
                logger.warning(f"File not found for deletion: {file_path}")
                return False

            if not validated_path.is_file():
                raise StorageError(
                    "Path is not a file",
                    details={'path': str(file_path)}
                )

            validated_path.unlink()
            logger.info(f"Deleted file: {validated_path}")
            return True

        except Exception as e:
            if isinstance(e, StorageError):
                raise
            raise StorageError(
                f"Failed to delete file: {str(e)}",
                details={'path': str(file_path)}
            )

    def schedule_deletion(
        self,
        file_path: Path,
        delay_hours: Optional[float] = None
    ) -> tuple[str, float]:
        """
        Schedule automatic file deletion.

        Args:
            file_path: Path to file to delete
            delay_hours: Hours to wait before deletion (uses config default if None)

        Returns:
            Tuple of (task_id, scheduled_timestamp)

        Raises:
            StorageError: If path is invalid
        """
        settings = get_settings()
        validated_path = self.validate_path(file_path)

        # Use configured retention hours if not specified
        if delay_hours is None:
            delay_hours = settings.FILE_RETENTION_HOURS

        delay_seconds = int(delay_hours * 3600)

        # Schedule deletion
        task_id, scheduled_time = self.scheduler.schedule_deletion(
            file_path=validated_path,
            delay_seconds=delay_seconds
        )

        logger.info(
            f"Scheduled deletion of {validated_path} "
            f"in {delay_hours} hours (task: {task_id})"
        )

        return task_id, scheduled_time

    def cancel_deletion(self, task_id: str) -> bool:
        """
        Cancel a scheduled deletion.

        Args:
            task_id: Deletion task ID

        Returns:
            True if cancellation was successful
        """
        success = self.scheduler.cancel_deletion(task_id)
        if success:
            logger.info(f"Cancelled deletion task: {task_id}")
        else:
            logger.warning(f"Deletion task not found: {task_id}")
        return success

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage directory statistics.

        Returns:
            Dictionary with storage statistics
        """
        try:
            total_size = 0
            file_count = 0

            for item in self.storage_dir.rglob('*'):
                if item.is_file():
                    file_count += 1
                    try:
                        total_size += item.stat().st_size
                    except OSError:
                        pass  # Skip inaccessible files

            return {
                'storage_dir': str(self.storage_dir),
                'total_files': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
            }

        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {
                'storage_dir': str(self.storage_dir),
                'error': str(e),
            }

    def cleanup_old_files(self, max_age_hours: float = 24.0) -> int:
        """
        Clean up files older than specified age.

        Args:
            max_age_hours: Maximum file age in hours

        Returns:
            Number of files deleted
        """
        import time

        cutoff_time = time.time() - (max_age_hours * 3600)
        deleted_count = 0

        try:
            for item in self.storage_dir.rglob('*'):
                if item.is_file():
                    try:
                        if item.stat().st_mtime < cutoff_time:
                            item.unlink()
                            deleted_count += 1
                            logger.info(f"Cleaned up old file: {item}")
                    except OSError as e:
                        logger.warning(f"Failed to delete {item}: {e}")

            logger.info(f"Cleanup complete: deleted {deleted_count} files")
            return deleted_count

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return deleted_count

    def get_relative_path(self, file_path: Path) -> str:
        """
        Get path relative to storage directory.

        Args:
            file_path: Absolute or relative file path

        Returns:
            Path relative to storage directory

        Raises:
            StorageError: If path is invalid
        """
        validated_path = self.validate_path(file_path)
        try:
            return str(validated_path.relative_to(self.storage_dir))
        except ValueError:
            raise StorageError(
                "Path is not within storage directory",
                details={'path': str(file_path)}
            )

    def get_public_url(self, file_path: Path) -> Optional[str]:
        """
        Get public URL for a file.

        Args:
            file_path: File path (absolute or relative)

        Returns:
            Public URL or None if PUBLIC_BASE_URL not configured
        """
        settings = get_settings()
        if not settings.PUBLIC_BASE_URL:
            return None

        relative_path = self.get_relative_path(file_path)
        return f"{settings.PUBLIC_BASE_URL}/files/{relative_path}"


# Global file manager instance
_file_manager: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    """
    Get the global FileManager instance.

    Returns:
        FileManager: Global file manager
    """
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager
