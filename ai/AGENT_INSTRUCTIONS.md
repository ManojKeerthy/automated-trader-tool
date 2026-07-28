# TradeCraft — Agent Instructions

> Version: 1.0.0 | Last Updated: 2026-07-28

## Before Any Substantial Work

1. Read this file (`AGENT_INSTRUCTIONS.md`)
2. Read `PROJECT_MEMORY.md`
3. Read `CURRENT_STATE.md`
4. Read relevant `docs/` policy documents
5. Read applicable `docs/adr/` ADRs
6. Inspect existing implementation and tests

## Core Rules

### Priority Hierarchy
Compliance > Capital preservation > Loss prevention > Data correctness > Risk management > Strategy robustness > Execution correctness > Risk-adjusted returns > Raw return.

**Never reverse this hierarchy to increase expected profit.**

### Anti-Hallucination
Never invent:
- Regulatory rules or broker capabilities
- API endpoints, limits, or fees
- Market data or financial results
- Backtest results or statistical significance
- Strategy performance
- Implemented functionality

Distinguish explicitly between: KNOWN, ASSUMED, PROPOSED, VERIFIED, IMPLEMENTED, TESTED.

### What You May Do
- Propose strategies, features, parameters
- Run research and backtests
- Analyse failures and propose improvements
- Identify strategy degradation
- Research modifications to live strategies
- Create and update documentation

### What You May NOT Do
- Promote a strategy to production
- Silently alter production strategy behaviour
- Bypass risk controls
- Bypass compliance controls
- Modify production code because regulation changed (without human approval)
- Claim functionality is implemented because documentation describes it
- Silently contradict repository decisions

### Documentation Updates
- When making changes, update CURRENT_STATE.md
- When making decisions, update DECISIONS.md
- When discovering limitations, update KNOWN_LIMITATIONS.md
- When making assumptions, update ASSUMPTIONS.md
- Never claim something exists that doesn't

### External Information
- Regulatory rules: Verify from primary sources
- Broker API: Use current official documentation
- Market data: Validate quality
- When unable to verify something important: mark unresolved, fail safely

## Repository Structure

```
src/tradecraft/          — Python application modules
dashboard/               — React + TypeScript dashboard
tests/                   — Automated tests
docs/                    — Policy & design documents
docs/adr/                — Architecture Decision Records
docs/strategy-decisions/ — Strategy Decision Records
ai/                      — Agent memory (this directory)
```

## Technology

- Python 3.11+ (backend)
- React + TypeScript (dashboard)
- PostgreSQL 16 (database, via Docker)
- Docker Compose (infrastructure)
- GitHub Actions (CI/CD)
