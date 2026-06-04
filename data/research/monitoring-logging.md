# Monitoring & Logging Best Practices

## Structured Logging
```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Usage
logger.info("scrape_started", url=url, api_key_id=key_id, job_id=job_id)
logger.info("scrape_completed", url=url, duration_ms=duration, status_code=200)
logger.error("scrape_failed", url=url, error=str(exc), retry_count=retries)
```

## Log Levels
- DEBUG: req/res bodies, proxy selection, UA rotation
- INFO: Job lifecycle, key usage
- WARN: Rate limit approaching, slow queries, degraded proxy
- ERROR: Scrape failures, DB errors, webhook failures
- CRITICAL: Service down, DB connection lost

## Health Checks
```python
@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0", "timestamp": datetime.utcnow()}

@app.get("/health/detailed")
async def health_detailed():
    checks = {
        "database": await check_db(),
        "redis": await check_redis(),
        "scraper": await check_scraper(),
    }
    status = "healthy" if all(c["ok"] for c in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

## Metrics to Track
- Request rate (req/s), response time (p50/p95/p99)
- Error rate (4xx/5xx), scrape success rate
- Proxy health, queue depth, DB pool usage, memory/CPU

## Alerting
- Error > 5% for 5min -> P1
- p95 latency > 10s for 10min -> P2
- Proxy pool < 50% healthy -> P2
- DB pool exhausted -> P1
- Disk > 80% -> P3

## Storage
- Local: rotating files (7d, 100MB max)
- Prod: Loki/Datadog/CloudWatch
- Retention: 30d hot, 90d cold
