# Caching Strategies - Redis

## Use Cases
1. **Rate limiting** — sliding window counter (already planned)
2. **API response cache** — cache scrape results for identical URLs
3. **Session/auth cache** — API key lookups
4. **Job queue** — Celery broker
5. **Webhook idempotency** — deduplicate deliveries

## Setup
```python
import redis.asyncio as redis

redis_pool = redis.ConnectionPool.from_url(
    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    max_connections=20,
    decode_responses=True,
)
redis_client = redis.Redis(connection_pool=redis_pool)
```

## Response Cache
```python
async def get_cached_scrape(url: str, selector: str | None) -> dict | None:
    cache_key = f"scrape:{hashlib.sha256(f'{url}:{selector}'.encode()).hexdigest()}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    return None

async def cache_scrape_result(url: str, selector: str | None, result: dict, ttl: int = 3600):
    cache_key = f"scrape:{hashlib.sha256(f'{url}:{selector}'.encode()).hexdigest()}"
    await redis_client.setex(cache_key, ttl, json.dumps(result))
```

## Cache Invalidation
- TTL-based: 1h for static pages, 5min for dynamic
- Manual: `DELETE /api/v1/cache?url=...` (Pro tier)
- LRU eviction when memory full

## Rate Limiting (Sliding Window)
```python
async def check_rate_limit(key_id: str, limit: int, window: int = 60) -> bool:
    now = time.time()
    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(f"ratelimit:{key_id}", 0, now - window)
    pipe.zadd(f"ratelimit:{key_id}", {str(now): now})
    pipe.zcard(f"ratelimit:{key_id}")
    pipe.expire(f"ratelimit:{key_id}", window)
    results = await pipe.execute()
    return results[2] <= limit
```

## Memory Management
- Max memory: 256MB (enough for cache + rate limiting)
- Eviction: allkeys-lru
- Key prefix: `scrapeapi:` for namespacing

## Monitoring
```python
async def get_redis_stats():
    info = await redis_client.info("memory")
    return {
        "used_memory_mb": info["used_memory"] / 1024 / 1024,
        "connected_clients": (await redis_client.info("clients"))["connected_clients"],
        "keyspace_hits": (await redis_client.info("stats"))["keyspace_hits"],
        "keyspace_misses": (await redis_client.info("stats"))["keyspace_misses"],
    }
```

## Tier-Based Caching
| Tier | Cache TTL | Manual Invalidate | Cache-First |
|------|-----------|-------------------|-------------|
| Free | 1h | No | No |
| Starter | 30min | No | Yes |
| Pro | 5min | Yes | Yes |
| Enterprise | Custom | Yes | Yes |
