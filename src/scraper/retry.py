"""
Retry mechanism with exponential backoff and jitter.

Provides a decorator and standalone retry function for handling
transient failures in scraping operations.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Callable, Optional, Set, Tuple, Type, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0         # seconds
    max_delay: float = 30.0         # seconds
    exponential_base: float = 2.0   # backoff multiplier
    jitter: bool = True             # add random jitter to prevent thundering herd
    retryable_status_codes: Tuple[int, ...] = (408, 429, 500, 502, 503, 504)
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )

    def __post_init__(self):
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")


def calculate_delay(
    attempt: int,
    config: RetryConfig,
    retry_after: Optional[float] = None,
) -> float:
    """
    Calculate delay for a given retry attempt.
    
    Args:
        attempt: Current attempt number (0-based)
        config: Retry configuration
        retry_after: Server-suggested retry-after seconds (from 429 response)
        
    Returns:
        Delay in seconds
    """
    # Respect server's Retry-After header if present
    if retry_after is not None and retry_after > 0:
        return min(retry_after, config.max_delay)

    # Exponential backoff: base * (exp_base ^ attempt)
    delay = config.base_delay * (config.exponential_base ** attempt)

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter: ±25% of delay
    if config.jitter:
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
        # Ensure non-negative
        delay = max(0.1, delay)

    return delay


def is_retryable_exception(exc: Exception, config: RetryConfig) -> bool:
    """Check if an exception is retryable."""
    # Check httpx-specific exceptions
    exc_name = type(exc).__name__
    if exc_name in ("TimeoutException", "ConnectTimeout", "ReadTimeout", "PoolTimeout"):
        return True

    # Check httpx status code exception
    resp = getattr(exc, "response", None)
    if resp is not None:
        status = getattr(resp, "status_code", None)
        if status is not None and status in config.retryable_status_codes:
            return True

    # Check standard exceptions
    return isinstance(exc, config.retryable_exceptions)


def is_retryable_status(status_code: int, config: RetryConfig) -> bool:
    """Check if an HTTP status code is retryable."""
    return status_code in config.retryable_status_codes


def get_retry_after(exc_or_headers: Any) -> Optional[float]:
    """
    Extract Retry-After value from exception response or headers.
    
    Args:
        exc_or_headers: Exception with response or dict of headers
        
    Returns:
        Retry-After in seconds, or None
    """
    headers = None

    if isinstance(exc_or_headers, dict):
        headers = exc_or_headers
    elif hasattr(exc_or_headers, "response"):
        resp = getattr(exc_or_headers, "response", None)
        if resp is not None:
            headers = getattr(resp, "headers", None)

    if headers is None:
        return None

    retry_after = headers.get("retry-after") or headers.get("Retry-After")
    if retry_after is None:
        return None

    try:
        # Retry-After can be seconds (integer) or HTTP date
        return float(retry_after)
    except (ValueError, TypeError):
        return None


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    **kwargs,
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration (uses defaults if None)
        on_retry: Callback called on each retry (attempt, exception, delay)
        **kwargs: Keyword arguments for func
        
    Returns:
        Result of func
        
    Raises:
        The last exception if all retries exhausted
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.info(
                    "Succeeded after %d retries: %s",
                    attempt, func.__name__ if hasattr(func, '__name__') else 'func',
                )
            return result

        except Exception as exc:
            last_exception = exc

            # Check if retryable
            if not is_retryable_exception(exc, config):
                logger.error(
                    "Non-retryable error (attempt %d/%d): %s: %s",
                    attempt + 1, config.max_retries + 1,
                    type(exc).__name__, str(exc),
                )
                raise

            # Don't sleep on last attempt
            if attempt >= config.max_retries:
                break

            # Calculate delay
            retry_after = get_retry_after(exc)
            delay = calculate_delay(attempt, config, retry_after)

            logger.warning(
                "Retryable error (attempt %d/%d): %s: %s — retrying in %.2fs",
                attempt + 1, config.max_retries + 1,
                type(exc).__name__, str(exc), delay,
            )

            # Callback
            if on_retry:
                on_retry(attempt, exc, delay)

            await asyncio.sleep(delay)

    # All retries exhausted
    logger.error(
        "All %d retries exhausted: %s",
        config.max_retries + 1,
        type(last_exception).__name__ if last_exception else "Unknown",
    )
    raise last_exception  # type: ignore[misc]


class RetryHandler:
    """
    Reusable retry handler with configuration.
    
    Usage:
        retry = RetryHandler(max_retries=3, base_delay=1.0)
        result = await retry.execute(some_async_func, arg1, arg2)
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_status_codes: Optional[Tuple[int, ...]] = None,
    ):
        self.config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            retryable_status_codes=retryable_status_codes or (408, 429, 500, 502, 503, 504),
        )
        self._retry_count = 0
        self._total_retry_time = 0.0

    async def execute(
        self,
        func: Callable[..., T],
        *args,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
        **kwargs,
    ) -> T:
        """Execute a function with retry."""
        start = time.monotonic()
        try:
            result = await retry_async(func, *args, config=self.config, on_retry=on_retry, **kwargs)
            return result
        finally:
            elapsed = time.monotonic() - start
            if elapsed > self.config.base_delay:
                self._total_retry_time += elapsed

    @property
    def stats(self) -> dict:
        """Get retry statistics."""
        return {
            "total_retry_time": round(self._total_retry_time, 3),
            "config": {
                "max_retries": self.config.max_retries,
                "base_delay": self.config.base_delay,
                "max_delay": self.config.max_delay,
                "exponential_base": self.config.exponential_base,
                "jitter": self.config.jitter,
            },
        }

    def __repr__(self) -> str:
        return f"RetryHandler(max_retries={self.config.max_retries}, base_delay={self.config.base_delay})"
