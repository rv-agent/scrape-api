# Scheduler Design

## Options
| Approach | Pros | Cons |
|----------|------|------|
| Cron (APScheduler) | Simple, built-in | Single-node, no persistence |
| Celery Beat | Distributed, persistent | Heavy, needs Redis/RabbitMQ |
| Custom + Redis | Lightweight, flexible | More code to write |
| Cloud (Render Cron) | Zero infra | Vendor lock-in |

## Recommendation: APScheduler + Redis
- Start with APScheduler (simple, works with FastAPI)
- Use Redis job store for persistence
- Migrate to Celery Beat if scaling needed

## Implementation
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore

jobstores = {"default": RedisJobStore(host=settings.REDIS_HOST, port=settings.REDIS_PORT)}
scheduler = AsyncIOScheduler(jobstores=jobstores)

@scheduler.scheduled_job("interval", hours=1, id="health_check")
async def scheduled_health_check():
    await run_health_checks()

# User-facing: schedule recurring scrapes
@app.post("/api/v1/schedules")
async def create_schedule(schedule: ScheduleCreate, key=Depends(get_api_key)):
    job = scheduler.add_job(
        "src.scraper.http_scraper:scrape",
        trigger=schedule.cron,  # "*/30 * * * *" = every 30min
        args=[schedule.url],
        id=f"schedule_{key.id}_{schedule.id}",
        replace_existing=True,
    )
    return {"schedule_id": schedule.id, "next_run": job.next_run_time}
```

## Cron Syntax
```
*/5 * * * *       Every 5 minutes
0 */2 * * *       Every 2 hours
0 9 * * 1-5       Weekdays at 9am
0 0 1 * *         First of month
```

## Limits per Tier
| Tier | Max Schedules | Min Interval |
|------|--------------|--------------|
| Free | 0 | - |
| Starter | 5 | 1 hour |
| Pro | 20 | 15 min |
| Enterprise | 100 | 1 min |

## Storage
```sql
CREATE TABLE schedules (
    id UUID PRIMARY KEY, api_key_id UUID REFERENCES api_keys(id),
    url TEXT NOT NULL, cron TEXT NOT NULL, selector TEXT,
    webhook_id UUID REFERENCES webhooks(id),
    active BOOLEAN DEFAULT TRUE, last_run TIMESTAMPTZ, next_run TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
