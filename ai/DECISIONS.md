# TradeCraft — Decisions Log

> Last Updated: 2026-07-28

## Decision Record

| # | Date | Decision | Rationale | Document |
|---|------|----------|-----------|----------|
| 1 | 2026-07-28 | Modular monolith architecture | Single user, single dev, complexity not justified | [ADR-001](../docs/adr/ADR-001-modular-monolith.md) |
| 2 | 2026-07-28 | Python + React + PostgreSQL + Docker | Best quant/AI ecosystem, rich UI, reliable DB | [ADR-002](../docs/adr/ADR-002-technology-stack.md) |
| 3 | 2026-07-28 | BrokerInterface with Paper/Zerodha adapters | Structural paper/live safety | [ADR-003](../docs/adr/ADR-003-paper-live-separation.md) |
| 4 | 2026-07-28 | Deterministic risk/compliance, AI advisory only | Safety, reliability, auditability | [ADR-004](../docs/adr/ADR-004-deterministic-vs-ai-boundaries.md) |
| 5 | 2026-07-28 | UTC storage + explicit Asia/Kolkata | Cross-timezone correctness | [ADR-005](../docs/adr/ADR-005-data-timezone-handling.md) |
| 6 | 2026-07-28 | Cross-platform portability | Dev on Windows, prod on Linux | [ADR-006](../docs/adr/ADR-006-cross-platform-portability.md) |
| 7 | 2026-07-28 | Immutable strategy versions | Auditability, reproducibility | [ADR-007](../docs/adr/ADR-007-strategy-versioning.md) |
| 8 | 2026-07-28 | Human approval with autonomous protective stops | Safety with human oversight | [ADR-008](../docs/adr/ADR-008-human-approval-workflow.md) |
| 9 | 2026-07-28 | RISK LOCK (10%) + KILL SWITCH | Emergency capital preservation | [ADR-009](../docs/adr/ADR-009-risk-lock-kill-switch.md) |
| 10 | 2026-07-28 | AI provider abstraction, pooled ₹2,500/month | Flexibility, cost control | [ADR-010](../docs/adr/ADR-010-ai-provider-abstraction.md) |
| 11 | 2026-07-28 | Zerodha Kite Connect for market data (M1+) | User has Kite dev account, adequate for daily OHLCV | Resolved Q2 |
| 12 | 2026-07-28 | NSE official calendar + exchange_calendars lib | Layered verification approach | Resolved Q1 |
| 13 | 2026-07-28 | NSE as primary corporate actions source | Official, free, adequate for V1 | Resolved Q7 |
| 14 | 2026-07-28 | GitHub Actions for CI/CD | Multi-OS support, standard for GitHub | Resolved Q6 |
| 15 | 2026-07-28 | Conservative risk parameters for paper trading | Capital preservation priority, ₹50K portfolio | [RISK_POLICY.md](../docs/RISK_POLICY.md) |
| 16 | 2026-07-28 | Nifty 50 as initial universe | Liquidity, data quality, manageable scope | [SD-001](../docs/strategy-decisions/SD-001-initial-universe.md) |
