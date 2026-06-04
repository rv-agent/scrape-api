"""
Proxy rotation manager with round-robin and health-check based selection.

Supports multiple proxy sources (datacenter, residential, custom).
Rotates proxies automatically and marks failed ones.
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class ProxyType(str, Enum):
    """Proxy types."""
    DATACENTER = "datacenter"
    RESIDENTIAL = "residential"
    CUSTOM = "custom"


@dataclass
class ProxyEntry:
    """A single proxy with health tracking."""
    url: str
    proxy_type: ProxyType = ProxyType.CUSTOM
    is_healthy: bool = True
    fail_count: int = 0
    success_count: int = 0
    last_used: float = 0.0
    last_checked: float = 0.0
    avg_response_time: float = 0.0
    _response_times: List[float] = field(default_factory=list)

    def record_success(self, response_time: float) -> None:
        """Record a successful request."""
        self.is_healthy = True
        self.fail_count = 0
        self.success_count += 1
        self.last_used = time.monotonic()
        self._response_times.append(response_time)
        # Keep last 20 response times for averaging
        if len(self._response_times) > 20:
            self._response_times = self._response_times[-20:]
        self.avg_response_time = sum(self._response_times) / len(self._response_times)

    def record_failure(self) -> None:
        """Record a failed request."""
        self.fail_count += 1
        self.last_used = time.monotonic()
        # Mark unhealthy after 3 consecutive failures
        if self.fail_count >= 3:
            self.is_healthy = False
            logger.warning("Proxy marked unhealthy after %d failures: %s", self.fail_count, self._mask_url())

    def reset_health(self) -> None:
        """Reset proxy health status."""
        self.is_healthy = True
        self.fail_count = 0

    def _mask_url(self) -> str:
        """Mask proxy URL for logging (hide credentials)."""
        if "@" in self.url:
            # user:pass@host:port -> ***@host:port
            parts = self.url.split("@")
            scheme_end = parts[0].rfind("//")
            return f"{parts[0][:scheme_end + 2]}***@{parts[1]}"
        return self.url


class ProxyManager:
    """
    Manages a pool of proxies with rotation strategies.
    
    Strategies:
    - round_robin: cycle through proxies sequentially
    - random: random selection from healthy proxies
    - least_used: select proxy with fewest recent uses (not implemented yet, falls back to round_robin)
    - fastest: select proxy with lowest avg response time (not implemented yet, falls back to round_robin)
    """

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        strategy: str = "round_robin",
        max_fails: int = 3,
        health_check_interval: int = 300,
        health_check_url: str = "https://httpbin.org/ip",
    ):
        self.strategy = strategy
        self.max_fails = max_fails
        self.health_check_interval = health_check_interval
        self.health_check_url = health_check_url
        self._current_index = 0
        self._proxies: List[ProxyEntry] = []

        if proxies:
            for p in proxies:
                self.add_proxy(p)

    def add_proxy(
        self,
        url: str,
        proxy_type: ProxyType = ProxyType.CUSTOM,
    ) -> None:
        """Add a proxy to the pool."""
        # Avoid duplicates
        if any(p.url == url for p in self._proxies):
            logger.debug("Proxy already in pool: %s", url)
            return

        entry = ProxyEntry(url=url, proxy_type=proxy_type)
        self._proxies.append(entry)
        logger.info("Added proxy to pool: type=%s total=%d", proxy_type.value, len(self._proxies))

    def remove_proxy(self, url: str) -> bool:
        """Remove a proxy from the pool."""
        before = len(self._proxies)
        self._proxies = [p for p in self._proxies if p.url != url]
        removed = len(self._proxies) < before
        if removed:
            logger.info("Removed proxy from pool. Remaining: %d", len(self._proxies))
        return removed

    @property
    def proxy_count(self) -> int:
        """Total number of proxies in the pool."""
        return len(self._proxies)

    @property
    def healthy_count(self) -> int:
        """Number of healthy proxies."""
        return sum(1 for p in self._proxies if p.is_healthy)

    def get_proxy(self) -> Optional[str]:
        """
        Get next proxy URL based on the configured strategy.
        
        Returns None if no healthy proxies available.
        """
        healthy = [p for p in self._proxies if p.is_healthy]
        if not healthy:
            if self._proxies:
                # Reset all proxies if none healthy (circuit breaker)
                logger.warning("No healthy proxies — resetting all %d proxies", len(self._proxies))
                for p in self._proxies:
                    p.reset_health()
                healthy = self._proxies
            else:
                return None

        if self.strategy == "random":
            selected = random.choice(healthy)
        elif self.strategy == "fastest":
            selected = min(healthy, key=lambda p: p.avg_response_time if p.avg_response_time > 0 else float('inf'))
        else:
            # round_robin (default)
            self._current_index = self._current_index % len(healthy)
            selected = healthy[self._current_index]
            self._current_index += 1

        logger.debug("Selected proxy: %s (strategy=%s)", selected._mask_url(), self.strategy)
        return selected.url

    def record_success(self, proxy_url: str, response_time: float) -> None:
        """Record successful use of a proxy."""
        for p in self._proxies:
            if p.url == proxy_url:
                p.record_success(response_time)
                break

    def record_failure(self, proxy_url: str) -> None:
        """Record failed use of a proxy."""
        for p in self._proxies:
            if p.url == proxy_url:
                p.record_failure()
                break

    async def check_health(self, proxy_url: Optional[str] = None) -> bool:
        """
        Check if a proxy is healthy by making a test request.
        
        Args:
            proxy_url: Specific proxy to check. If None, checks all.
            
        Returns:
            True if proxy is healthy, False otherwise.
        """
        targets = []
        if proxy_url:
            targets = [p for p in self._proxies if p.url == proxy_url]
        else:
            targets = self._proxies

        results = []
        for proxy_entry in targets:
            # Skip if checked recently
            now = time.monotonic()
            if now - proxy_entry.last_checked < self.health_check_interval:
                results.append(proxy_entry.is_healthy)
                continue

            try:
                start = time.monotonic()
                async with httpx.AsyncClient(timeout=10, proxy=proxy_entry.url) as client:
                    resp = await client.get(self.health_check_url)
                    elapsed = time.monotonic() - start

                if resp.status_code == 200:
                    proxy_entry.is_healthy = True
                    proxy_entry.fail_count = 0
                    proxy_entry.last_checked = now
                    proxy_entry._response_times.append(elapsed)
                    if len(proxy_entry._response_times) > 20:
                        proxy_entry._response_times = proxy_entry._response_times[-20:]
                    proxy_entry.avg_response_time = sum(proxy_entry._response_times) / len(proxy_entry._response_times)
                    results.append(True)
                    logger.debug("Health check OK: %s (%.2fs)", proxy_entry._mask_url(), elapsed)
                else:
                    proxy_entry.is_healthy = False
                    proxy_entry.last_checked = now
                    results.append(False)
                    logger.warning("Health check failed: %s (status=%d)", proxy_entry._mask_url(), resp.status_code)

            except Exception as e:
                proxy_entry.is_healthy = False
                proxy_entry.last_checked = now
                results.append(False)
                logger.warning("Health check error: %s — %s", proxy_entry._mask_url(), str(e))

        return all(results) if results else False

    def get_stats(self) -> Dict:
        """Get proxy pool statistics."""
        return {
            "total": len(self._proxies),
            "healthy": self.healthy_count,
            "unhealthy": len(self._proxies) - self.healthy_count,
            "strategy": self.strategy,
            "proxies": [
                {
                    "url": p._mask_url(),
                    "type": p.proxy_type.value,
                    "healthy": p.is_healthy,
                    "fail_count": p.fail_count,
                    "success_count": p.success_count,
                    "avg_response_time": round(p.avg_response_time, 3),
                }
                for p in self._proxies
            ],
        }

    def __repr__(self) -> str:
        return f"ProxyManager(proxies={len(self._proxies)}, healthy={self.healthy_count}, strategy={self.strategy})"
