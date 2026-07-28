# TradeCraft — Deployment

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Deployment Philosophy

**Build once, configure per environment, run anywhere.**

The same application code and container images deploy across all environments. Differences are configuration only.

## 2. Environment Matrix

| Environment | OS | Database | Broker | Mode | Purpose |
|-------------|-----|----------|--------|------|---------|
| LOCAL_WINDOWS | Windows | Docker PostgreSQL | Paper | PAPER | Primary development |
| LOCAL_MACOS | macOS | Docker PostgreSQL | Paper | PAPER | Development |
| LOCAL_LINUX | Linux | Docker PostgreSQL | Paper | PAPER | Development |
| CLOUD_DEV | Linux | Docker PostgreSQL | Paper | PAPER | Cloud development |
| CLOUD_PAPER | Linux | Managed PostgreSQL | Paper | PAPER | Cloud paper trading |
| CLOUD_PRODUCTION | Linux | Managed PostgreSQL | Zerodha | LIVE | Production (future) |

## 3. Docker

### Local Development
```bash
docker compose up -d    # Works on Windows, macOS, Linux
```

Current services:
- PostgreSQL 16 (Alpine)

Future services (to be added per milestone):
- Application container
- Dashboard container

### Production
- Same Docker images as local development
- Orchestration TBD (simple Docker Compose initially)
- No Kubernetes unless complexity demands it

## 4. Database Migrations

- All schema changes via version-controlled migrations
- Migration tool: TBD (Alembic is the likely choice)
- Fresh environment reproducible from: Git + config + Docker + migrations
- Never rely on manually created database state

## 5. CI/CD

### Platform: GitHub Actions

### Pipeline
```
Push/PR → Lint → Type Check → Unit Tests → Integration Tests → Build
```

### OS Matrix
| OS | Tests |
|----|-------|
| Linux (ubuntu-latest) | All tests |
| Windows (windows-latest) | All tests |
| macOS (macos-latest) | All tests (best effort) |

### Checks
- Ruff (linting + formatting)
- mypy (type checking)
- pytest (unit + integration)
- Security/dependency scanning
- Migration validation
- Docker build validation

## 6. Configuration Management

All environment-specific configuration via environment variables:
- `.env` file for local development
- Environment variables for cloud deployment
- No config files with environment-specific values committed to Git

## 7. Secrets in Deployment

| Environment | Secret Storage |
|-------------|---------------|
| Local | `.env` file (not committed) |
| Cloud | Cloud provider secret manager or environment variables |
| CI | GitHub Actions secrets |
