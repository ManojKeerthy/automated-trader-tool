# TradeCraft — Agent Instructions

> Version: 2.0.0 | Last Updated: **2026-08-06**

## Before Any Substantial Work

1. **Read [docs/PROJECT_STATUS.md](../docs/PROJECT_STATUS.md) FIRST.** It is authoritative
   and supersedes every other status document, cycle-closure certificate and milestone
   narrative in this repository.
2. Read this file (`AGENT_INSTRUCTIONS.md`)
3. Read `PROJECT_MEMORY.md` (carries a supersession notice)
4. Read relevant `docs/` policy documents
5. Read applicable `docs/adr/` ADRs
6. Inspect existing implementation and tests

## ⚠️ Do Not Trust The Historical Record

An independent audit on 2026-08-06 found that Research Cycles 1 and 2 ran entirely against a
**synthetic price database** generated inside this repository and stamped
`source='ZERODHA_KITE_EOD'`. Roughly 250 governance documents, SHA-256 certificates and
forensic audits attest to results that are artifacts.

Consequences for you:

- **Never cite an M3A–M3G result, gate verdict, or graveyard entry as evidence.** Documents
  carrying a `VOID — SYNTHETIC DATA` banner have zero evidentiary weight.
- **Prefer artifacts to prose.** Narrative documents in this repo were found to contain
  figures that contradict the JSON they claim to summarise, and to attribute P&L to
  instruments that never existed in the database. When prose and data disagree, the data
  wins — and say so.
- **Verify before asserting status.** Check `config/research_governance_state.json` and query
  the database rather than repeating a claim from a document.

## Standing Rules Adopted From Real Failures

1. **Provenance is a property of the numbers, never of a label.** A `source` column is worth
   nothing. `data verify` (the authenticity gate) is blocking before any research run.
2. **No metric may gate a decision unless a unit test proves it correct on a hand-computed
   fixture** with known winners, losers, and a force-closed position.
3. **Fix defects as classes, not instances.** Cycle 2 found a missing-exit bug and fixed one
   site; the same defect sat in all four Cycle 1 strategies and went unnoticed for a cycle.
   A fix is not complete until every site with the same pattern is found and cleared.
4. **Every result names its source database** (`BacktestResult.data_provenance`).
5. **Prefer assertions in code to certificates in prose.**
6. **Never pin a content hash of the market data.** It cannot distinguish tampering from
   correction; here it actively blocked ingesting real data.
7. **Unmeasurable is not zero.** Exclude and report coverage; never substitute 0.0.

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
- When making changes, update docs/PROJECT_STATUS.md and config/research_governance_state.json
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
