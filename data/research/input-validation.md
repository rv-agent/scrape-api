# Input Validation Best Practices

## URL Validation
```python
from urllib.parse import urlparse
from pydantic import field_validator

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "metadata.google.internal"}
BLOCKED_NETWORKS = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16"]

@field_validator("url")
@classmethod
def validate_url(cls, v):
    parsed = urlparse(v)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("URL must use http or https scheme")
    if not parsed.netloc:
        raise ValueError("URL must have a valid domain")
    if parsed.hostname in BLOCKED_HOSTS:
        raise ValueError("URL targets a blocked host")
    # Check against private IP ranges (SSRF prevention)
    import ipaddress
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        for network in BLOCKED_NETWORKS:
            if ip in ipaddress.ip_network(network):
                raise ValueError("URL targets a private network")
    except ValueError:
        pass  # hostname is a domain, not IP — DNS resolution check at request time
    return v
```

## SSRF Prevention
- Resolve DNS at request time, verify resolved IP not in private ranges
- Use `httpx` with `follow_redirects=False` then manually verify redirect targets
- Timeout: 30s max per request
- Block cloud metadata endpoints (169.254.169.254)

## CSS Selector Validation
```python
import re
SELECTOR_PATTERN = re.compile(r'^[a-zA-Z0-9\s\.\#\[\]\=\:\-\_\+\~\>\*\,"']+$')

@field_validator("selector")
@classmethod
def validate_selector(cls, v):
    if not SELECTOR_PATTERN.match(v):
        raise ValueError("Invalid CSS selector")
    if len(v) > 500:
        raise ValueError("Selector too long (max 500 chars)")
    return v
```

## Batch Size Limits
```python
TIER_LIMITS = {"free": 5, "starter": 20, "pro": 50, "enterprise": 200}

@field_validator("urls")
@classmethod
def validate_batch_size(cls, v):
    if len(v) > 200:
        raise ValueError("Max 200 URLs per batch")
    if len(v) == 0:
        raise ValueError("At least 1 URL required")
    return v
```

## Parameter Sanitization
- Strip whitespace from all string inputs
- Lowercase domain names
- Normalize URLs (remove trailing slash, default ports)
- Limit string field lengths: URL=2048, selector=500, callback_url=2048

## Request Body Size
```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 1_048_576:  # 1MB
            return JSONResponse(status_code=413, content={"error": {"code": "BODY_TOO_LARGE"}})
        return await call_next(request)
```

## File Upload Validation (future)
- Content-type whitelist
- Magic byte verification
- Size limits per tier
- Virus scanning integration
