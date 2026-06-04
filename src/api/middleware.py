"""
Rate limiting middleware using sliding window algorithm.

Tracks requests per API key in-memory (no Redis dependency for dev).
For production, swap with Redis-backed implementation.
"""

import logging
import time
from collections import defaultdict
from typing import Dict, List

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse

from src.config.settings import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter per API key.

    Tracks requests in a deque of timestamps per key.
    Cleans up expired entries on each check.
    """

    def __init__(self, app, window_seconds: int = 60):
        super().__init__(app)
        self.window_seconds = window_seconds
        # key -> list of timestamps
        self._requests: Dict[str, List[float]] = defaultdict(list)
        # Tier -> max requests per window (burst protection)
        # Daily/monthly quotas are enforced by auth dependency
        self._tier_limits = {
            "free": 60,          # 60 req/min burst
            "starter": 300,      # 300 req/min
            "pro": 1000,         # 1000 req/min
            "enterprise": 5000,  # 5000 req/min
        }

    def _get_client_key(self, request: Request) -> str:
        """Extract API key or client IP for rate limiting."""
        api_key = request.headers.get(settings.API_KEY_HEADER)
        if api_key:
            return f"key:{api_key[:8]}"
        # Fallback to IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _get_tier_from_request(self, request: Request) -> str:
        """Try to determine tier from request state (set by auth)."""
        return getattr(request.state, "tier", "free")

    def _clean_old_entries(self, key: str, now: float) -> None:
        """Remove timestamps outside the window."""
        cutoff = now - self.window_seconds
        entries = self._requests[key]
        i = 0
        while i < len(entries) and entries[i] < cutoff:
            i += 1
        if i > 0:
            self._requests[key] = entries[i:]

    def _check_rate_limit(self, key: str, tier: str) -> tuple:
        """
        Check if request is within rate limit.

        Returns:
            (allowed, remaining, limit)
        """
        now = time.time()
        self._clean_old_entries(key, now)

        limit = self._tier_limits.get(tier, self._tier_limits["free"])
        current = len(self._requests[key])

        if current >= limit:
            return False, 0, limit

        return True, limit - current - 1, limit

    def _record_request(self, key: str) -> None:
        """Record a request timestamp."""
        self._requests[key].append(time.time())

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request through rate limiter."""
        # Skip rate limiting for health checks and docs
        if request.url.path in ("/health", "/health/detailed", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        client_key = self._get_client_key(request)
        tier = self._get_tier_from_request(request)

        allowed, remaining, limit = self._check_rate_limit(client_key, tier)

        if not allowed:
            logger.warning(
                "Rate limit exceeded: client=%s tier=%s limit=%d",
                client_key, tier, limit,
            )
            return Response(
                content=f'{{"detail":"Rate limit exceeded. Max {limit} requests per {self.window_seconds}s window.",'
                        f'"retry_after":{self.window_seconds}}}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + self.window_seconds),
                },
            )

        # Record and proceed
        self._record_request(client_key)
        response = await call_next(request)

        # Collect body from StreamingResponse so we can return a proper Response with headers
        if isinstance(response, StreamingResponse):
            body = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    body += chunk.encode("utf-8")
                else:
                    body += chunk

            new_response = Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
            new_response.headers["X-RateLimit-Limit"] = str(limit)
            new_response.headers["X-RateLimit-Remaining"] = str(remaining)
            new_response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window_seconds)
            return new_response

        # Fallback for non-streaming responses
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window_seconds)
        return response
