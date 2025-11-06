"""
Cookie management service with encryption and browser extraction support.

This module provides secure storage and retrieval of authentication cookies
for downloading private/members-only content. Cookies are encrypted at rest
using AES-256-GCM and can be extracted from installed browsers.
"""

import json
import logging
import secrets
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class CookieEncryption:
    """
    Handle AES-256-GCM encryption and decryption for cookies.

    Uses authenticated encryption to ensure both confidentiality and integrity.
    """

    def __init__(self, encryption_key: bytes):
        """
        Initialize encryption handler.

        Args:
            encryption_key: 32-byte key for AES-256
        """
        if len(encryption_key) != 32:
            raise ValueError("Encryption key must be 32 bytes for AES-256")
        self.cipher = AESGCM(encryption_key)

    def encrypt(self, plaintext: str) -> Dict[str, str]:
        """
        Encrypt plaintext with AES-256-GCM.

        Args:
            plaintext: Text to encrypt

        Returns:
            Dictionary with 'nonce' and 'ciphertext' as base64-encoded strings
        """
        # Generate random 96-bit nonce (recommended for GCM)
        nonce = secrets.token_bytes(12)

        # Encrypt with authentication
        plaintext_bytes = plaintext.encode('utf-8')
        ciphertext = self.cipher.encrypt(nonce, plaintext_bytes, None)

        return {
            'nonce': nonce.hex(),
            'ciphertext': ciphertext.hex(),
        }

    def decrypt(self, encrypted_data: Dict[str, str]) -> str:
        """
        Decrypt ciphertext with AES-256-GCM.

        Args:
            encrypted_data: Dictionary with 'nonce' and 'ciphertext' hex strings

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails (tampered data or wrong key)
        """
        try:
            nonce = bytes.fromhex(encrypted_data['nonce'])
            ciphertext = bytes.fromhex(encrypted_data['ciphertext'])

            plaintext_bytes = self.cipher.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt cookies - data may be corrupted or key is invalid")


class CookieManager:
    """
    Manage cookie storage, retrieval, and browser extraction.

    Provides secure cookie management with encryption at rest and support
    for extracting cookies from Chrome, Firefox, Edge, Safari, and other browsers.
    """

    def __init__(self):
        """Initialize cookie manager with storage and encryption."""
        settings = get_settings()
        self.storage_dir = settings.STORAGE_DIR / "cookies"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize encryption
        encryption_key = self._get_or_create_encryption_key()
        self.encryptor = CookieEncryption(encryption_key)

        logger.info(f"Cookie manager initialized with storage: {self.storage_dir}")

    def _get_or_create_encryption_key(self) -> bytes:
        """
        Get encryption key from environment or generate new one.

        Returns:
            32-byte encryption key
        """
        settings = get_settings()

        # Check if key exists in environment
        env_key = getattr(settings, 'COOKIE_ENCRYPTION_KEY', None)
        if env_key:
            # Decode from hex if provided as hex string
            try:
                if isinstance(env_key, str):
                    key = bytes.fromhex(env_key)
                else:
                    key = env_key

                if len(key) == 32:
                    return key
                else:
                    logger.warning(f"Invalid encryption key length: {len(key)}, generating new key")
            except Exception as e:
                logger.warning(f"Failed to parse encryption key: {e}, generating new key")

        # Generate new key and save to file for persistence
        key_file = self.storage_dir / ".encryption_key"

        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    key = f.read()
                if len(key) == 32:
                    logger.info("Loaded existing encryption key from file")
                    return key
            except Exception as e:
                logger.warning(f"Failed to load encryption key from file: {e}")

        # Generate new 256-bit key
        key = secrets.token_bytes(32)

        # Save to file with restricted permissions
        try:
            key_file.touch(mode=0o600, exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            logger.warning(
                f"Generated new encryption key and saved to {key_file}. "
                "For production, set COOKIE_ENCRYPTION_KEY environment variable."
            )
        except Exception as e:
            logger.error(f"Failed to save encryption key: {e}")

        return key

    def validate_cookies(self, cookies_content: str) -> bool:
        """
        Validate Netscape cookie format.

        Args:
            cookies_content: Cookie content to validate

        Returns:
            True if valid format

        Raises:
            ValidationError: If format is invalid
        """
        if not cookies_content or not cookies_content.strip():
            raise ValidationError("Cookies content is empty")

        lines = cookies_content.strip().split('\n')
        has_valid_header = False
        has_valid_data = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for Netscape header
            if line.startswith('# Netscape HTTP Cookie File') or line.startswith('# HTTP Cookie File'):
                has_valid_header = True
                continue

            # Skip other comments
            if line.startswith('#'):
                continue

            # Validate cookie line format
            # Format: domain flag path secure expiration name value
            parts = line.split('\t')
            if len(parts) < 7:
                raise ValidationError(
                    f"Invalid cookie line format - expected 7 tab-separated fields, got {len(parts)}"
                )

            has_valid_data = True

            # Validate field types
            domain = parts[0]
            flag = parts[1]
            path = parts[2]
            secure = parts[3]
            expiration = parts[4]
            name = parts[5]

            if not domain:
                raise ValidationError("Cookie domain cannot be empty")
            if flag not in ['TRUE', 'FALSE']:
                raise ValidationError(f"Cookie flag must be TRUE or FALSE, got: {flag}")
            if secure not in ['TRUE', 'FALSE']:
                raise ValidationError(f"Cookie secure flag must be TRUE or FALSE, got: {secure}")
            try:
                int(expiration)
            except ValueError:
                raise ValidationError(f"Cookie expiration must be a number, got: {expiration}")
            if not name:
                raise ValidationError("Cookie name cannot be empty")

        if not (has_valid_header or has_valid_data):
            raise ValidationError(
                "Invalid Netscape cookie format - no valid header or data found. "
                "Cookies should be in Netscape format (tab-separated values)."
            )

        return True

    def save_cookies(
        self,
        cookies_content: str,
        name: str = "default",
        browser: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Save cookies with encryption.

        Args:
            cookies_content: Cookies in Netscape format
            name: Friendly name for the cookie set
            browser: Browser name if extracted from browser

        Returns:
            Dictionary with cookie_id and metadata

        Raises:
            ValidationError: If cookies are invalid
        """
        # Validate cookies format
        self.validate_cookies(cookies_content)

        # Generate unique cookie ID
        cookie_id = str(uuid4())

        # Encrypt cookies
        encrypted = self.encryptor.encrypt(cookies_content)

        # Extract domains from cookies
        domains = self._extract_domains(cookies_content)

        # Create metadata
        metadata = {
            'cookie_id': cookie_id,
            'name': name,
            'browser': browser,
            'domains': domains,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
        }

        # Save encrypted cookies
        cookie_file = self.storage_dir / f"{cookie_id}.enc"
        try:
            with open(cookie_file, 'w') as f:
                json.dump(encrypted, f)
            cookie_file.chmod(0o600)  # Restrict permissions
        except Exception as e:
            logger.error(f"Failed to save encrypted cookies: {e}")
            raise ValidationError(f"Failed to save cookies: {str(e)}")

        # Save metadata
        metadata_file = self.storage_dir / f"{cookie_id}.meta.json"
        try:
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            metadata_file.chmod(0o600)
        except Exception as e:
            logger.error(f"Failed to save cookie metadata: {e}")
            cookie_file.unlink(missing_ok=True)  # Clean up
            raise ValidationError(f"Failed to save metadata: {str(e)}")

        logger.info(f"Saved cookies: {cookie_id} (name: {name}, browser: {browser})")
        return metadata

    def _extract_domains(self, cookies_content: str) -> List[str]:
        """
        Extract unique domains from cookies.

        Args:
            cookies_content: Cookie content in Netscape format

        Returns:
            List of unique domains
        """
        domains = set()
        lines = cookies_content.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split('\t')
            if len(parts) >= 7:
                domain = parts[0].lstrip('.')  # Remove leading dot
                domains.add(domain)

        return sorted(list(domains))

    def get_cookies(self, cookie_id: str) -> str:
        """
        Retrieve and decrypt cookies.

        Args:
            cookie_id: Unique cookie identifier

        Returns:
            Decrypted cookie content

        Raises:
            ValidationError: If cookies not found or decryption fails
        """
        cookie_file = self.storage_dir / f"{cookie_id}.enc"

        if not cookie_file.exists():
            raise ValidationError(f"Cookies not found: {cookie_id}")

        try:
            with open(cookie_file, 'r') as f:
                encrypted = json.load(f)

            decrypted = self.encryptor.decrypt(encrypted)
            logger.debug(f"Retrieved cookies: {cookie_id}")
            return decrypted

        except Exception as e:
            logger.error(f"Failed to retrieve cookies {cookie_id}: {e}")
            raise ValidationError(f"Failed to decrypt cookies: {str(e)}")

    def get_cookies_metadata(self, cookie_id: str) -> Dict[str, any]:
        """
        Get cookie metadata without decrypting content.

        Args:
            cookie_id: Unique cookie identifier

        Returns:
            Cookie metadata dictionary

        Raises:
            ValidationError: If metadata not found
        """
        metadata_file = self.storage_dir / f"{cookie_id}.meta.json"

        if not metadata_file.exists():
            raise ValidationError(f"Cookie metadata not found: {cookie_id}")

        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            return metadata
        except Exception as e:
            logger.error(f"Failed to read metadata for {cookie_id}: {e}")
            raise ValidationError(f"Failed to read metadata: {str(e)}")

    def list_cookies(self) -> List[Dict[str, any]]:
        """
        List all stored cookies (metadata only).

        Returns:
            List of cookie metadata dictionaries
        """
        cookies = []

        for meta_file in self.storage_dir.glob("*.meta.json"):
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                cookies.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to read metadata file {meta_file}: {e}")

        # Sort by creation date (newest first)
        cookies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return cookies

    def delete_cookies(self, cookie_id: str) -> bool:
        """
        Delete cookies and metadata.

        Args:
            cookie_id: Unique cookie identifier

        Returns:
            True if deleted successfully

        Raises:
            ValidationError: If cookies not found
        """
        cookie_file = self.storage_dir / f"{cookie_id}.enc"
        metadata_file = self.storage_dir / f"{cookie_id}.meta.json"

        if not cookie_file.exists() and not metadata_file.exists():
            raise ValidationError(f"Cookies not found: {cookie_id}")

        try:
            cookie_file.unlink(missing_ok=True)
            metadata_file.unlink(missing_ok=True)
            logger.info(f"Deleted cookies: {cookie_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete cookies {cookie_id}: {e}")
            raise ValidationError(f"Failed to delete cookies: {str(e)}")

    def extract_browser_cookies(
        self,
        browser: str,
        name: str = "default",
        profile: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Extract cookies from an installed browser using yt-dlp.

        Args:
            browser: Browser name (chrome, firefox, edge, safari, etc.)
            name: Friendly name for the cookie set
            profile: Browser profile name (optional)

        Returns:
            Dictionary with cookie_id and metadata

        Raises:
            ValidationError: If extraction fails
        """
        import yt_dlp

        browser = browser.lower()
        valid_browsers = ['chrome', 'firefox', 'edge', 'safari', 'brave', 'opera', 'chromium']

        if browser not in valid_browsers:
            raise ValidationError(
                f"Unsupported browser: {browser}. "
                f"Supported browsers: {', '.join(valid_browsers)}"
            )

        # Create temporary file for extracted cookies
        temp_file = None
        try:
            # Use yt-dlp's cookie extraction
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }

            # Build cookies_from_browser string
            if profile:
                cookies_from = f"{browser}:{profile}"
            else:
                cookies_from = browser

            ydl_opts['cookies_from_browser'] = (cookies_from,)

            # Create temporary cookie file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp:
                temp_file = Path(temp.name)
                ydl_opts['cookiefile'] = str(temp_file)

            # Extract cookies using a dummy URL (yt-dlp will extract cookies during setup)
            # We use a reliable URL that won't trigger actual download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # Force cookie extraction by preparing
                    ydl.cookiejar
                except Exception:
                    pass  # May fail but cookies should be extracted

            # Check if cookies were extracted
            if not temp_file.exists() or temp_file.stat().st_size == 0:
                raise ValidationError(
                    f"Failed to extract cookies from {browser}. "
                    "Browser may not be installed or no cookies found."
                )

            # Read extracted cookies
            with open(temp_file, 'r') as f:
                cookies_content = f.read()

            # Validate and save
            result = self.save_cookies(cookies_content, name=name, browser=browser)
            logger.info(f"Extracted cookies from {browser} browser")
            return result

        except yt_dlp.utils.YoutubeDLError as e:
            logger.error(f"yt-dlp cookie extraction failed for {browser}: {e}")
            raise ValidationError(
                f"Failed to extract cookies from {browser}: {str(e)}. "
                "Make sure the browser is installed and has been run at least once."
            )
        except Exception as e:
            logger.error(f"Browser cookie extraction failed for {browser}: {e}")
            raise ValidationError(f"Failed to extract cookies from {browser}: {str(e)}")
        finally:
            # Clean up temporary file
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete temporary cookie file: {e}")

    def get_cookie_file_path(self, cookie_id: str) -> Path:
        """
        Get a temporary file path with decrypted cookies for use with yt-dlp.

        This creates a temporary file that should be cleaned up after use.

        Args:
            cookie_id: Unique cookie identifier

        Returns:
            Path to temporary cookie file

        Raises:
            ValidationError: If cookies not found
        """
        cookies_content = self.get_cookies(cookie_id)

        # Create temporary file with cookies
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            prefix=f'cookies_{cookie_id}_',
            delete=False
        )

        try:
            temp_file.write(cookies_content)
            temp_file.flush()
            temp_path = Path(temp_file.name)
            temp_path.chmod(0o600)  # Restrict permissions
            logger.debug(f"Created temporary cookie file for {cookie_id}: {temp_path}")
            return temp_path
        except Exception as e:
            logger.error(f"Failed to create temporary cookie file: {e}")
            raise ValidationError(f"Failed to create cookie file: {str(e)}")
        finally:
            temp_file.close()


# Singleton instance
_cookie_manager: Optional[CookieManager] = None


def get_cookie_manager() -> CookieManager:
    """
    Get singleton cookie manager instance.

    Returns:
        CookieManager instance
    """
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = CookieManager()
    return _cookie_manager
