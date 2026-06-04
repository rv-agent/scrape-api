# Docker Best Practices

## Multi-Stage Dockerfile
Stage 1 (builder): python:3.11-slim, pip install --user
Stage 2 (runtime): python:3.11-slim, non-root user, copy from builder
HEALTHCHECK: curl -f http://localhost:8000/health

## Docker Compose
- api: FastAPI web server, port 8000
- worker: Celery worker, 4 concurrency
- redis: Redis 7-alpine, volume persistent
- db: Postgres 15-alpine, volume persistent

## Security
- Non-root user (appuser)
- No shell in production
- Read-only filesystem where possible
- Scan: trivy image scrapeapi:latest

## Optimization
- .dockerignore: .git, __pycache__, .venv, node_modules
- Layer caching: requirements.txt first, then source
- Alpine base (~50MB vs ~900MB)
- Multi-stage excludes build tools from runtime

## Logging
- stdout/stderr only (no file logging)
- Docker logging driver: json-file with max-size/max-file
