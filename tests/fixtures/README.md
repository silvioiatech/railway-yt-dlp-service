# Test Fixtures

This directory contains test fixture data used across the test suite.

## Files

### channel_response.json
Mock yt-dlp channel extraction response with sample videos. Used for testing channel info extraction, filtering, sorting, and pagination.

**Contents:**
- Channel metadata (id, name, subscriber count, etc.)
- 5 sample video entries with various durations, view counts, and upload dates
- Useful for testing date/duration/view filters

### cookies_netscape.txt
Sample cookies in Netscape format for testing cookie upload, encryption, and usage.

**Contents:**
- YouTube domain cookies with various types (session, preferences, authentication)
- Properly formatted according to Netscape cookie file specification
- Safe for testing (no real credentials)

### batch_urls.json
Collections of URLs for testing batch download functionality.

**Collections:**
- `test_batch_small`: 3 URLs for basic batch testing
- `test_batch_medium`: 10 URLs for testing moderate concurrency
- `test_batch_large`: 20 URLs for stress testing
- `test_batch_mixed_platforms`: URLs from different platforms
- `test_batch_with_invalid`: Mix of valid and invalid URLs for error handling

## Usage

Load fixtures in tests using the `load_fixture_json` fixture from conftest.py:

```python
def test_something(load_fixture_json):
    channel_data = load_fixture_json('channel_response.json')
    assert channel_data['channel_id'] == 'UC_fixture_channel'
```

For cookie files, read directly:

```python
def test_cookies():
    fixture_path = Path(__file__).parent / 'fixtures' / 'cookies_netscape.txt'
    cookies = fixture_path.read_text()
```

## Notes

- These fixtures are for testing only and contain no real credentials
- Update fixtures when adding new test scenarios
- Keep fixture data realistic but minimal for fast test execution
