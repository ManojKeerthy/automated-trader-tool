# ADR-017 — PERMANENT FREEZE OF DEVELOPMENT RESEARCH PHASE FOR RESEARCH CYCLE 2

## Context
Following successful completion of:
- Hypothesis Pre-Registration (`hypo-cycle2-alpha013-v1`)
- Pure Code Implementation (`EarningsDriftV1Strategy`)
- Blind Signal Viability Audit & Signal Sanity Audit (`M3D.3`)
- Single Authoritative DEVELOPMENT Backtest (`M3D.4` — Verdict: `DEVELOPMENT_SURVIVOR`)
- Independent Forensic Backtest Audit & Monte Carlo Simulation (`M3D.4.5` — Verdict: `GO_FOR_VALIDATION`)

The DEVELOPMENT dataset research phase for `EarningsDriftV1Strategy` must be permanently sealed to prevent data mining, post-hoc parameter tuning, and overfitting.

---

## Decision
1. **Permanent Freeze**: The `DEVELOPMENT` research dataset (`2016-08-01` to `2021-12-31`) is **PERMANENTLY FROZEN, IMMUTABLE, AND CLOSED**.
2. **Strict Exception Rule**: No further strategy code changes, parameter tuning, indicator retries, forensic analyses, or statistical queries on `DEVELOPMENT` data are permitted without a formal written governance exception.
3. **Immutable Fingerprint Lock**: The 180-trade DEVELOPMENT backtest ledger is locked to SHA-256 fingerprint:  
   `72414b3adb3cc21f29a275a7ccc8819328b56e584ea80f0cc1801fc8cd1d4bd8`
4. **Authorized Activity**: The ONLY remaining authorized research activity is the Validation phase on the sealed Validation dataset (`2022-01-01` to `2024-06-30`), which requires explicit user approval before execution.

---

## Status
**ACCEPTED AND ENFORCED** (`2026-08-03`)
