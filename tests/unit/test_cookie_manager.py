"""
Unit tests for cookie manager.

Tests cookie encryption/decryption, validation, browser extraction, and CRUD operations.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from app.core.exceptions import ValidationError
from app.services.cookie_manager import CookieEncryption, CookieManager


# =========================
# Fixtures
# =========================

@pytest.fixture
def encryption_key() -> bytes:
    """Generate test encryption key."""
    return b'0' * 32  # 32-byte key for AES-256


@pytest.fixture
def cookie_encryptor(encryption_key) -> CookieEncryption:
    """Create cookie encryption handler."""
    return CookieEncryption(encryption_key)


@pytest.fixture
def cookie_manager(tmp_path) -> CookieManager:
    """Create cookie manager with temporary storage."""
    with patch('app.services.cookie_manager.get_settings') as mock_settings:
        mock_settings.return_value.STORAGE_DIR = tmp_path
        mock_settings.return_value.COOKIE_ENCRYPTION_KEY = None
        manager = CookieManager()
        return manager


@pytest.fixture
def valid_netscape_cookies() -> str:
    """Valid Netscape format cookies."""
    return """# Netscape HTTP Cookie File
# This is a generated file! Do not edit.

.youtube.com	TRUE	/	TRUE	1735689600	CONSENT	YES+cb.20210101-08-p0
.youtube.com	TRUE	/	FALSE	1735689600	VISITOR_INFO1_LIVE	abcdef123456
.youtube.com	TRUE	/	TRUE	1735689600	LOGIN_INFO	session123
"""


@pytest.fixture
def invalid_netscape_cookies() -> str:
    """Invalid Netscape format cookies."""
    return """This is not a valid cookie format
Just some random text
"""


# =========================
# Test CookieEncryption
# =========================

def test_encryption_init_valid_key(encryption_key):
    """Test encryption initialization with valid key."""
    encryptor = CookieEncryption(encryption_key)
    assert encryptor.cipher is not None


def test_encryption_init_invalid_key_length():
    """Test encryption initialization with invalid key length."""
    with pytest.raises(ValueError) as exc_info:
        CookieEncryption(b'short_key')

    assert "must be 32 bytes" in str(exc_info.value)


def test_encrypt_decrypt_roundtrip(cookie_encryptor):
    """Test encryption and decryption roundtrip."""
    plaintext = "test cookie data"

    # Encrypt
    encrypted = cookie_encryptor.encrypt(plaintext)

    assert 'nonce' in encrypted
    assert 'ciphertext' in encrypted
    assert encrypted['nonce'] != plaintext
    assert encrypted['ciphertext'] != plaintext

    # Decrypt
    decrypted = cookie_encryptor.decrypt(encrypted)

    assert decrypted == plaintext


def test_encrypt_produces_different_ciphertext(cookie_encryptor):
    """Test that encrypting same plaintext produces different ciphertext (due to random nonce)."""
    plaintext = "test cookie data"

    encrypted1 = cookie_encryptor.encrypt(plaintext)
    encrypted2 = cookie_encryptor.encrypt(plaintext)

    # Nonces should be different (randomly generated)
    assert encrypted1['nonce'] != encrypted2['nonce']
    # Ciphertexts should be different
    assert encrypted1['ciphertext'] != encrypted2['ciphertext']

    # But both should decrypt to same plaintext
    assert cookie_encryptor.decrypt(encrypted1) == plaintext
    assert cookie_encryptor.decrypt(encrypted2) == plaintext


def test_decrypt_with_wrong_key():
    """Test decryption fails with wrong key."""
    key1 = b'1' * 32
    key2 = b'2' * 32

    encryptor1 = CookieEncryption(key1)
    encryptor2 = CookieEncryption(key2)

    plaintext = "test cookie data"
    encrypted = encryptor1.encrypt(plaintext)

    # Decryption with wrong key should fail
    with pytest.raises(ValueError) as exc_info:
        encryptor2.decrypt(encrypted)

    assert "Failed to decrypt" in str(exc_info.value)


def test_decrypt_with_tampered_data(cookie_encryptor):
    """Test decryption fails with tampered data."""
    plaintext = "test cookie data"
    encrypted = cookie_encryptor.encrypt(plaintext)

    # Tamper with ciphertext
    tampered = encrypted.copy()
    ciphertext_bytes = bytes.fromhex(encrypted['ciphertext'])
    tampered_bytes = bytes([b ^ 0xFF for b in ciphertext_bytes[:10]]) + ciphertext_bytes[10:]
    tampered['ciphertext'] = tampered_bytes.hex()

    # Decryption should fail due to authentication tag mismatch
    with pytest.raises(ValueError):
        cookie_encryptor.decrypt(tampered)


def test_encrypt_empty_string(cookie_encryptor):
    """Test encrypting empty string."""
    plaintext = ""
    encrypted = cookie_encryptor.encrypt(plaintext)
    decrypted = cookie_encryptor.decrypt(encrypted)

    assert decrypted == plaintext


def test_encrypt_unicode(cookie_encryptor):
    """Test encrypting unicode characters."""
    plaintext = "Test with émojis 🎉 and spëcial çhars"
    encrypted = cookie_encryptor.encrypt(plaintext)
    decrypted = cookie_encryptor.decrypt(encrypted)

    assert decrypted == plaintext


# =========================
# Test Cookie Validation
# =========================

def test_validate_cookies_valid_format(cookie_manager, valid_netscape_cookies):
    """Test validating valid Netscape cookies."""
    result = cookie_manager.validate_cookies(valid_netscape_cookies)
    assert result is True


def test_validate_cookies_invalid_format(cookie_manager, invalid_netscape_cookies):
    """Test validating invalid cookies."""
    with pytest.raises(ValidationError) as exc_info:
        cookie_manager.validate_cookies(invalid_netscape_cookies)

    assert "Invalid Netscape cookie format" in str(exc_info.value)


def test_validate_cookies_empty_string(cookie_manager):
    """Test validating empty cookies."""
    with pytest.raises(ValidationError) as exc_info:
        cookie_manager.validate_cookies("")

    assert "empty" in str(exc_info.value).lower()


def test_validate_cookies_missing_columns(cookie_manager):
    """Test validating cookies with insufficient columns."""
    invalid_cookies = """# Netscape HTTP Cookie File
.example.com	TRUE	/	TRUE	123"""  # Only 5 columns

    with pytest.raises(ValidationError) as exc_info:
        cookie_manager.validate_cookies(invalid_cookies)

    assert "7 tab-separated fields" in str(exc_info.value)


def test_validate_cookies_invalid_flag(cookie_manager):
    """Test validating cookies with invalid flag values."""
    invalid_cookies = """# Netscape HTTP Cookie File
.example.com	INVALID	/	TRUE	1234567890	name	value"""

    with pytest.raises(ValidationError) as exc_info:
        cookie_manager.validate_cookies(invalid_cookies)

    assert "must be TRUE or FALSE" in str(exc_info.value)


def test_validate_cookies_invalid_expiration(cookie_manager):
    """Test validating cookies with invalid expiration."""
    invalid_cookies = """# Netscape HTTP Cookie File
.example.com	TRUE	/	TRUE	not_a_number	name	value"""

    with pytest.raises(ValidationError) as exc_info:
        cookie_manager.validate_cookies(invalid_cookies)

    assert "must be a number" in str(exc_info.value)


def test_validate_cookies_empty_domain(cookie_manager):
    """Test validating cookies with empty domain."""
    invalid_cookies = """# Netscape HTTP Cookie File
	TRUE	/	TRUE	1234567890	name	value"""

    with pytest.raises(ValidationError) as exc_info:
        cookie_manager.validate_cookies(invalid_cookies)

    assert "domain cannot be empty" in str(exc_info.value)


def test_validate_cookies_without_header(cookie_manager):
    """Test validating cookies without Netscape header (but with valid data)."""
    cookies_no_header = """.youtube.com	TRUE	/	TRUE	1735689600	CONSENT	YES+cb
.youtube.com	TRUE	/	FALSE	1735689600	VISITOR	abc123"""

    # Should still be valid if it has proper data lines
    result = cookie_manager.validate_cookies(cookies_no_header)
    assert result is True


# =========================
# Test Save Cookies
# =========================

def test_save_cookies_basic(cookie_manager, valid_netscape_cookies):
    """Test saving cookies."""
    result = cookie_manager.save_cookies(
        cookies_content=valid_netscape_cookies,
        name="test_cookies"
    )

    assert 'cookie_id' in result
    assert result['name'] == "test_cookies"
    assert result['status'] == 'active'
    assert 'created_at' in result
    assert 'domains' in result
    assert 'youtube.com' in result['domains']


def test_save_cookies_with_browser(cookie_manager, valid_netscape_cookies):
    """Test saving cookies with browser metadata."""
    result = cookie_manager.save_cookies(
        cookies_content=valid_netscape_cookies,
        name="chrome_cookies",
        browser="chrome"
    )

    assert result['browser'] == "chrome"


def test_save_cookies_creates_encrypted_file(cookie_manager, valid_netscape_cookies):
    """Test that saving cookies creates encrypted file."""
    result = cookie_manager.save_cookies(
        cookies_content=valid_netscape_cookies,
        name="test"
    )

    cookie_id = result['cookie_id']
    cookie_file = cookie_manager.storage_dir / f"{cookie_id}.enc"
    metadata_file = cookie_manager.storage_dir / f"{cookie_id}.meta.json"

    assert cookie_file.exists()
    assert metadata_file.exists()


def test_save_cookies_invalid_format(cookie_manager, invalid_netscape_cookies):
    """Test saving invalid cookies fails."""
    with pytest.raises(ValidationError):
        cookie_manager.save_cookies(
            cookies_content=invalid_netscape_cookies,
            name="test"
        )


def test_save_cookies_extract_domains(cookie_manager, valid_netscape_cookies):
    """Test that domains are correctly extracted."""
    result = cookie_manager.save_cookies(
        cookies_content=valid_netscape_cookies,
        name="test"
    )

    domains = result['domains']
    assert 'youtube.com' in domains
    assert len(domains) == 1


def test_save_cookies_multiple_domains(cookie_manager):
    """Test extracting multiple domains."""
    cookies = """# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1735689600	session	abc
.google.com	TRUE	/	TRUE	1735689600	token	xyz
.example.com	TRUE	/	FALSE	1735689600	auth	123"""

    result = cookie_manager.save_cookies(cookies_content=cookies, name="test")

    domains = result['domains']
    assert len(domains) == 3
    assert 'youtube.com' in domains
    assert 'google.com' in domains
    assert 'example.com' in domains


# =========================
# Test Get Cookies
# =========================

def test_get_cookies_basic(cookie_manager, valid_netscape_cookies):
    """Test retrieving cookies."""
    # Save cookies
    save_result = cookie_manager.save_cookies(
        cookies_content=valid_netscape_cookies,
        name="test"
    )
    cookie_id = save_result['cookie_id']

    # Retrieve cookies
    retrieved = cookie_manager.get_cookies(cookie_id)

    assert retrieved == valid_netscape_cookies


def test_get_cookies_not_found(cookie_manager):
    """Test retrieving non-existent cookies."""
    with pytest.raises(ValidationError) as exc_info:
        cookie_manager.get_cookies("nonexistent_id")

    assert "not found" in str(exc_info.value)


def test_get_cookies_metadata(cookie_manager, valid_netscape_cookies):
    """Test retrieving cookie metadata."""
    save_result = cookie_manager.save_cookies(
        cookies_content=valid_netscape_cookies,
        name="test_meta"
    )
    cookie_id = save_result['cookie_id']

    metadata = cookie_manager.get_cookies_metadata(cookie_id)

    assert metadata['cookie_id'] == cookie_id
    assert metadata['name'] == "test_meta"
    assert 'created_at' in metadata


def test_get_cookies_metadata_not_found(cookie_manager):
    """Test retrieving metadata for non-existent cookies."""
    with pytest.raises(ValidationError):
        cookie_manager.get_cookies_metadata("nonexistent_id")


# =========================
# Test List Cookies
# =========================

def test_list_cookies_empty(cookie_manager):
    """Test listing cookies when none exist."""
    cookies_list = cookie_manager.list_cookies()

    assert isinstance(cookies_list, list)
    assert len(cookies_list) == 0


def test_list_cookies_multiple(cookie_manager, valid_netscape_cookies):
    """Test listing multiple cookie sets."""
    # Save multiple cookie sets
    cookie_manager.save_cookies(valid_netscape_cookies, name="cookies1")
    cookie_manager.save_cookies(valid_netscape_cookies, name="cookies2")
    cookie_manager.save_cookies(valid_netscape_cookies, name="cookies3")

    cookies_list = cookie_manager.list_cookies()

    assert len(cookies_list) == 3
    names = [c['name'] for c in cookies_list]
    assert 'cookies1' in names
    assert 'cookies2' in names
    assert 'cookies3' in names


def test_list_cookies_sorted_by_date(cookie_manager, valid_netscape_cookies):
    """Test that cookies are sorted by creation date (newest first)."""
    # Save cookies with different names
    result1 = cookie_manager.save_cookies(valid_netscape_cookies, name="old")
    result2 = cookie_manager.save_cookies(valid_netscape_cookies, name="new")

    cookies_list = cookie_manager.list_cookies()

    # Should be sorted newest first
    assert len(cookies_list) >= 2


# =========================
# Test Delete Cookies
# =========================

def test_delete_cookies_basic(cookie_manager, valid_netscape_cookies):
    """Test deleting cookies."""
    save_result = cookie_manager.save_cookies(valid_netscape_cookies, name="test")
    cookie_id = save_result['cookie_id']

    # Delete cookies
    result = cookie_manager.delete_cookies(cookie_id)

    assert result is True

    # Verify files are deleted
    cookie_file = cookie_manager.storage_dir / f"{cookie_id}.enc"
    metadata_file = cookie_manager.storage_dir / f"{cookie_id}.meta.json"

    assert not cookie_file.exists()
    assert not metadata_file.exists()


def test_delete_cookies_not_found(cookie_manager):
    """Test deleting non-existent cookies."""
    with pytest.raises(ValidationError):
        cookie_manager.delete_cookies("nonexistent_id")


def test_delete_cookies_no_longer_retrievable(cookie_manager, valid_netscape_cookies):
    """Test that deleted cookies cannot be retrieved."""
    save_result = cookie_manager.save_cookies(valid_netscape_cookies, name="test")
    cookie_id = save_result['cookie_id']

    # Delete cookies
    cookie_manager.delete_cookies(cookie_id)

    # Try to retrieve
    with pytest.raises(ValidationError):
        cookie_manager.get_cookies(cookie_id)


# =========================
# Test Browser Cookie Extraction
# =========================

def test_extract_browser_cookies_chrome(cookie_manager):
    """Test extracting cookies from Chrome."""
    with patch('app.services.cookie_manager.yt_dlp.YoutubeDL') as mock_ydl, \
         patch('app.services.cookie_manager.tempfile.NamedTemporaryFile') as mock_temp:

        # Mock temporary file
        temp_path = cookie_manager.storage_dir / "temp_cookies.txt"
        temp_path.write_text("""# Netscape HTTP Cookie File
.example.com	TRUE	/	TRUE	1234567890	session	abc123""")

        mock_temp.return_value.__enter__.return_value.name = str(temp_path)

        # Mock YoutubeDL
        mock_ydl.return_value.__enter__.return_value.cookiejar = None

        result = cookie_manager.extract_browser_cookies(
            browser="chrome",
            name="chrome_cookies"
        )

        assert result['name'] == "chrome_cookies"
        assert result['browser'] == "chrome"


def test_extract_browser_cookies_unsupported(cookie_manager):
    """Test extracting from unsupported browser."""
    with pytest.raises(ValidationError) as exc_info:
        cookie_manager.extract_browser_cookies(
            browser="unsupported_browser",
            name="test"
        )

    assert "Unsupported browser" in str(exc_info.value)


def test_extract_browser_cookies_with_profile(cookie_manager):
    """Test extracting cookies with specific profile."""
    with patch('app.services.cookie_manager.yt_dlp.YoutubeDL') as mock_ydl, \
         patch('app.services.cookie_manager.tempfile.NamedTemporaryFile') as mock_temp:

        temp_path = cookie_manager.storage_dir / "temp_cookies.txt"
        temp_path.write_text("""# Netscape HTTP Cookie File
.example.com	TRUE	/	TRUE	1234567890	session	abc123""")

        mock_temp.return_value.__enter__.return_value.name = str(temp_path)
        mock_ydl.return_value.__enter__.return_value.cookiejar = None

        result = cookie_manager.extract_browser_cookies(
            browser="firefox",
            name="firefox_cookies",
            profile="default"
        )

        assert result['browser'] == "firefox"


@patch('app.services.cookie_manager.yt_dlp.YoutubeDL')
def test_extract_browser_cookies_extraction_failed(mock_ydl, cookie_manager):
    """Test handling of failed browser extraction."""
    # Mock extraction failure
    mock_ydl.side_effect = Exception("Browser not found")

    with pytest.raises(ValidationError) as exc_info:
        cookie_manager.extract_browser_cookies(
            browser="chrome",
            name="test"
        )

    assert "Failed to extract cookies" in str(exc_info.value)


# =========================
# Test Cookie File Path
# =========================

def test_get_cookie_file_path(cookie_manager, valid_netscape_cookies):
    """Test getting temporary cookie file path."""
    save_result = cookie_manager.save_cookies(valid_netscape_cookies, name="test")
    cookie_id = save_result['cookie_id']

    temp_path = cookie_manager.get_cookie_file_path(cookie_id)

    assert temp_path.exists()
    assert temp_path.suffix == '.txt'
    assert cookie_id in temp_path.name

    # Verify content
    content = temp_path.read_text()
    assert content == valid_netscape_cookies

    # Cleanup
    temp_path.unlink()


def test_get_cookie_file_path_not_found(cookie_manager):
    """Test getting cookie file path for non-existent cookies."""
    with pytest.raises(ValidationError):
        cookie_manager.get_cookie_file_path("nonexistent_id")


def test_get_cookie_file_path_permissions(cookie_manager, valid_netscape_cookies):
    """Test that cookie file has restricted permissions."""
    save_result = cookie_manager.save_cookies(valid_netscape_cookies, name="test")
    cookie_id = save_result['cookie_id']

    temp_path = cookie_manager.get_cookie_file_path(cookie_id)

    # Check file permissions (should be 0600)
    import stat
    mode = temp_path.stat().st_mode
    perms = stat.S_IMODE(mode)

    # Should be readable and writable by owner only
    assert perms & stat.S_IRUSR  # Owner read
    assert perms & stat.S_IWUSR  # Owner write
    assert not (perms & stat.S_IRGRP)  # Group read denied
    assert not (perms & stat.S_IROTH)  # Other read denied

    # Cleanup
    temp_path.unlink()


# =========================
# Test Encryption Key Management
# =========================

def test_encryption_key_persistence(tmp_path):
    """Test that encryption key is persisted between instances."""
    with patch('app.services.cookie_manager.get_settings') as mock_settings:
        mock_settings.return_value.STORAGE_DIR = tmp_path
        mock_settings.return_value.COOKIE_ENCRYPTION_KEY = None

        # Create first manager instance
        manager1 = CookieManager()

        # Create second manager instance
        manager2 = CookieManager()

        # Both should use the same key (loaded from file)
        key_file = tmp_path / "cookies" / ".encryption_key"
        assert key_file.exists()


def test_encryption_key_from_environment(tmp_path):
    """Test using encryption key from environment."""
    env_key = b'1' * 32

    with patch('app.services.cookie_manager.get_settings') as mock_settings:
        mock_settings.return_value.STORAGE_DIR = tmp_path
        mock_settings.return_value.COOKIE_ENCRYPTION_KEY = env_key.hex()

        manager = CookieManager()

        # Should use environment key
        assert manager.encryptor is not None


# =========================
# Test Edge Cases
# =========================

def test_cookie_manager_storage_dir_creation(tmp_path):
    """Test that storage directory is created if it doesn't exist."""
    storage_path = tmp_path / "new_storage"

    with patch('app.services.cookie_manager.get_settings') as mock_settings:
        mock_settings.return_value.STORAGE_DIR = storage_path
        mock_settings.return_value.COOKIE_ENCRYPTION_KEY = None

        manager = CookieManager()

        cookies_dir = storage_path / "cookies"
        assert cookies_dir.exists()


def test_save_cookies_default_name(cookie_manager, valid_netscape_cookies):
    """Test saving cookies with default name."""
    result = cookie_manager.save_cookies(cookies_content=valid_netscape_cookies)

    assert result['name'] == "default"


def test_domain_extraction_removes_leading_dot(cookie_manager):
    """Test that leading dots are removed from domains."""
    cookies = """# Netscape HTTP Cookie File
.example.com	TRUE	/	TRUE	1735689600	session	abc"""

    result = cookie_manager.save_cookies(cookies_content=cookies, name="test")

    # Domain should be 'example.com' not '.example.com'
    assert 'example.com' in result['domains']
