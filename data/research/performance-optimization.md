# Performance Optimization

## Connection Pooling
- httpx: max_connections=100, keepalive=20, expiry=30s
- SQLAlchemy: pool_size=20, max_overflow=10

## Async Optimization
- Parallel batch: asyncio.Semaphore(10) + gather()
- Stream large responses: aiter_bytes(8192)

## Database
- Indexes: api_keys.key_hash, scrape_jobs.status, scrape_jobs.created_at
- Cursor pagination (not offset)
- select() with specific columns, not SELECT *

## Caching
- L1: in-process LRU (1000 items)
- L2: Redis (shared, TTL-based)
- L3: Database (source of truth)

## Load Testing
- Locust or k6
- Target: 100 concurrent users

## Performance Targets
| Metric | Target | Critical |
|--------|--------|----------|
| API p50 | < 200ms | < 500ms |
| API p95 | < 1s | < 3s |
| Scrape static | < 2s | < 10s |
| Scrape dynamic | < 10s | < 30s |
| Concurrent | 100 | 50 |
| DB query p95 | < 50ms | < 200ms |

## Scaling Strategy
Single -> Multiple workers -> Horizontal -> Auto-scaling
< 100 rps -> < 1K rps -> < 10K rps -> > 10K rps
