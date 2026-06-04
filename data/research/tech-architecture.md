# Technical Architecture: ScrapeAPI

## OVERVIEW

Document ini berisi analisa teknis untuk membangun ScrapeAPI — platform scraping API berbasis FastAPI dengan Playwright, Celery, Redis, dan PostgreSQL.

---

## 1. SCRAPING ENGINE OPTIONS

### Option A: Playwright (RECOMMENDED)
```python
# Pros:
- Async native (asyncio)
- Multi-browser (Chromium, Firefox, WebKit)
- Auto-wait for elements
- Network interception
- Built-in stealth capabilities
- Active development by Microsoft

# Cons:
- Heavy resource usage (~300MB per browser instance)
- Slower than raw HTTP for simple pages
- Requires browser binaries

# Best for: Dynamic pages, SPAs, anti-bot protected sites
```

### Option B: httpx + BeautifulSoup
```python
# Pros:
- Very fast (no browser overhead)
- Low resource usage
- Async support
- Simple to implement

# Cons:
- No JavaScript rendering
- Can't handle SPAs
- Easy to block

# Best for: Static pages, APIs, simple scraping
```

### Option C: Scrapy
```python
# Pros:
- Battle-tested framework
- Built-in middleware pipeline
- Extensive plugin ecosystem
- Distributed crawling support

# Cons:
- Steep learning curve
- Not async-native (Twisted)
- Heavy framework for simple API

# Best for: Large-scale crawling projects
```

### Option D: Selenium
```python
# Pros:
- Widely known
- Many tutorials
- Multi-browser

# Cons:
- Synchronous by default
- Slower than Playwright
- More flaky
- Older architecture

# Best for: Legacy projects (NOT recommended for new)
```

### RECOMMENDATION: Hybrid Approach
```
Simple pages → httpx (fast, cheap)
Dynamic pages → Playwright (full rendering)
Auto-detect → Try httpx first, fallback to Playwright
```

---

## 2. ANTI-DETECTION TECHNIQUES

### Browser Fingerprint Rotation
```python
# Key fingerprints to rotate:
- User-Agent string
- Screen resolution
- Canvas fingerprint
- WebGL fingerprint
- AudioContext fingerprint
- Navigator properties (platform, languages)
- Timezone
- WebRTC IP leak prevention

# Implementation:
playwright-stealth or custom stealth patches
```

### Proxy Rotation
```python
# Strategies:
1. Per-request rotation (most anonymous)
2. Per-session rotation (maintain state)
3. Per-domain rotation (optimize for target)

# Pool management:
- Track proxy health (success rate, latency)
- Remove bad proxies automatically
- Rotate within pool based on strategy
```

### Request Rate Randomization
```python
# Techniques:
- Random delays between requests (1-5 seconds)
- Human-like scrolling/clicking patterns
- Randomize request order
- Exponential backoff on rate limits
```

### TLS Fingerprint Spoofing
```python
# Libraries:
- curl_cffi (Python) — impersonate browser TLS
- tls-client — Go-based TLS fingerprint library
- JA3/JA4 fingerprint rotation

# Priority: HIGH (many anti-bot systems check TLS fingerprint)
```

---

## 3. PROXY INFRASTRUCTURE

### Proxy Types
| Type | Speed | Cost/GB | Detection Risk | Use Case |
|------|-------|---------|----------------|----------|
| Datacenter | Fast | $0.5-2 | High | Low-protection sites |
| ISP | Fast | $2-8 | Medium | General scraping |
| Residential | Medium | $5-15 | Low | Protected sites |
| Mobile | Slow | $15-30 | Very Low | Mobile-specific |

### Proxy Providers (Recommended for ScrapeAPI)
| Provider | Starting Price | Pool Size | Notes |
|----------|---------------|-----------|-------|
| Smartproxy | $7/GB | 40M+ | Good value |
| IPRoyal | $1.75/GB | 32M+ | Budget option |
| WebShare | $0.05/proxy | 30M+ | Datacenter focus |
| Bright Data | $5/GB | 72M+ | Enterprise |

### Rotation Strategy for ScrapeAPI
```
Phase 1 (MVP):
- Datacenter proxies only
- Per-request rotation
- Cost: ~$50-100/month

Phase 2 (Growth):
- Add ISP proxies
- Session-based rotation for login flows
- Cost: ~$200-500/month

Phase 3 (Scale):
- Add residential for premium tier
- Smart routing (cheap proxy first, escalate if blocked)
- Cost: ~$1000+/month
```

---

## 4. TASK QUEUE SYSTEM

### Celery + Redis (RECOMMENDED)

```python
# Architecture:
Client → FastAPI → Redis (queue) → Celery Workers → Scrapers → Results → Redis/DB

# Celery Configuration:
app = Celery('scraper', broker='redis://localhost:6379/0')

# Task states:
PENDING → STARTED → SUCCESS/FAILURE/RETRY

# Worker scaling:
- Horizontal: Add more worker containers
- Vertical: Increase concurrency per worker
- Auto-scale based on queue depth
```

### Alternative: Dramatiq
```python
# Pros over Celery:
- Simpler API
- Better error handling
- Built-in retry with backoff
- Redis + RabbitMQ support

# Cons:
- Smaller ecosystem
- Less monitoring tools
- Fewer integrations

# Verdict: Celery is safer choice for production
```

### Job State Machine
```
┌─────────┐
│ PENDING │ ← Initial state
└────┬────┘
     │
     ▼
┌─────────┐
│ STARTED │ ← Worker picked up
└────┬────┘
     │
     ├──── SUCCESS → Store results
     │
     ├──── FAILURE → Retry (if attempts left)
     │               → FAILED (if max retries)
     │
     └──── TIMEOUT → FAILED
```

---

## 5. RATE LIMITING

### Token Bucket Algorithm (RECOMMENDED)
```python
# Concept:
- Bucket has capacity (max tokens)
- Tokens added at fixed rate
- Each request consumes 1 token
- If bucket empty → request rejected

# Redis implementation:
def check_rate_limit(api_key, limit, window):
    key = f"rate:{api_key}"
    now = time.time()
    
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, window)
    
    _, count, _, _ = pipe.execute()
    
    return count < limit
```

### Sliding Window Counter
```python
# Better for bursty traffic
# Combines current + previous window counts
# Smoother rate limiting experience
```

### Per-API-Key Rate Limits
| Tier | Requests/Minute | Requests/Hour | Requests/Day |
|------|----------------|---------------|--------------|
| Free | 5 | 100 | 100 |
| Starter | 30 | 1,000 | 10,000 |
| Pro | 100 | 5,000 | 50,000 |
| Business | 300 | 15,000 | Unlimited |

---

## 6. CACHING STRATEGY

### Redis Caching
```python
# Cache key generation:
import hashlib
import json

def make_cache_key(url, params):
    content = json.dumps({"url": url, **params}, sort_keys=True)
    return f"cache:{hashlib.sha256(content.encode()).hexdigest()}"

# Cache TTL:
- Success: 1 hour (configurable)
- Failure: 5 minutes
- 404: 1 hour
- Rate limited: 1 minute

# Cache invalidation:
- TTL-based (automatic)
- Manual invalidation via API
- Cache-Control header respect
```

### Content Deduplication
```python
# Before scraping, check if same URL+params was recently scraped
# Saves proxy bandwidth and improves response time
# Dedup window: 5 minutes (configurable)
```

---

## 7. DATABASE SCHEMA

### PostgreSQL (Production) / SQLite (Development)

```sql
-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(100),
    tier VARCHAR(20) DEFAULT 'free',
    rate_limit_per_minute INT DEFAULT 5,
    rate_limit_per_day INT DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);

-- Scrape Jobs
CREATE TABLE scrape_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id UUID REFERENCES api_keys(id),
    url TEXT NOT NULL,
    method VARCHAR(10) DEFAULT 'GET',
    params JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    priority INT DEFAULT 0,
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 3,
    result JSONB,
    error TEXT,
    response_code INT,
    response_time_ms INT,
    proxy_used VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Usage Logs
CREATE TABLE usage_logs (
    id BIGSERIAL PRIMARY KEY,
    api_key_id UUID REFERENCES api_keys(id),
    date DATE NOT NULL,
    requests_count INT DEFAULT 0,
    success_count INT DEFAULT 0,
    failure_count INT DEFAULT 0,
    bandwidth_bytes BIGINT DEFAULT 0,
    UNIQUE(api_key_id, date)
);

-- Subscriptions
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    plan VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    stripe_subscription_id VARCHAR(100),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_jobs_status ON scrape_jobs(status);
CREATE INDEX idx_jobs_api_key ON scrape_jobs(api_key_id);
CREATE INDEX idx_jobs_created ON scrape_jobs(created_at);
CREATE INDEX idx_usage_date ON usage_logs(api_key_id, date);
```

---

## 8. API DESIGN

### Endpoints

```
POST /v1/scrape
  - Single URL scraping
  - Body: { url, render_js, proxy_type, geotarget, custom_headers, wait_for }
  - Response: { id, status, data, metadata }

POST /v1/batch
  - Multiple URLs
  - Body: { urls: [{ url, ...options }], webhook_url }
  - Response: { batch_id, job_count, status }

GET /v1/status/{job_id}
  - Check job status
  - Response: { id, status, progress, result }

GET /v1/usage
  - Current usage stats
  - Response: { requests_today, requests_this_month, limits }

POST /v1/extract
  - AI-powered extraction
  - Body: { url, schema, instructions }
  - Response: { id, status, extracted_data }
```

### Request Schema
```json
{
  "url": "https://example.com",
  "render_js": false,
  "proxy_type": "datacenter",
  "geotarget": "US",
  "custom_headers": {
    "Accept-Language": "en-US"
  },
  "wait_for": "#content",
  "timeout": 30000,
  "format": "json"
}
```

### Response Schema
```json
{
  "id": "job_abc123",
  "status": "completed",
  "url": "https://example.com",
  "data": {
    "html": "...",
    "text": "...",
    "metadata": {
      "title": "Example",
      "status_code": 200,
      "response_time_ms": 1234
    }
  },
  "cost": {
    "credits_used": 1,
    "proxy_type": "datacenter"
  }
}
```

### Error Codes
```json
{
  "400": "Invalid request parameters",
  "401": "Invalid or missing API key",
  "403": "API key suspended",
  "429": "Rate limit exceeded",
  "500": "Internal server error",
  "502": "Target site unreachable",
  "503": "Service temporarily unavailable",
  "504": "Scraping timeout"
}
```

---

## 9. DEPLOYMENT ARCHITECTURE

### Docker Compose (Development)
```yaml
version: '3.8'
services:
  api:
    build: ./docker/api
    ports: ["8000:8000"]
    depends_on: [redis, postgres]
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres/scrapeapi
      - REDIS_URL=redis://redis:6379/0
  
  worker:
    build: ./docker/worker
    depends_on: [redis, postgres]
    command: celery -A src.tasks worker -l info -c 4
  
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  
  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=scrapeapi
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### Production (Render.com)
```
- Web Service: FastAPI (auto-scaling)
- Worker Service: Celery workers
- Redis: Managed Redis
- PostgreSQL: Managed PostgreSQL
- CDN: Cloudflare
```

---

## 10. TECHNOLOGY STACK DECISIONS

### Final Stack
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| API Framework | FastAPI | Async, auto-docs, performance |
| Scraping (static) | httpx + BeautifulSoup | Fast, lightweight |
| Scraping (dynamic) | Playwright | Full browser rendering |
| Task Queue | Celery + Redis | Mature, scalable |
| Database | PostgreSQL | Reliable, JSONB support |
| Cache | Redis | Fast, pub/sub support |
| Proxy Management | Custom pool | Flexibility |
| Monitoring | Sentry + Prometheus | Error tracking + metrics |
| Deployment | Docker + Render.com | Simple, scalable |

### Dependencies (Python)
```
fastapi>=0.104.0
uvicorn>=0.24.0
celery>=5.3.0
redis>=5.0.0
httpx>=0.25.0
beautifulsoup4>=4.12.0
playwright>=1.40.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
pydantic>=2.5.0
python-dotenv>=1.0.0
sentry-sdk>=1.38.0
prometheus-client>=0.19.0
```

---

## IMPLEMENTATION PRIORITIES

### Phase 1 (Week 1): MVP
1. FastAPI skeleton with health endpoint
2. httpx-based static scraper
3. API key authentication
4. Basic rate limiting (Redis)
5. Single URL scraping endpoint

### Phase 2 (Week 2): Dynamic
1. Playwright integration
2. Celery async task queue
3. Job status tracking
4. Proxy rotation (datacenter)

### Phase 3 (Week 3): Production
1. PostgreSQL database
2. Usage tracking & billing
3. Error handling & retries
4. Monitoring (Sentry)
5. Docker containerization

### Phase 4 (Week 4+): Scale
1. Batch processing
2. Webhook callbacks
3. AI-powered extraction
4. Dashboard
5. Advanced proxy management
