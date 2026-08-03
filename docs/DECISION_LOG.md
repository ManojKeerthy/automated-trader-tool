# PERMANENT ARCHITECTURAL DECISION LOG

This document logs all major architectural choices, rejected alternatives, and key engineering lessons:

| Decision ID | Date | Decision | Rationale | Alternatives Rejected | Associated ADR |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **DEC-001** | 2026-07-28 | Event-Driven Backtesting Engine | Exact simulation of order routing & cash balances | Vectorized backtesters (lookahead risk) | ADR-002 |
| **DEC-002** | 2026-07-29 | Point-in-Time Universe Architecture | Completely eliminates survivorship bias | Static universe lists (survivorship bias) | ADR-012 |
| **DEC-003** | 2026-08-03 | Public Research SDK Interface | Exposes single clean API for notebooks & scripts | Importing internal modules directly | ADR-013 |
| **DEC-004** | 2026-08-03 | Research Graveyard & Novelty Engine | Blocks recycling of failed strategy lineages | Parameter retries on failed strategies | ADR-015 |
| **DEC-005** | 2026-08-03 | 100% Financial Blinding in M3D.3 | Prevents premature reaction to P&L | Early P&L inspection (overfitting) | ADR-016 |
| **DEC-006** | 2026-08-03 | Permanent Freeze of DEVELOPMENT Phase | Sealing DEVELOPMENT data post forensic audit | Multiple DEVELOPMENT backtest iterations | ADR-017 |
