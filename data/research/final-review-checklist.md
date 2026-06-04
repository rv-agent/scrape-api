# Pre-Launch Checklist

## Functionality
- [ ] Single URL scrape (static + dynamic)
- [ ] Batch scrape (parallel)
- [ ] Job status tracking
- [ ] API key CRUD
- [ ] Rate limiting per tier
- [ ] Webhook delivery with retry
- [ ] Export (JSON, CSV, Excel)
- [ ] Scheduler (cron-based)
- [ ] Caching (Redis, TTL)

## Security
- [ ] OWASP API Top 10 mitigated
- [ ] SSRF protection verified
- [ ] Keys hashed in DB
- [ ] HTTPS enforced
- [ ] CORS configured
- [ ] Security headers set
- [ ] No sensitive data in logs
- [ ] Dependencies audited

## Performance
- [ ] Load test passed (100 concurrent)
- [ ] Response time targets met
- [ ] Connection pooling configured
- [ ] DB indexes created
- [ ] Caching reduces repeat load

## Infrastructure
- [ ] Docker image builds
- [ ] Health checks respond
- [ ] Monitoring (Sentry, structured logging)
- [ ] Alerts configured
- [ ] DB backup strategy
- [ ] SSL valid

## Billing
- [ ] Stripe integration tested
- [ ] Subscription lifecycle works
- [ ] Usage metering accurate
- [ ] Over-limit handling correct
- [ ] Webhook signature verification

## Docs
- [ ] API docs with examples
- [ ] SDK generated (Python min)
- [ ] Getting started guide
- [ ] Error code reference
- [ ] Rate limit docs
- [ ] Webhook events docs

## Legal
- [ ] Terms of Service
- [ ] Privacy Policy
- [ ] Acceptable Use Policy
- [ ] GDPR compliance (EU)
