# Security Audit Checklist

## Auth
- [ ] API keys hashed in DB (SHA-256+)
- [ ] Key gen: secrets.token_urlsafe(32)
- [ ] Rate limit auth failures (10/5min)
- [ ] No keys in logs/errors/responses
- [ ] Key rotation support
- [ ] Admin endpoints role-checked

## Input
- [ ] URL validated (scheme, host, SSRF)
- [ ] Body size limits enforced
- [ ] SQL injection prevented (ORM)
- [ ] CSS selector sanitized
- [ ] Batch size limits per tier

## Network
- [ ] HTTPS enforced (HSTS)
- [ ] CORS whitelist
- [ ] Security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP
- [ ] No open redirects

## Dependencies
```bash
pip-audit
safety check
bandit -r src/ -ll
trivy image scrapeapi:latest
```

## Infrastructure
- [ ] Non-root Docker user
- [ ] Secrets in env vars, not code
- [ ] Debug off in production
- [ ] OpenAPI docs disabled in prod
- [ ] DB connection string not in logs

## API-Specific
- [ ] SSRF protection (private IP block)
- [ ] Response size limits
- [ ] Concurrent request limits per key
- [ ] Webhook URL HTTPS only
- [ ] Errors don't leak internals
