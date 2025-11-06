# Authentication & Cookie Management Guide

Complete guide to managing cookies for accessing private and members-only content.

## Overview

The cookie management system allows you to:

- **Upload cookies** in Netscape format
- **Auto-extract cookies** from installed browsers
- **Securely store** cookies with AES-256-GCM encryption
- **Use cookies** in download requests for authenticated content
- **Manage multiple** cookie profiles

## Use Cases

- Download private or unlisted videos
- Access members-only content (Patreon, YouTube memberships)
- Download age-restricted content
- Access region-locked content
- Download from platforms requiring authentication

## Cookie Upload Methods

### Method 1: Browser Extraction (Recommended)

Automatically extract cookies from installed browsers:

```bash
curl -X POST http://localhost:8080/api/v1/cookies \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "browser": "chrome",
    "name": "my_chrome_cookies"
  }'
```

**Supported Browsers**:
- Chrome
- Firefox
- Edge
- Safari
- Brave
- Opera
- Chromium

**With Profile**:
```json
{
  "browser": "firefox",
  "name": "firefox_work",
  "profile": "work-profile"
}
```

### Method 2: Manual Upload

Upload cookies exported in Netscape format:

```bash
curl -X POST http://localhost:8080/api/v1/cookies \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t1234567890\tSESSION\tabc123",
    "name": "youtube_cookies"
  }'
```

## Exporting Cookies

### Using Browser Extensions

#### Chrome/Edge/Brave

1. Install "Get cookies.txt LOCALLY" extension
2. Navigate to the site you're logged into
3. Click extension icon
4. Click "Export" button
5. Save cookies.txt file

#### Firefox

1. Install "cookies.txt" extension
2. Navigate to the site
3. Click extension icon
4. Click "Download" button

### Using Python

```python
import browser_cookie3

# Extract cookies from Chrome
cookies = browser_cookie3.chrome(domain_name='youtube.com')

# Save to Netscape format
with open('cookies.txt', 'w') as f:
    for cookie in cookies:
        f.write(f"{cookie.domain}\t")
        f.write(f"{'TRUE' if cookie.domain.startswith('.') else 'FALSE'}\t")
        f.write(f"{cookie.path}\t")
        f.write(f"{'TRUE' if cookie.secure else 'FALSE'}\t")
        f.write(f"{int(cookie.expires) if cookie.expires else 0}\t")
        f.write(f"{cookie.name}\t")
        f.write(f"{cookie.value}\n")
```

## Python Examples

### Complete Cookie Manager

```python
import requests
from typing import Dict, List, Optional

class CookieManager:
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base
        self.headers = {"X-API-Key": api_key}

    def extract_from_browser(
        self,
        browser: str,
        name: str = "default",
        profile: Optional[str] = None
    ) -> Dict:
        """Extract cookies from browser."""
        payload = {
            "browser": browser,
            "name": name
        }
        if profile:
            payload["profile"] = profile

        response = requests.post(
            f"{self.api_base}/api/v1/cookies",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def upload_cookies(
        self,
        cookies_content: str,
        name: str = "default"
    ) -> Dict:
        """Upload cookies in Netscape format."""
        response = requests.post(
            f"{self.api_base}/api/v1/cookies",
            headers=self.headers,
            json={
                "cookies": cookies_content,
                "name": name
            }
        )
        response.raise_for_status()
        return response.json()

    def list_cookies(self) -> List[Dict]:
        """List all stored cookies."""
        response = requests.get(
            f"{self.api_base}/api/v1/cookies",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["cookies"]

    def get_cookie(self, cookie_id: str) -> Dict:
        """Get cookie metadata."""
        response = requests.get(
            f"{self.api_base}/api/v1/cookies/{cookie_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def delete_cookie(self, cookie_id: str) -> Dict:
        """Delete stored cookies."""
        response = requests.delete(
            f"{self.api_base}/api/v1/cookies/{cookie_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
manager = CookieManager("http://localhost:8080", "your-api-key")

# Extract from Chrome
result = manager.extract_from_browser("chrome", "youtube_cookies")
cookie_id = result["cookie_id"]

# Or upload from file
with open('cookies.txt', 'r') as f:
    cookies = f.read()
result = manager.upload_cookies(cookies, "youtube_manual")
cookie_id = result["cookie_id"]

# List all cookies
all_cookies = manager.list_cookies()
for cookie in all_cookies:
    print(f"{cookie['name']}: {cookie['domains']}")
```

### Using Cookies in Downloads

```python
# 1. Upload or extract cookies
cookie_response = manager.extract_from_browser("chrome", "youtube")
cookie_id = cookie_response["cookie_id"]

# 2. Use cookies in download
response = requests.post(
    f"{api_base}/api/v1/download",
    headers={"X-API-Key": api_key},
    json={
        "url": "https://youtube.com/watch?v=private_video",
        "cookies_id": cookie_id,
        "quality": "1080p"
    }
)

request_id = response.json()["request_id"]
```

### Automatic Cookie Management

```python
class AuthenticatedDownloader:
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base
        self.api_key = api_key
        self.cookie_manager = CookieManager(api_base, api_key)
        self.cookie_cache = {}

    def get_or_create_cookies(self, domain: str, browser: str = "chrome") -> str:
        """Get cookies for domain, create if not exists."""
        # Check cache
        if domain in self.cookie_cache:
            return self.cookie_cache[domain]

        # Check existing cookies
        existing = self.cookie_manager.list_cookies()
        for cookie in existing:
            if any(domain in d for d in cookie['domains']):
                cookie_id = cookie['cookie_id']
                self.cookie_cache[domain] = cookie_id
                return cookie_id

        # Create new cookies
        result = self.cookie_manager.extract_from_browser(
            browser,
            f"{domain}_cookies"
        )
        cookie_id = result['cookie_id']
        self.cookie_cache[domain] = cookie_id
        return cookie_id

    def download_with_auth(self, url: str, **kwargs):
        """Download with automatic cookie management."""
        # Extract domain
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        # Get cookies for domain
        cookie_id = self.get_or_create_cookies(domain)

        # Download with cookies
        response = requests.post(
            f"{self.api_base}/api/v1/download",
            headers={"X-API-Key": self.api_key},
            json={
                "url": url,
                "cookies_id": cookie_id,
                **kwargs
            }
        )
        return response.json()

# Usage
downloader = AuthenticatedDownloader("http://localhost:8080", "your-api-key")

# Automatically manages cookies
result = downloader.download_with_auth(
    "https://youtube.com/watch?v=members_only",
    quality="1080p"
)
```

## Cookie Response Format

### Upload Response

```json
{
  "cookie_id": "cookie_abc123",
  "name": "youtube_cookies",
  "created_at": "2025-11-06T10:00:00Z",
  "browser": "chrome",
  "domains": [".youtube.com", ".google.com"],
  "status": "active"
}
```

### List Response

```json
{
  "cookies": [
    {
      "cookie_id": "cookie_abc123",
      "name": "youtube_cookies",
      "created_at": "2025-11-06T10:00:00Z",
      "browser": "chrome",
      "domains": [".youtube.com"],
      "status": "active"
    }
  ],
  "total": 1
}
```

## Security

### Encryption

All cookies are encrypted at rest using AES-256-GCM:

```python
# Cookie encryption is automatic
# Keys are stored securely in STORAGE_DIR/cookies/.encryption_key
```

### Generate Encryption Key

```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"

# Add to .env
COOKIE_ENCRYPTION_KEY=<generated-key>
```

### Access Control

- Cookies require API key authentication
- Each user's cookies are isolated
- No cross-user cookie access

## Best Practices

### 1. Use Browser Extraction

Prefer automatic browser extraction over manual upload:

```python
# Good - automatic and secure
result = manager.extract_from_browser("chrome", "youtube")

# OK but less convenient - requires manual export
with open('cookies.txt') as f:
    result = manager.upload_cookies(f.read(), "youtube")
```

### 2. Organize by Purpose

Use meaningful cookie names:

```python
# Good - descriptive names
manager.extract_from_browser("chrome", "youtube_main_account")
manager.extract_from_browser("firefox", "patreon_premium")

# Bad - unclear names
manager.extract_from_browser("chrome", "cookies1")
manager.extract_from_browser("chrome", "test")
```

### 3. Refresh Cookies Periodically

Cookies expire - refresh them regularly:

```python
# Check cookie age
cookie = manager.get_cookie(cookie_id)
created = datetime.fromisoformat(cookie['created_at'])

# Refresh if older than 7 days
if (datetime.now() - created).days > 7:
    # Delete old
    manager.delete_cookie(cookie_id)
    # Extract new
    result = manager.extract_from_browser("chrome", cookie['name'])
    cookie_id = result['cookie_id']
```

### 4. Clean Up Unused Cookies

Remove cookies you no longer need:

```python
# List all cookies
cookies = manager.list_cookies()

# Delete old or unused
for cookie in cookies:
    created = datetime.fromisoformat(cookie['created_at'])
    if (datetime.now() - created).days > 30:
        manager.delete_cookie(cookie['cookie_id'])
        print(f"Deleted old cookie: {cookie['name']}")
```

## Common Issues

### Issue: Browser extraction fails

**Cause**: Browser not installed or running as root

**Solutions**:
1. Ensure browser is installed
2. Don't run service as root
3. Try manual cookie export instead

```python
# Fallback to manual upload
with open('cookies.txt') as f:
    result = manager.upload_cookies(f.read(), "manual")
```

### Issue: Download still fails with cookies

**Cause**: Cookies expired or insufficient permissions

**Solutions**:
1. Re-extract fresh cookies
2. Ensure you're logged into the service in your browser
3. Check that your account has access to the content

### Issue: Wrong cookies being used

**Cause**: Multiple cookie sets for same domain

**Solution**: Use specific cookie_id, not automatic selection

```python
# Explicit cookie selection
response = requests.post(
    f"{api_base}/api/v1/download",
    headers={"X-API-Key": api_key},
    json={
        "url": url,
        "cookies_id": "cookie_abc123"  # Specific cookie set
    }
)
```

## Cookie Validation

### Netscape Format

Valid Netscape cookie format:

```
# Netscape HTTP Cookie File
.youtube.com    TRUE    /    TRUE    1699267200    CONSENT    YES+1
.youtube.com    TRUE    /    FALSE    1699267200    VISITOR_INFO1_LIVE    abc123
```

Format: `domain flag path secure expiration name value`

### Validation in Python

```python
def validate_netscape_cookies(cookies_content: str) -> bool:
    """Validate Netscape cookie format."""
    lines = cookies_content.strip().split('\n')

    has_header = False
    has_data = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('#'):
            has_header = True
            continue

        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 7:
                has_data = True

    return has_header or has_data
```

## CLI Tool

### Cookie Management Script

```python
#!/usr/bin/env python3
import click
import requests

@click.group()
def cli():
    """Cookie management CLI."""
    pass

@cli.command()
@click.option('--browser', required=True)
@click.option('--name', required=True)
def extract(browser, name):
    """Extract cookies from browser."""
    manager = CookieManager(API_BASE, API_KEY)
    result = manager.extract_from_browser(browser, name)
    click.echo(f"Created: {result['cookie_id']}")

@cli.command()
def list():
    """List all cookies."""
    manager = CookieManager(API_BASE, API_KEY)
    cookies = manager.list_cookies()
    for cookie in cookies:
        click.echo(f"{cookie['cookie_id']}: {cookie['name']} ({', '.join(cookie['domains'])})")

@cli.command()
@click.argument('cookie_id')
def delete(cookie_id):
    """Delete cookies."""
    manager = CookieManager(API_BASE, API_KEY)
    manager.delete_cookie(cookie_id)
    click.echo(f"Deleted: {cookie_id}")

if __name__ == '__main__':
    cli()
```

Usage:
```bash
# Extract cookies
python cookie_tool.py extract --browser chrome --name youtube

# List cookies
python cookie_tool.py list

# Delete cookies
python cookie_tool.py delete cookie_abc123
```

## Related Guides

- [API Reference](../api/API_REFERENCE_COMPLETE.md)
- [Quick Start Guide](../QUICKSTART.md)
- [Channel Downloads](CHANNEL_DOWNLOADS.md)

---

**Last Updated**: 2025-11-06
