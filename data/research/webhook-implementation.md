# Webhook System

## Events
- job.completed, job.failed, job.batch_completed
- key.rotated, usage.limit_reached

## Registration
```python
class WebhookCreate(BaseModel):
    url: HttpUrl
    events: list[str]
    secret: str | None = None  # auto-generated if absent
```

## Delivery
```python
async def deliver_webhook(webhook, event, payload):
    body = json.dumps({"event": event, "data": payload, "timestamp": time.time()})
    sig = hmac.new(webhook.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-ScrapeAPI-Signature": f"sha256={sig}",
        "X-ScrapeAPI-Event": event,
        "X-ScrapeAPI-Delivery": str(uuid.uuid4()),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook.url, content=body, headers=headers)
        return resp.status_code
```

## Retry
- 3 attempts: immediate, 1min, 5min
- Then: 30min, 2hr, 12hr exponential
- Inactive after 7 consecutive failures

## Verification (customer side)
```python
def verify_webhook(payload, signature, secret):
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## Security
- HTTPS only, secret as hash in DB
- Rate limit: 100 deliveries/min per key
- Payload limit: 1MB

## Schema
```sql
CREATE TABLE webhooks (
    id UUID PRIMARY KEY, api_key_id UUID REFERENCES api_keys(id),
    url TEXT NOT NULL, events TEXT[] NOT NULL, secret_hash TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE, consecutive_failures INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY, webhook_id UUID REFERENCES webhooks(id),
    event TEXT NOT NULL, status_code INT, response_body TEXT,
    attempt INT DEFAULT 1, delivered_at TIMESTAMPTZ DEFAULT NOW()
);
```
