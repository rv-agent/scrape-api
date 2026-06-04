"""
Input validation module for ScrapeAPI.

Validates URLs, CSS selectors, batch sizes, and sanitizes parameters.
Prevents SSRF, injection, and abuse.
"""

import ipaddress
import logging
import re
from typing import Optional
from urllib.parse import urlparse

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Private/internal IP ranges (SSRF protection)
PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 private
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]

# Blocked domains (metadata services, etc.)
BLOCKED_DOMAINS = {
    "metadata.google.internal",
    "169.254.169.254",
    "instance-data",
}

# CSS selector regex (simplified but covers common patterns)
CSS_SELECTOR_PATTERN = re.compile(
    r'^'
    r'[\w\-\.\#\[\]=\"\'\~\|\^\$\*\:\,\>\+\s\(\)]+'
    r'$'
)

# Batch size limits per tier
TIER_BATCH_LIMITS = {
    "free": 5,
    "starter": 20,
    "pro": 50,
    "enterprise": 100,
}

# Dangerous characters for parameter sanitization
DANGEROUS_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


class ValidationError(Exception):
    """Custom validation error with structured details."""

    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def validate_url(url: str, allow_private: bool = False) -> str:
    """
    Validate a URL for safety and correctness.

    Args:
        url: URL string to validate
        allow_private: If True, allow private IPs (for internal use)

    Returns:
        Cleaned URL string

    Raises:
        ValidationError: If URL is invalid or unsafe
    """
    url = url.strip()

    if not url:
        raise ValidationError("EMPTY_URL", "URL cannot be empty")

    # Scheme check
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError(
            "INVALID_SCHEME",
            f"URL scheme must be http or https, got '{parsed.scheme}'",
            {"scheme": parsed.scheme},
        )

    # Domain check
    hostname = parsed.hostname
    if not hostname:
        raise ValidationError("MISSING_HOST", "URL must have a valid hostname")

    # Blocked domains
    if hostname in BLOCKED_DOMAINS:
        raise ValidationError(
            "BLOCKED_DOMAIN",
            f"Domain '{hostname}' is blocked",
            {"hostname": hostname},
        )

    # SSRF protection — check for private IPs
    if not allow_private:
        try:
            ip = ipaddress.ip_address(hostname)
            for network in PRIVATE_NETWORKS:
                if ip in network:
                    raise ValidationError(
                        "PRIVATE_IP",
                        "URL resolves to a private/internal IP address",
                        {"hostname": hostname, "ip": str(ip)},
                    )
        except ValueError:
            # hostname is a domain name, not an IP — that's fine
            pass

    # Check for suspicious patterns
    suspicious_patterns = [
        r'\.\./',          # path traversal
        r'%00',            # null byte
        r'\\',             # backslash
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            raise ValidationError(
                "SUSPICIOUS_URL",
                "URL contains suspicious characters",
                {"pattern": pattern},
            )

    return url


def validate_selector(selector: Optional[str]) -> Optional[str]:
    """
    Validate a CSS selector for syntax safety.

    Args:
        selector: CSS selector string or None

    Returns:
        Cleaned selector or None

    Raises:
        ValidationError: If selector is invalid
    """
    if selector is None:
        return None

    selector = selector.strip()
    if not selector:
        return None

    # Length limit
    if len(selector) > 1000:
        raise ValidationError(
            "SELECTOR_TOO_LONG",
            "CSS selector exceeds maximum length of 1000 characters",
            {"length": len(selector)},
        )

    # Basic syntax check
    if not CSS_SELECTOR_PATTERN.match(selector):
        raise ValidationError(
            "INVALID_SELECTOR",
            "CSS selector contains invalid characters",
            {"selector": selector},
        )

    # Check for dangerous patterns (script injection via selector)
    dangerous = ['<script', 'javascript:', 'onerror', 'onload']
    selector_lower = selector.lower()
    for pattern in dangerous:
        if pattern in selector_lower:
            raise ValidationError(
                "DANGEROUS_SELECTOR",
                "CSS selector contains potentially dangerous content",
                {"selector": selector},
            )

    return selector


def validate_batch_size(urls: list, tier: str = "free") -> int:
    """
    Validate batch request size against tier limits.

    Args:
        urls: List of URLs
        tier: Subscription tier

    Returns:
        Validated batch size

    Raises:
        ValidationError: If batch exceeds tier limit
    """
    limit = TIER_BATCH_LIMITS.get(tier, TIER_BATCH_LIMITS["free"])

    if len(urls) > limit:
        raise ValidationError(
            "BATCH_LIMIT_EXCEEDED",
            f"Batch size {len(urls)} exceeds tier limit of {limit}",
            {"size": len(urls), "limit": limit, "tier": tier},
        )

    return len(urls)


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize a string input by removing dangerous characters.

    Args:
        value: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return value

    # Remove control characters
    value = DANGEROUS_CHARS.sub('', value)

    # Truncate
    if len(value) > max_length:
        value = value[:max_length]

    return value.strip()


def sanitize_headers(headers: Optional[dict]) -> Optional[dict]:
    """
    Sanitize custom HTTP headers.

    Args:
        headers: Dict of header name:value pairs

    Returns:
        Sanitized headers dict or None
    """
    if not headers:
        return None

    sanitized = {}
    blocked_headers = {"host", "content-length", "transfer-encoding", "connection"}

    for key, value in headers.items():
        key = sanitize_string(key, max_length=256).lower()
        value = sanitize_string(value, max_length=4096)

        if key in blocked_headers:
            logger.warning("Blocked header: %s", key)
            continue

        if key and value:
            sanitized[key] = value

    return sanitized if sanitized else None
