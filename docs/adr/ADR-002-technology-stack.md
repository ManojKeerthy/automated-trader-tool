# ADR-002: Technology Stack

**Status**: ACCEPTED
**Date**: 2026-07-28
**Decision Makers**: User (constitution)

## Context

Need to select a technology stack that supports quantitative finance, cross-platform development, and a rich dashboard UI.

## Decision

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend | Python | 3.11+ |
| Dashboard | React + TypeScript | Latest |
| Build tool | Vite | Latest |
| Database | PostgreSQL | 16 |
| Infrastructure | Docker + Docker Compose | Latest |
| Version control | Git + GitHub | — |
| CI/CD | GitHub Actions | — |
| Linting | Ruff | Latest |
| Type checking | mypy | Latest |
| Testing | pytest | Latest |

## Rationale

- **Python**: Best ecosystem for quant finance (pandas, numpy, scipy, scikit-learn), data analysis, and AI integration
- **React + TypeScript**: Rich interactive UI for trade approval workflow, type safety
- **PostgreSQL**: Reliable, ACID-compliant, excellent for financial data, cross-platform via Docker
- **Docker**: Eliminates "works on my machine" problems, identical setup across all OS
- **GitHub Actions**: Supports Windows/macOS/Linux CI matrix

## Consequences

- All quantitative logic, risk engine, and trading engine in Python
- Dashboard communicates with backend via REST API (FastAPI)
- PostgreSQL runs in Docker for local dev, managed service for cloud
- Dependencies pinned for reproducibility
