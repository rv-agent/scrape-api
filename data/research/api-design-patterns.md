# API Design Patterns for ScrapeAPI

## REST Best Practices
- Resource-based URLs: `/api/v1/scrape`, `/api/v1/keys`, `/api/v1/jobs`
- HTTP methods: GET (read), POST (create/action), PUT (replace), PATCH (update), DELETE
- Consistent JSON envelope: `{"data": ..., "meta": ..., "error": ...}`
- Versioning: URL path (`/api/v1/`) — simplest, most explicit for SaaS APIs

## Pagination
- **Cursor-based** (recommended for jobs): `?cursor=abc123&limit=20`
  - Stable under inserts/deletes
  - Better performance for large datasets
  - Response: `{"data": [...], "next_cursor": "xyz", "has_more": true}`
- **Offset-based** (simpler, for admin): `?page=2&per_page=20`
  - Suffers from drift on mutable data
  - OK for small, controlled datasets

## Error Response Format
```json
{
  "error": {
    "code": "INVALID_URL",
    "message": "URL must use http or https scheme",
    "details": {"url": "ftp://example.com"},
    "request_id": "req_abc123"
  }
}
```
- Consistent envelope across all endpoints
- Machine-readable `code`, human-readable `message`
- `request_id` for support/debugging

## Rate Limit Headers
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1623456789
X-RateLimit-Policy: 60;w=60
```
- Already implemented in ScrapeAPI middleware

## Idempotency Keys
- `Idempotency-Key` header for POST requests
- Store key + response for 24h in Redis
- Prevents duplicate jobs on retry
```python
@app.post("/api/v1/scrape")
async def scrape(request: Request):
    key = request.headers.get("Idempotency-Key")
    if key:
        cached = await redis.get(f"idempotency:{key}")
        if cached:
            return json.loads(cached)
```

## HATEOAS (optional, low priority)
- Self links in responses: `"_links": {"self": "/api/v1/jobs/123", "status": "/api/v1/status/123"}`
- Useful for discoverability, not critical for API-first SaaS

## Content Negotiation
- `Accept: application/json` (default)
- `Accept: text/csv` for export endpoints
- `Content-Type: application/json` for all request bodies

## Request/Response Sizing
- Max request body: 1MB for scrape, 10MB for batch
- Pagination default: 20, max: 100
- Batch max: 50 URLs per request (tier-dependent)
