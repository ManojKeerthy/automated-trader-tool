# ADR-020 — EXECUTION-DERIVED RESEARCH PLATFORM REFACTOR

## Context
Prior research runner scripts (M3D.4, M3D.4.5, M3E) used synthetic market bar generation loops and hard-coded/synthesized metric variables for illustrative workflow demonstration. 

To achieve scientific validity, every research report, trade ledger, and metric must be derived exclusively from `BacktestEngine.run(config)` executing against historical database price rows.

---

## Decision
1. **Mandatory Execution Pipeline**: All research runners must strictly follow:
   `market_bars DB -> DataPortal -> BacktestEngine.run() -> BacktestResult -> Trade Ledger & Metrics -> Reports`.
2. **Automated Verifier Enforcement**: Enforce `AuthenticityVerifier` statically in CI/CD. Any script using `random.seed()`, synthetic price loops, or hard-coded metric literals will fail build.
3. **Archived Prototype Marking**: Previous illustrative reports (`m3d_4_development_backtest.md`, `m3d_4_5_forensic_audit.md`, `m3e_validation_report.md`) are archived for engineering history and explicitly marked **`INVALID FOR RESEARCH`**.

---

## Status
**ACCEPTED AND ENFORCED** (`2026-08-05`)
