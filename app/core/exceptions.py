"""
Custom exceptions for the Ultimate Media Downloader.

Provides a hierarchy of exceptions for different error scenarios with
proper HTTP status codes and error messages.
"""

from typing import Any, Dict, Optional


class MediaDownloaderException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        result = {
            'error': self.message,
            'error_code': self.error_code,
            'status_code': self.status_code,
        }
        if self.details:
            result['details'] = self.details
        return result


# Download-related exceptions
class DownloadError(MediaDownloaderException):
    """General download error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code='DOWNLOAD_ERROR',
            details=details
        )


class DownloadTimeoutError(DownloadError):
    """Download exceeded timeout limit."""

    def __init__(self, timeout_seconds: int):
        super().__init__(
            message=f"Download timed out after {timeout_seconds} seconds",
            details={'timeout_seconds': timeout_seconds}
        )
        self.error_code = 'DOWNLOAD_TIMEOUT'
        self.status_code = 408


class DownloadCancelledError(DownloadError):
    """Download was cancelled by user."""

    def __init__(self, request_id: str):
        super().__init__(
            message="Download was cancelled",
            details={'request_id': request_id}
        )
        self.error_code = 'DOWNLOAD_CANCELLED'
        self.status_code = 499


class FileSizeLimitExceeded(DownloadError):
    """File size exceeds configured limit."""

    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            message=f"File size ({file_size} bytes) exceeds limit ({max_size} bytes)",
            details={'file_size': file_size, 'max_size': max_size}
        )
        self.error_code = 'FILE_SIZE_LIMIT_EXCEEDED'
        self.status_code = 413


# Metadata-related exceptions
class MetadataExtractionError(MediaDownloaderException):
    """Failed to extract metadata from URL."""

    def __init__(self, message: str, url: str):
        super().__init__(
            message=message,
            status_code=422,
            error_code='METADATA_EXTRACTION_ERROR',
            details={'url': url}
        )


# Validation exceptions
class ValidationError(MediaDownloaderException):
    """General validation error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code='VALIDATION_ERROR',
            details=details
        )


class InvalidURLError(MediaDownloaderException):
    """Invalid or unsupported URL."""

    def __init__(self, url: str, reason: Optional[str] = None):
        message = f"Invalid URL: {url}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            status_code=400,
            error_code='INVALID_URL',
            details={'url': url, 'reason': reason}
        )


class UnsupportedPlatformError(MediaDownloaderException):
    """Platform/domain not supported or allowed."""

    def __init__(self, domain: str, reason: Optional[str] = None):
        message = f"Platform not supported: {domain}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            status_code=403,
            error_code='UNSUPPORTED_PLATFORM',
            details={'domain': domain, 'reason': reason}
        )


class InvalidFormatError(MediaDownloaderException):
    """Invalid format specification."""

    def __init__(self, format_string: str, reason: Optional[str] = None):
        message = f"Invalid format: {format_string}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            status_code=400,
            error_code='INVALID_FORMAT',
            details={'format': format_string, 'reason': reason}
        )


# Job/Queue exceptions
class JobNotFoundError(MediaDownloaderException):
    """Job with specified ID not found."""

    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job not found: {job_id}",
            status_code=404,
            error_code='JOB_NOT_FOUND',
            details={'job_id': job_id}
        )


class QueueFullError(MediaDownloaderException):
    """Job queue is full."""

    def __init__(self, queue_size: int):
        super().__init__(
            message="Job queue is full, please try again later",
            status_code=503,
            error_code='QUEUE_FULL',
            details={'queue_size': queue_size}
        )


# Storage exceptions
class StorageError(MediaDownloaderException):
    """Storage operation failed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code='STORAGE_ERROR',
            details=details
        )


class StorageQuotaExceeded(StorageError):
    """Storage quota exceeded."""

    def __init__(self, used_bytes: int, quota_bytes: int):
        super().__init__(
            message="Storage quota exceeded",
            details={'used_bytes': used_bytes, 'quota_bytes': quota_bytes}
        )
        self.error_code = 'STORAGE_QUOTA_EXCEEDED'
        self.status_code = 507


class FileNotFoundError(StorageError):
    """File not found in storage."""

    def __init__(self, file_path: str):
        super().__init__(
            message=f"File not found: {file_path}",
            details={'file_path': file_path}
        )
        self.error_code = 'FILE_NOT_FOUND'
        self.status_code = 404


# Authentication exceptions
class AuthenticationError(MediaDownloaderException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            error_code='AUTHENTICATION_REQUIRED'
        )


class InvalidAPIKeyError(AuthenticationError):
    """Invalid API key provided."""

    def __init__(self):
        super().__init__(message="Invalid API key")
        self.error_code = 'INVALID_API_KEY'


class RateLimitExceededError(MediaDownloaderException):
    """Rate limit exceeded."""

    def __init__(self, retry_after: Optional[int] = None):
        message = "Rate limit exceeded"
        details = {}
        if retry_after:
            message += f", retry after {retry_after} seconds"
            details['retry_after'] = retry_after

        super().__init__(
            message=message,
            status_code=429,
            error_code='RATE_LIMIT_EXCEEDED',
            details=details
        )


# Cookie/Auth management exceptions
class CookieError(MediaDownloaderException):
    """Cookie-related error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code='COOKIE_ERROR',
            details=details
        )


class InvalidCookieFormatError(CookieError):
    """Invalid cookie format."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid cookie format: {reason}",
            details={'reason': reason}
        )
        self.error_code = 'INVALID_COOKIE_FORMAT'


# Webhook exceptions
class WebhookError(MediaDownloaderException):
    """Webhook delivery failed."""

    def __init__(self, url: str, reason: str):
        super().__init__(
            message=f"Webhook delivery failed: {reason}",
            status_code=500,
            error_code='WEBHOOK_ERROR',
            details={'webhook_url': url, 'reason': reason}
        )


# Configuration exceptions
class ConfigurationError(MediaDownloaderException):
    """Configuration error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code='CONFIGURATION_ERROR',
            details=details
        )
