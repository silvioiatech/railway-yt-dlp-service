# Ultimate Media Downloader - Test Suite

Comprehensive test suite for the Ultimate Media Downloader with 85%+ coverage target.

## Overview

The test suite is organized into three main categories:

- **Unit Tests** (`tests/unit/`): Fast, isolated tests for individual components
- **Integration Tests** (`tests/integration/`): Tests for API endpoints and service integration
- **E2E Tests** (`tests/e2e/`): End-to-end workflow tests

## Test Structure

```
tests/
├── unit/
│   ├── test_channel_service.py      # Channel service unit tests
│   ├── test_batch_service.py        # Batch service unit tests
│   └── test_cookie_manager.py       # Cookie manager unit tests
├── integration/
│   ├── test_channel_api.py          # Channel API endpoint tests
│   ├── test_batch_api.py            # Batch API endpoint tests
│   └── test_cookies_api.py          # Cookies API endpoint tests
├── e2e/
│   └── test_complete_workflows.py   # End-to-end workflow tests
├── fixtures/
│   ├── channel_response.json        # Sample channel data
│   ├── cookies_netscape.txt         # Sample cookies
│   └── batch_urls.json              # Sample batch URLs
├── conftest.py                       # Shared fixtures
└── README.md                         # This file
```

## Installation

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# E2E tests only
pytest tests/e2e/ -v
```

### Run by Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only e2e tests
pytest -m e2e
```

### Run with Coverage

```bash
# Generate HTML coverage report
pytest tests/ --cov=app --cov-report=html

# Generate terminal coverage report
pytest tests/ --cov=app --cov-report=term-missing

# Both
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
```

### Run Specific Test File

```bash
pytest tests/unit/test_channel_service.py -v
```

### Run Specific Test Function

```bash
pytest tests/unit/test_channel_service.py::test_get_channel_info_basic -v
```

### Run Tests in Parallel

```bash
# Use all CPU cores
pytest tests/ -n auto

# Use specific number of cores
pytest tests/ -n 4
```

## Test Coverage

### Coverage Goals

- **Overall**: 85%+ coverage
- **Unit Tests**: 90%+ per module
- **Integration Tests**: 80%+ API coverage
- **E2E Tests**: All critical paths

### View Coverage Report

After running tests with coverage:

```bash
# Open HTML report
open tests/coverage/html/index.html

# View in terminal
pytest tests/ --cov=app --cov-report=term-missing
```

## Test Features

### Unit Tests

#### `test_channel_service.py`
- Channel info extraction
- Date filtering (date_after, date_before)
- Duration filtering (min_duration, max_duration)
- View count filtering (min_views, max_views)
- Sorting (upload_date, view_count, duration, title)
- Pagination
- Error handling

#### `test_batch_service.py`
- Batch creation with multiple URLs
- Concurrent limit enforcement
- Stop on error vs continue on error
- Batch status calculation
- Batch cancellation
- Job state tracking

#### `test_cookie_manager.py`
- Cookie encryption/decryption (AES-256-GCM)
- Netscape format validation
- Browser cookie extraction (mocked)
- Cookie CRUD operations
- Encryption key generation
- File permissions

### Integration Tests

#### `test_channel_api.py`
- GET `/api/v1/channel/info` endpoint
- POST `/api/v1/channel/download` endpoint
- Filter validation
- Authentication
- Error handling

#### `test_batch_api.py`
- POST `/api/v1/batch/download` endpoint
- GET `/api/v1/batch/{batch_id}` endpoint
- DELETE `/api/v1/batch/{batch_id}` endpoint
- Concurrent downloads
- Error scenarios

#### `test_cookies_api.py`
- POST `/api/v1/cookies` (upload)
- POST `/api/v1/cookies` (browser extraction)
- GET `/api/v1/cookies` (list)
- GET `/api/v1/cookies/{id}` (metadata)
- DELETE `/api/v1/cookies/{id}`
- Integration with downloads

### E2E Tests

#### `test_complete_workflows.py`
- Complete channel download workflow
- Batch download with webhooks
- Download with cookies
- Mixed playlist + channel + batch
- Browser cookie extraction + download
- Error recovery
- Rate limiting
- Pagination
- Quality selection
- Metadata and subtitles

## Fixtures

Shared fixtures are defined in `conftest.py`:

- `auth_headers`: Authentication headers for API tests
- `sample_channel_response`: Mock channel data
- `valid_netscape_cookies`: Sample cookies
- `mock_ytdlp_wrapper`: Mocked yt-dlp wrapper
- `test_client`: HTTP test client

Additional fixtures in `tests/fixtures/`:

- `channel_response.json`: Complete channel extraction response
- `cookies_netscape.txt`: Valid Netscape cookies
- `batch_urls.json`: URL collections for batch testing

## Mocking Strategy

- **yt-dlp**: All yt-dlp operations are mocked to avoid real downloads
- **External APIs**: Webhook endpoints are mocked
- **File System**: Use `tmp_path` fixtures for file operations
- **Time**: Use freezegun for time-dependent tests (when needed)

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Use Fixtures**: Reuse fixtures from `conftest.py`
3. **Mock External Services**: Never make real API calls
4. **Clean Up**: Use `tmp_path` and cleanup fixtures
5. **Async Tests**: Use `@pytest.mark.asyncio` for async tests
6. **Descriptive Names**: Test names should describe what they test
7. **Error Cases**: Test both success and error scenarios

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Install dependencies
  run: pip install -r requirements-test.txt

- name: Run tests with coverage
  run: pytest tests/ --cov=app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests Fail Due to Import Errors

Ensure app is in PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

### Async Tests Fail

Ensure pytest-asyncio is installed:

```bash
pip install pytest-asyncio
```

### Coverage Not Generated

Ensure pytest-cov is installed:

```bash
pip install pytest-cov
```

### Tests Run Slow

Use parallel execution:

```bash
pytest tests/ -n auto
```

## Contributing

When adding new features:

1. Write unit tests first (TDD)
2. Add integration tests for API endpoints
3. Add E2E tests for workflows
4. Ensure coverage stays above 85%
5. Update this README if needed

## Test Statistics

Current test counts (approximate):

- **Unit Tests**: 100+ tests
- **Integration Tests**: 60+ tests
- **E2E Tests**: 15+ tests
- **Total**: 175+ tests

Target execution time:

- Unit tests: < 10 seconds
- Integration tests: < 30 seconds
- E2E tests: < 60 seconds
- Total: < 2 minutes

## Coverage Reports

Coverage reports are generated in:

- `tests/coverage/html/` - HTML report (open `index.html`)
- `tests/coverage/coverage.json` - JSON report
- Terminal output with `--cov-report=term-missing`

## License

Same as main project.
