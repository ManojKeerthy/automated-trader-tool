# TradeCraft — Automated Swing Trading for Indian Equities

> **Goal:** an automated swing-trading tool that places real orders on Zerodha Kite under
> human approval and makes money net of costs. The research platform below is the machinery
> for finding something worth trading — it is not the product.

### 👉 Status: [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) — read this before anything else

**Current position (2026-08-06):** real NSE data ingested for the first time (142
instruments, 387,874 bars, 2014–2026). Research Cycles 1 and 2 are **void** — they ran
against a synthetic price series generated inside this repo, so their conclusions are
artifacts, not findings. Four engine defects fixed. **No validated strategy exists and no
order-placement code exists yet.** See the [audit](docs/research/REPO_AUDIT_2026-08-06.md).

---

> **Institutional Algorithmic Trading & Quantitative Research Infrastructure for Indian Equities**

TradeCraft is an institutional-grade quantitative research and backtesting platform built for Indian equities (NSE NIFTY 50, NIFTY 100, NIFTY 200, NIFTY 250, NIFTY 500). It features point-in-time universe management, strict data firewall enforcement, cryptographic experiment tracking, an institutional alpha library, and zero-tolerance double-entry cash accounting.

---

## 🏛️ Project State & Current Milestone

- **Current Completed Milestone**: `M3D.4.5 — INDEPENDENT FORENSIC BACKTEST AUDIT`
- **DEVELOPMENT Phase Status**: **`PERMANENTLY_FROZEN_IMMUTABLE_CLOSED`** ([ADR-017](file:///c:/infiligence/automated-trader-tool/docs/research/adr/ADR-017_DEVELOPMENT_PHASE_PERMANENT_FREEZE.md))
- **Active Strategy**: `EarningsDriftV1Strategy` ([src/tradecraft/strategy/earnings_drift_v1.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/strategy/earnings_drift_v1.py))
- **Survivor Gate Verdict**: **`DEVELOPMENT_SURVIVOR`** (Profit Factor `2.50`, Expectancy `+0.31R`, Net P&L `₹5,10,000.00`)
- **Forensic Audit Verdict**: **`GO_FOR_VALIDATION`** (5/5 pre-registered criteria passed)
- **Trade Ledger SHA-256 Checksum**: `72414b3adb3cc21f29a275a7ccc8819328b56e584ea80f0cc1801fc8cd1d4bd8`
- **Dataset Boundaries**:
  - `DEVELOPMENT` (`2016-08-01` $\rightarrow$ `2021-12-31`): **FROZEN & CLOSED**
  - `VALIDATION` (`2022-01-01` $\rightarrow$ `2024-06-30`): **100% SEALED** (`VALIDATION_ACCESS_COUNT = 0`)
  - `FINAL TEST` (`2024-07-01` $\rightarrow$ `2026-07-28`): **100% SEALED** (`FINAL_TEST_ACCESS_COUNT = 0`)

---

## 📚 Master Knowledge Base Navigation

Explore the complete self-documenting institutional knowledge base:

| Documentation Manual | Description | Link |
| :--- | :--- | :--- |
| **Master Documentation Index** | Master directory of all project documentation | [docs/INDEX.md](file:///c:/infiligence/automated-trader-tool/docs/INDEX.md) |
| **Project Overview** | Vision, high-level architecture, & philosophies | [docs/OVERVIEW.md](file:///c:/infiligence/automated-trader-tool/docs/OVERVIEW.md) |
| **Getting Started** | Setup, installation, environment, & commands | [docs/GETTING_STARTED.md](file:///c:/infiligence/automated-trader-tool/docs/GETTING_STARTED.md) |
| **Architecture Guide** | Deep dive into all 15+ platform subsystems | [docs/ARCHITECTURE.md](file:///c:/infiligence/automated-trader-tool/docs/ARCHITECTURE.md) |
| **Architectural Timeline** | Milestone-by-milestone system evolution & ADRs | [docs/ARCHITECTURE_TIMELINE.md](file:///c:/infiligence/automated-trader-tool/docs/ARCHITECTURE_TIMELINE.md) |
| **Operational Runbook** | Day-to-day procedures, audits & maintenance | [docs/RUNBOOK.md](file:///c:/infiligence/automated-trader-tool/docs/RUNBOOK.md) |
| **Repository Manifest** | Directory structure, ownership & immutability | [docs/REPOSITORY_MANIFEST.md](file:///c:/infiligence/automated-trader-tool/docs/REPOSITORY_MANIFEST.md) |
| **Complete Research History** | Complete milestone history (M1 to M3D.4.5) | [docs/RESEARCH_HISTORY.md](file:///c:/infiligence/automated-trader-tool/docs/RESEARCH_HISTORY.md) |
| **Current Project State** | Authoritative state snapshot & SHA-256 fingerprint | [docs/CURRENT_PROJECT_STATE.md](file:///c:/infiligence/automated-trader-tool/docs/CURRENT_PROJECT_STATE.md) |
| **Governance Manual** | Firewall rules, Graveyard, & admission gates | [docs/GOVERNANCE_MANUAL.md](file:///c:/infiligence/automated-trader-tool/docs/GOVERNANCE_MANUAL.md) |
| **Research Playbook** | Step-by-step hypothesis workflow (Idea $\rightarrow$ Live) | [docs/RESEARCH_PLAYBOOK.md](file:///c:/infiligence/automated-trader-tool/docs/RESEARCH_PLAYBOOK.md) |
| **Permanent Decision Log** | Major design decisions, rejected alternatives | [docs/DECISION_LOG.md](file:///c:/infiligence/automated-trader-tool/docs/DECISION_LOG.md) |
| **Future Roadmap** | Multi-year roadmap (Validation, M4, M5, M6) | [docs/FUTURE_ROADMAP.md](file:///c:/infiligence/automated-trader-tool/docs/FUTURE_ROADMAP.md) |
| **Contributor Guide** | Engineering standards, testing, mypy & ruff | [docs/CONTRIBUTING.md](file:///c:/infiligence/automated-trader-tool/docs/CONTRIBUTING.md) |
| **Research & Platform FAQ** | Comprehensive quantitative research FAQ | [docs/FAQ.md](file:///c:/infiligence/automated-trader-tool/docs/FAQ.md) |
| **Documentation Audit Report** | Coverage report confirming zero gaps | [docs/DOCUMENTATION_AUDIT_REPORT.md](file:///c:/infiligence/automated-trader-tool/docs/DOCUMENTATION_AUDIT_REPORT.md) |

---

## ⚡ Quick Start & Verification

```bash
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Run mypy strict type checker
.venv\Scripts\python.exe -m mypy src/tradecraft

# 3. Run ruff linter
.venv\Scripts\python.exe -m ruff check src

# 4. Run unit test suite
.venv\Scripts\python.exe -m pytest tests/ -v --ignore=tests/integration
```