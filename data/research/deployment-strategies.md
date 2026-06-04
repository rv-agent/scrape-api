# Deployment Strategies

## Platform: Render.com
- Web service: uvicorn src.main:app
- Worker service: celery -A src.tasks worker
- Redis: managed Redis
- Postgres: managed Postgres
- Scaling: min 1, max 3 instances

## Blue-Green Deploy
Current (blue) -> New (green) -> Health check -> Switch traffic
Render: built-in zero-downtime deploys

## Environment Strategy
| Env | Purpose | Auto-deploy |
|-----|---------|-------------|
| dev | Local | On push to feature branch |
| staging | Testing | On push to main |
| production | Live | Manual approval |

## Pre-Deploy Checklist
- All tests pass
- Linting clean
- Docker build succeeds
- Health check responds
- DB migrations applied
- Env vars set
- Sentry DSN configured
- Stripe webhooks configured

## Rollback
- Render: rollback via dashboard or CLI
- Docker: tag previous version, docker-compose up -d

## Domain & SSL
- Custom domain: api.scrapeapi.com
- Cloudflare DNS + SSL (free tier)
- HSTS header for forced HTTPS
