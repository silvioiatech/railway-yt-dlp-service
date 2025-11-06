# Bug Fixes for Core Modules

This document provides detailed fixes for bugs discovered during comprehensive testing of core modules.

---

## BUG #1: API_KEY Validator Field Order Issue

**File:** `/Users/silvio/Documents/GitHub/railway-yt-dlp-service/app/config.py`  
**Lines:** 32-33, 134-144  
**Severity:** MEDIUM  
**Impact:** Users cannot use empty API_KEY with REQUIRE_API_KEY=false via environment variables

### Problem

The `API_KEY` field (line 32) is defined BEFORE `REQUIRE_API_KEY` (line 33). When pydantic validates fields, they are processed in definition order. The validator for `API_KEY` (lines 134-144) tries to check `info.data.get('REQUIRE_API_KEY', True)`, but at that point, `REQUIRE_API_KEY` hasn't been parsed yet, so it always uses the default value of `True`.

### Current Code

```python
# API Configuration
API_KEY: str = Field(default="", description="API authentication key")
REQUIRE_API_KEY: bool = Field(default=True, description="Enforce API key authentication")

@field_validator('API_KEY')
@classmethod
def validate_api_key(cls, v: str, info) -> str:
    """Validate API key is set when required."""
    require_key = info.data.get('REQUIRE_API_KEY', True)  # Always gets True!
    if require_key and not v:
        raise ValueError(
            "API_KEY must be set when REQUIRE_API_KEY is true. "
            "Set API_KEY environment variable or disable authentication."
        )
    return v
```

### Fix Option 1: Reorder Fields (Simplest)

```python
# API Configuration
REQUIRE_API_KEY: bool = Field(default=True, description="Enforce API key authentication")
API_KEY: str = Field(default="", description="API authentication key")

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
```

### Fix Option 2: Use model_validator (More Robust)

```python
from pydantic import model_validator

# Keep fields in any order
API_KEY: str = Field(default="", description="API authentication key")
REQUIRE_API_KEY: bool = Field(default=True, description="Enforce API key authentication")

# Remove the field_validator for API_KEY and add this:
@model_validator(mode='after')
def validate_api_key_requirement(self) -> 'Settings':
    """Validate API key is set when required."""
    if self.REQUIRE_API_KEY and not self.API_KEY:
        raise ValueError(
            "API_KEY must be set when REQUIRE_API_KEY is true. "
            "Set API_KEY environment variable or disable authentication."
        )
    return self
```

### Fix Option 3: Move to validate_settings() (External Validation)

```python
# Remove the field_validator entirely

# In validate_settings() function (around line 233):
def validate_settings() -> None:
    """Validate settings and raise detailed errors if invalid."""
    try:
        settings = get_settings()

        # ... existing validations ...

        # Add this validation:
        if settings.REQUIRE_API_KEY and not settings.API_KEY:
            raise RuntimeError(
                "API_KEY must be set when REQUIRE_API_KEY is true. "
                "Set API_KEY environment variable or disable authentication."
            )
        
        # ... rest of validations ...
```

### Recommended Fix

**Use Option 1 (Reorder Fields)** - it's the simplest and most pydantic-idiomatic solution.

---

## BUG #2: List Fields Cannot Be Set Via Environment Variables

**File:** `/Users/silvio/Documents/GitHub/railway-yt-dlp-service/app/config.py`  
**Lines:** 93-106 (CORS_ORIGINS), 103-106 (ALLOWED_DOMAINS), 173-191 (validators)  
**Severity:** HIGH  
**Impact:** Cannot configure ALLOWED_DOMAINS or CORS_ORIGINS via environment variables

### Problem

Pydantic-settings v2 attempts to JSON-parse List fields from environment variables before applying validators. When users set:

```bash
export ALLOWED_DOMAINS="youtube.com,vimeo.com"
export CORS_ORIGINS="http://localhost:3000,https://example.com"
```

Pydantic tries to `json.loads()` these values, which fails because they're not valid JSON arrays. The custom validators at lines 173-191 never get called.

### Current Code

```python
CORS_ORIGINS: List[str] = Field(
    default_factory=lambda: ["*"],
    description="Allowed CORS origins"
)

ALLOWED_DOMAINS: List[str] = Field(
    default_factory=list,
    description="Whitelist of allowed domains (empty = all allowed)"
)

@field_validator('CORS_ORIGINS', mode='before')
@classmethod
def parse_cors_origins(cls, v) -> List[str]:
    """Parse CORS origins from string or list."""
    if isinstance(v, str):
        if not v:
            return []
        return [origin.strip() for origin in v.split(',') if origin.strip()]
    return v

@field_validator('ALLOWED_DOMAINS', mode='before')
@classmethod
def parse_allowed_domains(cls, v) -> List[str]:
    """Parse allowed domains from string or list."""
    if isinstance(v, str):
        if not v:
            return []
        return [domain.strip().lower() for domain in v.split(',') if domain.strip()]
    return v
```

### Fix Option 1: Use BeforeValidator with Union Type (Recommended)

```python
from typing import Union
from pydantic import BeforeValidator
from typing_extensions import Annotated

def parse_str_or_list(v: Union[str, List[str]]) -> List[str]:
    """Parse comma-separated string or list into list."""
    if isinstance(v, str):
        if not v:
            return []
        return [item.strip() for item in v.split(',') if item.strip()]
    return v if isinstance(v, list) else []

def parse_str_or_list_lower(v: Union[str, List[str]]) -> List[str]:
    """Parse comma-separated string or list into lowercase list."""
    if isinstance(v, str):
        if not v:
            return []
        return [item.strip().lower() for item in v.split(',') if item.strip()]
    return [item.lower() for item in v] if isinstance(v, list) else []

# Update field definitions
CORS_ORIGINS: Annotated[List[str], BeforeValidator(parse_str_or_list)] = Field(
    default_factory=lambda: ["*"],
    description="Allowed CORS origins (comma-separated string or JSON array)"
)

ALLOWED_DOMAINS: Annotated[List[str], BeforeValidator(parse_str_or_list_lower)] = Field(
    default_factory=list,
    description="Whitelist of allowed domains (comma-separated string or JSON array, empty = all allowed)"
)

# Remove the old field_validator methods for these fields
```

### Fix Option 2: Convert to String Fields with Properties

```python
# Change field types to str
CORS_ORIGINS: str = Field(
    default="*",
    description="Allowed CORS origins (comma-separated)"
)

ALLOWED_DOMAINS: str = Field(
    default="",
    description="Whitelist of allowed domains (comma-separated, empty = all allowed)"
)

# Add properties to access as lists
@property
def cors_origins_list(self) -> List[str]:
    """Get CORS origins as a list."""
    if not self.CORS_ORIGINS:
        return []
    return [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]

@property
def allowed_domains_list(self) -> List[str]:
    """Get allowed domains as a list."""
    if not self.ALLOWED_DOMAINS:
        return []
    return [domain.strip().lower() for domain in self.ALLOWED_DOMAINS.split(',') if domain.strip()]

# Update methods that use these fields
def is_domain_allowed(self, domain: str) -> bool:
    """Check if a domain is allowed."""
    allowed = self.allowed_domains_list  # Use property
    if not allowed:
        return True  # Empty list means all domains allowed

    domain = domain.lower()
    return any(
        allowed_domain in domain or domain in allowed_domain
        for allowed_domain in allowed
    )
```

### Fix Option 3: Use json_schema_extra (Least Invasive)

```python
from pydantic import Field

CORS_ORIGINS: List[str] = Field(
    default_factory=lambda: ["*"],
    description="Allowed CORS origins",
    json_schema_extra={
        "env_parse": "csv"  # Custom marker for our validator
    }
)

ALLOWED_DOMAINS: List[str] = Field(
    default_factory=list,
    description="Whitelist of allowed domains (empty = all allowed)",
    json_schema_extra={
        "env_parse": "csv"
    }
)

# Keep the existing validators but update the Config class:
class Config:
    """Pydantic configuration."""
    env_file = '.env'
    env_file_encoding = 'utf-8'
    case_sensitive = True
    extra = 'ignore'
    
    # Add this to prevent JSON parsing for these fields
    @classmethod
    def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
        if field_name in ('CORS_ORIGINS', 'ALLOWED_DOMAINS'):
            # Return as-is string, let our validator handle it
            return raw_val
        return json.loads(raw_val)
```

### Recommended Fix

**Use Option 1 (BeforeValidator with Union Type)** - it's explicit, type-safe, and works well with pydantic v2.

### Full Implementation for Option 1

```python
from typing import List, Union
from pydantic import BeforeValidator, Field
from typing_extensions import Annotated

# Helper functions
def parse_str_or_list(v: Union[str, List[str]]) -> List[str]:
    """Parse comma-separated string or list into list."""
    if isinstance(v, str):
        if not v:
            return []
        return [item.strip() for item in v.split(',') if item.strip()]
    return v if isinstance(v, list) else []

def parse_str_or_list_lower(v: Union[str, List[str]]) -> List[str]:
    """Parse comma-separated string or list into lowercase list."""
    if isinstance(v, str):
        if not v:
            return []
        return [item.strip().lower() for item in v.split(',') if item.strip()]
    return [item.lower() for item in v] if isinstance(v, list) else []

class Settings(BaseSettings):
    # ... other fields ...
    
    # CORS Configuration
    CORS_ORIGINS: Annotated[List[str], BeforeValidator(parse_str_or_list)] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins (comma-separated string or JSON array)"
    )

    # Feature Flags
    ALLOWED_DOMAINS: Annotated[List[str], BeforeValidator(parse_str_or_list_lower)] = Field(
        default_factory=list,
        description="Whitelist of allowed domains (comma-separated string or JSON array, empty = all allowed)"
    )
    
    # REMOVE these old validators:
    # @field_validator('CORS_ORIGINS', mode='before')
    # @field_validator('ALLOWED_DOMAINS', mode='before')
```

### Testing the Fix

```python
# Test with environment variables
import os
os.environ['ALLOWED_DOMAINS'] = 'youtube.com,vimeo.com'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000,https://example.com'

from app.config import Settings
settings = Settings(REQUIRE_API_KEY=False)

print(settings.ALLOWED_DOMAINS)  # ['youtube.com', 'vimeo.com']
print(settings.CORS_ORIGINS)     # ['http://localhost:3000', 'https://example.com']

# Test with JSON array (still works)
os.environ['ALLOWED_DOMAINS'] = '["youtube.com", "vimeo.com"]'
settings = Settings(REQUIRE_API_KEY=False)
print(settings.ALLOWED_DOMAINS)  # ['youtube.com', 'vimeo.com']
```

---

## Summary

### Apply These Fixes

1. **For BUG #1:** Reorder `REQUIRE_API_KEY` to be before `API_KEY` (5 minute fix)
2. **For BUG #2:** Add `BeforeValidator` with Union types for `ALLOWED_DOMAINS` and `CORS_ORIGINS` (20 minute fix)

### Files to Modify

- `/Users/silvio/Documents/GitHub/railway-yt-dlp-service/app/config.py`

### Total Estimated Time

30 minutes to fix both bugs

### Testing

After applying fixes, run:
```bash
python3 test_core_modules.py
```

Expected result: 47/47 tests passing (100% pass rate)

---

*Generated from comprehensive core modules testing*
