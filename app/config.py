"""
Configuration management for Ultimate Media Downloader.

This module centralizes all application configuration with environment-based settings,
validation, and type safety using Pydantic.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Core Settings
    APP_NAME: str = "Ultimate Media Downloader"
    VERSION: str = "3.0.0"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8080, ge=1024, le=65535, description="Server port")
    WORKERS: int = Field(default=2, ge=1, le=16, description="Worker processes")

    # API Configuration (REQUIRE_API_KEY must come before API_KEY for validation)
    REQUIRE_API_KEY: bool = Field(default=True, description="Enforce API key authentication")
    API_KEY: str = Field(default="", description="API authentication key")

    # Storage Configuration
    STORAGE_DIR: Path = Field(
        default=Path("/tmp/railway-downloads"),
        description="Root directory for downloaded files"
    )
    FILE_RETENTION_HOURS: float = Field(
        default=1.0,
        ge=0.1,
        le=168.0,
        description="Hours to retain files before auto-deletion"
    )

    # URL Configuration
    PUBLIC_BASE_URL: str = Field(
        default="",
        description="Public base URL for file serving"
    )

    # Download Configuration
    MAX_CONCURRENT_DOWNLOADS: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum concurrent downloads"
    )
    DEFAULT_TIMEOUT_SEC: int = Field(
        default=1800,
        ge=60,
        le=7200,
        description="Default download timeout in seconds"
    )
    PROGRESS_TIMEOUT_SEC: int = Field(
        default=300,
        ge=60,
        le=1800,
        description="Timeout for no progress detection"
    )
    MAX_CONTENT_LENGTH: int = Field(
        default=10737418240,  # 10GB
        ge=1048576,  # 1MB minimum
        description="Maximum file size in bytes"
    )

    # Rate Limiting
    RATE_LIMIT_RPS: int = Field(
        default=2,
        ge=1,
        le=100,
        description="Rate limit requests per second"
    )
    RATE_LIMIT_BURST: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Rate limit burst allowance"
    )

    # CORS Configuration (can be set as comma-separated string in env)
    CORS_ORIGINS: str = Field(
        default="*",
        description="Allowed CORS origins (comma-separated)"
    )

    # Feature Flags
    ALLOW_YT_DOWNLOADS: bool = Field(
        default=False,
        description="Allow YouTube downloads (check ToS compliance)"
    )
    ALLOWED_DOMAINS: str = Field(
        default="",
        description="Whitelist of allowed domains (comma-separated, empty = all allowed)"
    )

    # Webhook Configuration
    WEBHOOK_ENABLE: bool = Field(
        default=True,
        description="Enable webhook notification system"
    )
    WEBHOOK_TIMEOUT_SEC: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Webhook request timeout in seconds"
    )
    WEBHOOK_MAX_RETRIES: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum webhook retry attempts"
    )

    # Logging Configuration
    LOG_DIR: Path = Field(
        default=Path("./logs"),
        description="Directory for log files"
    )
    LOG_FILE_MAX_BYTES: int = Field(
        default=10485760,  # 10MB
        description="Maximum log file size before rotation"
    )
    LOG_FILE_BACKUP_COUNT: int = Field(
        default=5,
        description="Number of backup log files to keep"
    )

    # Documentation
    DISABLE_DOCS: bool = Field(
        default=False,
        description="Disable API documentation endpoints"
    )

    # Static Files
    STATIC_DIR: Path = Field(
        default=Path("./static"),
        description="Directory for static files"
    )

    # Cookie Management
    COOKIE_ENCRYPTION_KEY: Optional[str] = Field(
        default=None,
        description="AES-256 encryption key for cookies (64 hex chars / 32 bytes)"
    )

    @field_validator('API_KEY')
    @classmethod
    def validate_api_key(cls, v: str, info) -> str:
        """Validate API key is set when required."""
        require_key = info.data.get('REQUIRE_API_KEY', True)
        if require_key and not v:
            raise ValueError(
                "API_KEY must be set when REQUIRE_API_KEY is true. "
                "Set API_KEY environment variable or disable authentication."
            )
        return v

    @field_validator('STORAGE_DIR', 'LOG_DIR', 'STATIC_DIR')
    @classmethod
    def ensure_directory_exists(cls, v: Path) -> Path:
        """Ensure directory exists and is writable."""
        v = Path(v).resolve()
        v.mkdir(parents=True, exist_ok=True)

        # Test write permissions
        test_file = v / '.write_test'
        try:
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            raise ValueError(f"Directory {v} is not writable: {e}")

        return v

    @field_validator('PUBLIC_BASE_URL')
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize base URL."""
        if v:
            v = v.rstrip('/')
            if not v.startswith(('http://', 'https://')):
                raise ValueError("PUBLIC_BASE_URL must start with http:// or https://")
        return v

    @field_validator('COOKIE_ENCRYPTION_KEY')
    @classmethod
    def validate_encryption_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate encryption key format."""
        if v:
            # Remove whitespace
            v = v.strip()
            # Check if it's a valid hex string of correct length (64 hex chars = 32 bytes)
            if len(v) not in [64, 0]:
                raise ValueError(
                    "COOKIE_ENCRYPTION_KEY must be 64 hexadecimal characters (32 bytes for AES-256). "
                    "Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
                )
            if v and not all(c in '0123456789abcdefABCDEF' for c in v):
                raise ValueError("COOKIE_ENCRYPTION_KEY must be a hexadecimal string")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        if not self.CORS_ORIGINS or self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]

    @property
    def allowed_domains_list(self) -> List[str]:
        """Get allowed domains as a list."""
        if not self.ALLOWED_DOMAINS:
            return []
        return [domain.strip().lower() for domain in self.ALLOWED_DOMAINS.split(',') if domain.strip()]

    @property
    def cookies_storage_dir(self) -> Path:
        """Get cookies storage directory path."""
        return self.STORAGE_DIR / "cookies"

    class Config:
        """Pydantic configuration."""
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = 'ignore'  # Ignore extra environment variables

    def get_storage_path(self, relative_path: str) -> Path:
        """Get absolute storage path from relative path."""
        return self.STORAGE_DIR / relative_path

    def get_public_url(self, relative_path: str) -> Optional[str]:
        """Get public URL for a file path."""
        if not self.PUBLIC_BASE_URL:
            return None
        return f"{self.PUBLIC_BASE_URL}/{relative_path.lstrip('/')}"

    def is_domain_allowed(self, domain: str) -> bool:
        """Check if a domain is allowed."""
        allowed_list = self.allowed_domains_list
        if not allowed_list:
            return True  # Empty list means all domains allowed

        domain = domain.lower()
        return any(
            allowed in domain or domain in allowed
            for allowed in allowed_list
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    This function uses lru_cache to ensure only one Settings instance
    is created during the application lifetime.
    """
    return Settings()


def validate_settings() -> None:
    """
    Validate settings and raise detailed errors if invalid.

    Call this during application startup to fail fast on configuration errors.
    """
    try:
        settings = get_settings()

        # Validate critical paths
        if not settings.STORAGE_DIR.exists():
            raise RuntimeError(f"Storage directory does not exist: {settings.STORAGE_DIR}")

        if not settings.LOG_DIR.exists():
            raise RuntimeError(f"Log directory does not exist: {settings.LOG_DIR}")

        # Validate authentication requirements
        if settings.REQUIRE_API_KEY and not settings.API_KEY:
            raise RuntimeError("API_KEY is required when REQUIRE_API_KEY=true")

        # Validate YouTube compliance
        if not settings.ALLOW_YT_DOWNLOADS:
            print("⚠️  YouTube downloads are DISABLED per Terms of Service compliance")

        # Log configuration summary
        print(f"✓ Configuration validated successfully")
        print(f"  - Storage: {settings.STORAGE_DIR}")
        print(f"  - Workers: {settings.WORKERS}")
        print(f"  - Max concurrent downloads: {settings.MAX_CONCURRENT_DOWNLOADS}")
        print(f"  - Authentication: {'Required' if settings.REQUIRE_API_KEY else 'Optional'}")
        print(f"  - Cookie encryption: {'Enabled' if settings.COOKIE_ENCRYPTION_KEY else 'Auto-generated'}")

    except Exception as e:
        raise RuntimeError(f"Configuration validation failed: {e}")


# Export commonly used settings for convenience
__all__ = [
    'Settings',
    'get_settings',
    'validate_settings',
]
