# Retry Mechanisms Deep Dive

## Current (Phase 4)
- Exponential: 1s->2s->4s, max 30s, jitter 25%
- Retryable: 408,429,500,502,503,504
- Retry-After header respect

## Dead Letter Queue
```python
class DeadLetterQueue:
    async def add(self, job_id, error, attempts):
        await db.execute("INSERT INTO dead_letter (job_id, error, attempts) VALUES (?,?,?)",
                         (job_id, error, attempts))
    async def retry_all(self):
        jobs = await db.fetch_all("SELECT * FROM dead_letter")
        for job in jobs:
            await requeue_job(job["job_id"])
```

## Circuit Breaker (per domain)
```python
class DomainCircuitBreaker:
    def __init__(self, fail_threshold=5, window=600, cooldown=1800):
        self.failures = defaultdict(list)
        self.open_until = {}
    async def is_open(self, domain):
        if domain in self.open_until:
            if time.time() < self.open_until[domain]: return True
            del self.open_until[domain]
        return False
    async def record_failure(self, domain):
        now = time.time()
        self.failures[domain].append(now)
        self.failures[domain] = [t for t in self.failures[domain] if now - t < 600]
        if len(self.failures[domain]) >= 5:
            self.open_until[domain] = now + 1800
```

## Retry Budget
- Max 20% of total requests can be retries
- Per-destination: max 3 retries per URL
- Global retry counter with sliding window

## Status-Specific Strategy
| Status | Strategy |
|--------|----------|
| 408 | Retry immediately |
| 429 | Respect Retry-After, then exponential |
| 500-504 | Exponential backoff |
| 520-530 | Cloudflare errors, exponential backoff |
