# TradeCraft — Cloud Migration Plan

> Version: 1.0.0 | Status: PLANNED | Last Updated: 2026-07-28

## 1. Cloud Migration (M13)

Cloud migration is the final milestone. The system must first prove itself locally through paper trading before any cloud deployment is considered.

## 2. Target Architecture

- **Runtime**: Linux containers
- **Database**: Managed PostgreSQL (cloud provider)
- **Compute**: Single VM initially (not Kubernetes)
- **Operation**: 24×7 (vs current manual daily start)

## 3. Prerequisites Before Cloud

- [ ] All milestones M0–M12 completed
- [ ] System proven stable in local paper trading
- [ ] System proven stable in limited live trading
- [ ] No Windows-specific dependencies (verified by CI)
- [ ] Docker images build and run on Linux
- [ ] All configuration externalised

## 4. Migration Concerns

| Concern | Approach |
|---------|----------|
| Database migration | PostgreSQL dump/restore or managed migration |
| Secrets | Cloud provider secret manager |
| Monitoring | Cloud-native logging + alerting |
| Availability | Single VM with health monitoring |
| Cost | Estimate before committing |
| Backup | Automated database backups |
| Security | Network isolation, firewall rules |

## 5. What Changes

| Aspect | Local | Cloud |
|--------|-------|-------|
| Start/stop | Manual | Always running |
| Database | Docker PostgreSQL | Managed PostgreSQL |
| Secrets | `.env` file | Cloud secret manager |
| Monitoring | Dashboard only | Dashboard + alerting |
| Network | Local only | Internet-accessible (secured) |

## 6. What Does NOT Change

- Application code
- Docker images
- Configuration structure (values change, keys don't)
- Module boundaries
- Risk controls
- Compliance rules
- Paper/live separation
