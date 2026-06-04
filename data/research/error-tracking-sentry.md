# Error Tracking - Sentry

## Setup
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    integrations=[FastApiIntegration(), SqlalchemyIntegration(), HttpxIntegration()],
    before_send=filter_sensitive_data,
)
```

## Filtering
```python
def filter_sensitive_data(event, hint):
    if "request" in event:
        headers = event["request"].get("headers", {})
        headers.pop("Authorization", None)
        headers.pop("X-API-Key", None)
    if "exc_info" in hint:
        exc = hint["exc_info"][1]
        if isinstance(exc, TargetSiteError) and exc.status_code < 500:
            return None
    return event
```

## Grouping
- By exception type + message + stack fingerprint
- Custom: scope.fingerprint = ["scrape-error", error_type, domain]

## Context Tags
```python
sentry_sdk.set_tag("api_key_id", key_id)
sentry_sdk.set_tag("tier", key.tier)
sentry_sdk.set_tag("target_domain", domain)
sentry_sdk.set_context("scrape_job", {
    "job_id": job_id, "url": url, "proxy_used": proxy, "retry_count": retries
})
```

## Performance
- Scrape duration as transaction
- DB query time spans
- Custom spans for proxy selection, UA rotation

## Alerts
- New issue -> Slack/email
- Recurring > 10x/hr -> escalation
- Perf regression > 2x -> alert
