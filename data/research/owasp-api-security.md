# OWASP Top 10 API Security (2023) — ScrapeAPI Context

## API1: Broken Object Level Authorization
**Risk:** User A accesses User B's scrape jobs via predictable IDs (UUID enumeration)
**ScrapeAPI Impact:** HIGH — Job IDs could be enumerated
**Mitigation:**
- Use UUIDs for job IDs (already done: `scrape_job.id`)
- Verify `api_key_id` matches job owner before returning results
```python
if job.api_key_id != current_api_key.id:
    raise HTTPException(404, "Job not found")  # Don't reveal existence
```

## API2: Broken Authentication
**Risk:** API key theft, brute force, weak key generation
**ScrapeAPI Impact:** HIGH — API keys are the only auth
**Mitigation:**
- Generate keys with `secrets.token_urlsafe(32)` (256-bit entropy)
- Hash keys in DB (store `sha256(key)`, compare hash)
- Rate limit auth failures (lock after 10 failures/5min)
- Key rotation support (create new, deprecate old)

## API3: Broken Object Property Level Authorization
**Risk:** Mass assignment — user sets `tier=pro` or `rate_limit=999999`
**ScrapeAPI Impact:** MEDIUM — Pydantic schemas could allow this
**Mitigation:**
- Separate `CreateSchema` (user input) from `ResponseSchema` (output)
- Never expose internal fields (`is_admin`, `tier_override`)
- Use `model_config = ConfigDict(extra="forbid")` in Pydantic

## API4: Unrestricted Resource Consumption
**Risk:** Single user sends 10K batch requests, exhausts server resources
**ScrapeAPI Impact:** HIGH — Scraping is resource-intensive
**Mitigation:**
- Rate limiting per API key (done)
- Batch size limits per tier
- Request timeout (30s per scrape)
- Max concurrent jobs per key
- Response size limits (don't return 100MB pages)

## API5: Broken Function Level Authorization
**Risk:** Regular user hits `/api/v1/keys` admin endpoints
**ScrapeAPI Impact:** MEDIUM — Key management endpoints exist
**Mitigation:**
- Separate admin routes with role check
- `is_admin` field on API key model
- Middleware check: `if route.requires_admin and not key.is_admin: 403`

## API6: Unrestricted Access to Sensitive Business Flows
**Risk:** Bot creates 1000 free accounts, abuses free tier
**ScrapeAPI Impact:** HIGH — Free tier abuse
**Mitigation:**
- Email verification for key creation
- IP-based free tier limits (not just API key)
- CAPTCHA on registration
- Monitor for patterns: same IP, multiple keys

## API7: Server Side Request Forgery (SSRF)
**Risk:** User passes `http://169.254.169.254/latest/meta-data/` as scrape URL
**ScrapeAPI Impact:** CRITICAL — Core function is fetching URLs
**Mitigation:**
- URL validation (see input-validation.md)
- DNS resolution verification (check resolved IP, not hostname)
- Block private IP ranges at httpx transport level
- Use `httpx.AsyncClient(limits=httpx.Limits(max_redirects=0))` + manual redirect following
- Dedicated scrape worker network (no access to internal services)

## API8: Security Misconfiguration
**Risk:** Debug mode in production, default secrets, verbose errors
**ScrapeAPI Impact:** MEDIUM
**Mitigation:**
- Environment-based config (dev/staging/prod)
- Hide stack traces in production
- Disable OpenAPI docs in production (`/docs`, `/redoc`)
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`
- CORS: whitelist specific origins, not `*`

## API9: Improper Inventory Management
**Risk:** Old API versions still accessible, undocumented endpoints
**ScrapeAPI Impact:** LOW (single version currently)
**Mitigation:**
- Version deprecation policy
- Endpoint inventory documentation
- Automated endpoint discovery testing

## API10: Unsafe Consumption of APIs
**Risk:** ScrapeAPI fetches URLs that return malicious content
**ScrapeAPI Impact:** HIGH — We consume arbitrary web content
**Mitigation:**
- Sanitize scraped content before storage
- Content-type verification
- Size limits on response bodies
- Don't execute JavaScript from scraped content blindly
- Sandbox Playwright contexts
