# CI/CD Pipeline

## GitHub Actions Workflow
### Jobs:
1. test: lint (ruff) + type check (mypy) + tests (pytest --cov) + security (pip-audit, bandit)
2. build: docker build + push to GHCR (on main only)
3. deploy-staging: auto on main push
4. deploy-production: manual approval required

## Quality Gates
| Gate | Tool | Threshold |
|------|------|----------|
| Linting | ruff | 0 errors |
| Type check | mypy | 0 errors |
| Tests | pytest | 100% pass |
| Coverage | coverage.py | > 80% |
| Security | pip-audit | 0 critical |
| Bandit | bandit | 0 high |
| Docker scan | trivy | 0 critical |

## Makefile
make lint, make test, make security, make build, make deploy-staging

## Branch Strategy
- main -> production (manual approval)
- develop -> staging (auto)
- feature/* -> PR to develop
- hotfix/* -> PR to main
