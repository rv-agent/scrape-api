"""
Security hardening middleware for ScrapeAPI.

Implements OWASP API Security Top 10 protections:
- Rate limiting (already in middleware.py)
- Input validation (already in validation.py)
- Security headers
- Request size limits
- IP allowlisting/blocklisting
"""

import logging
import time
from typing import Callable, Optional, Set

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.config.settings import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # OWASP recommended headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS."""

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > self.max_size:
                return Response(
                    content='{"error":{"code":"PAYLOAD_TOO_LARGE","message":"Request body too large"}}',
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    media_type="application/json",
                )

        return await call_next(request)


class IPFilterMiddleware(BaseHTTPMiddleware):
    """IP allowlist/blocklist middleware."""

    def __init__(
        self,
        app,
        blocked_ips: Optional[Set[str]] = None,
        allowed_ips: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.blocked_ips = blocked_ips or set()
        self.allowed_ips = allowed_ips  # None means allow all

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = self._get_client_ip(request)

        # Check blocklist
        if client_ip in self.blocked_ips:
            logger.warning("Blocked IP: %s", client_ip)
            return Response(
                content='{"error":{"code":"IP_BLOCKED","message":"Access denied"}}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json",
            )

        # Check allowlist (if configured)
        if self.allowed_ips is not None and client_ip not in self.allowed_ips:
            logger.warning("IP not in allowlist: %s", client_ip)
            return Response(
                content='{"error":{"code":"IP_NOT_ALLOWED","message":"Access denied"}}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json",
            )

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing and status."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.time()

        # Get client info
        client_ip = request.headers.get("X-Forwarded-For", "")
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"

        api_key = request.headers.get(settings.API_KEY_HEADER, "none")[:8]

        response = await call_next(request)

        elapsed = (time.time() - start) * 1000

        logger.info(
            "%s %s → %d (%.1fms) client=%s key=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
            client_ip,
            api_key,
        )

        return response
