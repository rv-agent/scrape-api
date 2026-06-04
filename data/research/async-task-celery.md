# Async Task Processing - Celery

## Why Celery
- Scrape jobs can take 10-60s (Playwright especially)
- Current: synchronous request -> scrape -> response (blocks worker)
- Celery: request -> enqueue -> return job_id -> poll status

## Architecture
```
FastAPI -> Redis (queue) -> Celery Worker -> Result DB
                                |
                          Playwright/HTTP scraper
```

## Setup
```python
from celery import Celery

celery_app = Celery(
    "scrapeapi",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_time_limit=300,  # 5min hard limit per task
    task_soft_time_limit=240,  # 4min soft limit (raises SoftTimeLimitExceeded)
    worker_prefetch_multiplier=1,  # one task at a time per worker
    worker_max_tasks_per_child=100,  # restart worker after 100 tasks (memory leak prevention)
)
```

## Task Definition
```python
@celery_app.task(bind=True, max_retries=3)
def scrape_task(self, job_id, url, selector=None, proxy=None, user_agent=None):
    try:
        result = asyncio.run(scraper.scrape(url, selector=selector))
        update_job_status(job_id, "completed", result)
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        update_job_status(job_id, "failed", str(exc))
```

## Result Backend
- Redis: fast, volatile (lost on Redis restart)
- SQLAlchemy: persistent, queryable (better for job history)
- Recommendation: Redis for caching, DB for persistence

## Worker Management
```bash
# Start workers
celery -A src.tasks worker -l info -c 4 -Q scrape,default

# Scale up
celery -A src.tasks worker -l info -c 8 -Q scrape

# Monitor
celery -A src.tasks flower --port=5555
```

## Queue Routing
```python
celery_app.conf.task_routes = {
    "src.tasks.scrape_task": {"queue": "scrape"},
    "src.tasks.batch_task": {"queue": "batch"},
    "src.tasks.webhook_task": {"queue": "webhooks"},
}
```

## Concurrency
| Tier | Max Concurrent Jobs |
|------|-------------------|
| Free | 1 |
| Starter | 5 |
| Pro | 20 |
| Enterprise | 100 |
