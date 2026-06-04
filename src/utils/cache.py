"""
Redis caching layer for ScrapeAPI.

Provides cache-aside pattern for scrape results.
Reduces duplicate scrape requests and improves response times.
"""

import hashlib
import json
import logging
from typing import Optional

import redis.asyncio as redis

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            # Test connection
            await _redis_client.ping()
            logger.info("Redis connected: %s", settings.REDIS_URL)
        except Exception as e:
            logger.warning("Redis not available: %s — caching disabled", str(e))
            _redis_client = None
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


def _cache_key(url: str, selector: Optional[str] = None, render_js: bool = False) -> str:
    """Generate cache key from scrape parameters."""
    key_parts = f"{url}|{selector or ''}|{render_js}"
    key_hash = hashlib.sha256(key_parts.encode()).hexdigest()[:16]
    return f"scrape:result:{key_hash}"


async def get_cached(url: str, selector: Optional[str] = None, render_js: bool = False) -> Optional[dict]:
    """
    Get cached scrape result.

    Args:
        url: Target URL
        selector: CSS selector
        render_js: JS rendering flag

    Returns:
        Cached result dict or None
    """
    r = await get_redis()
    if not r:
        return None

    key = _cache_key(url, selector, render_js)
    try:
        cached = await r.get(key)
        if cached:
            logger.debug("Cache HIT: %s", key)
            return json.loads(cached)
        logger.debug("Cache MISS: %s", key)
        return None
    except Exception as e:
        logger.warning("Cache read error: %s", str(e))
        return None


async def set_cached(
    url: str,
    data: dict,
    selector: Optional[str] = None,
    render_js: bool = False,
    ttl: Optional[int] = None,
) -> bool:
    """
    Cache a scrape result.

    Args:
        url: Target URL
        data: Result data to cache
        selector: CSS selector
        render_js: JS rendering flag
        ttl: Cache TTL in seconds (default from settings)

    Returns:
        True if cached successfully
    """
    r = await get_redis()
    if not r:
        return False

    key = _cache_key(url, selector, render_js)
    ttl = ttl or settings.REDIS_CACHE_TTL

    try:
        await r.setex(key, ttl, json.dumps(data))
        logger.debug("Cached: %s (TTL=%ds)", key, ttl)
        return True
    except Exception as e:
        logger.warning("Cache write error: %s", str(e))
        return False


async def invalidate_cached(url: str, selector: Optional[str] = None, render_js: bool = False) -> bool:
    """Invalidate a specific cache entry."""
    r = await get_redis()
    if not r:
        return False

    key = _cache_key(url, selector, render_js)
    try:
        await r.delete(key)
        logger.debug("Cache invalidated: %s", key)
        return True
    except Exception as e:
        logger.warning("Cache invalidation error: %s", str(e))
        return False


async def get_cache_stats() -> dict:
    """Get cache statistics."""
    r = await get_redis()
    if not r:
        return {"available": False}

    try:
        info = await r.info("stats")
        memory = await r.info("memory")
        return {
            "available": True,
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": round(
                info.get("keyspace_hits", 0) /
                max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100,
                2,
            ),
            "used_memory": memory.get("used_memory_human", "N/A"),
            "keys": await r.dbsize(),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
