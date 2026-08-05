# ADR-021: Execution-Derived Validation Governance Lock & Preflight Protection

## Status
**ACCEPTED & ENACTED** (2026-08-05)

## Context
Following the completion of Milestone M3D.4R (Authoritative Execution-Derived DEVELOPMENT Backtest) and Milestone M3D.4.5R (Forensic Audit), the quantitative research platform must establish an immutable governance lock before executing out-of-sample testing on the sealed `VALIDATION` dataset (`2022-01-01` $\rightarrow$ `2024-06-30`).

## Decision
1. **Immutable Artifact Lock**: SHA-256 fingerprints for all 15 production files, data models, engine components, and DEVELOPMENT research artifacts are frozen in `scratch/m3e_0r_validation_manifest.json`.
2. **Mandatory Execution Preflight Gate**: The M3ER validation runner MUST verify that all 15 SHA-256 checksums, `VALIDATION_ACCESS_COUNT == 0`, and `AuthenticityVerifier` pass before reading any VALIDATION bar.
3. **Pre-Registered Decision Thresholds**:
   - Profit Factor $\ge 1.30$
   - Expectancy $\ge +0.25R$
   - Sharpe Ratio $\ge 0.50$
   - Maximum Drawdown $\le 25.0\%$
   - Residual Accounting Error $= 0.0000$ INR
   - Minimum Trade Count $\ge 15$
4. **Environment Reproducibility Metadata**: Recorded Python `3.11.9`, OS `Windows-10`, Git commit `f9ec5330...`, SQLite `3.45.1`, Timezone `UTC`, and Seed `42`.

## Consequences
- Zero code modifications or parameter tuning permitted prior to or during M3ER execution.
- If preflight gate fails or any decision gate is breached, the strategy family is permanently retired with zero retries.
