# M3D.4R2 — RESEARCH LINEAGE SUPERSEDENCE NOTICE

> **NOTICE TYPE**: **`FORMAL SUPERSEDENCE OF PRIOR DEVELOPMENT & VALIDATION RESULTS`**  
> **EFFECTIVE DATE**: `2026-08-05`  
> **AUTHORITATIVE BASELINE**: **`M3D.4R2 IS NOW THE SOLE AUTHORITATIVE DEVELOPMENT BASELINE`**

---

## 1. SUPERSEDED RESEARCH ARTIFACTS

The following research milestones and their associated reports, trade ledgers, equity curves, and certificates are **FORMALLY SUPERSEDED** and retained strictly as engineering history:

1. **M3D.4R** (`scratch/m3d_4r_results.json`): Initial execution-derived DEVELOPMENT backtest.
2. **M3D.4.5R** (`scratch/m3d_4_5r_research_ledger.json`): Initial forensic audit of M3D.4R.
3. **M3ER** (`scratch/m3er_results.json`): Initial VALIDATION backtest (`VALIDATION_ACCESS_COUNT = 1`).
4. **M3ER.5** (`scratch/m3er_5_metric_audit.json`): Initial audit of M3ER results.

---

## 2. SCIENTIFIC REASON FOR SUPERSEDENCE

All 4 superseded milestones were generated using a strategy implementation (`earnings_drift_v1.py:60`) that contained an interface parameter omission defect. Because `active_positions` was not propagated into `generate_signals()`, the `_bars_held` counter remained stuck at 0, preventing the 30-session `MAX_HOLDING_PERIOD` time exit from executing during backtesting simulations.

Following the engineering remediation in **M3R.4** and independent defect closure certification in **M3R.5**, **M3D.4R2** represents the first true evaluation of the pre-registered PEAD hypothesis.

---

## 3. GOVERNANCE MANDATE

From this milestone onward:
- No scientific comparison, research paper, or deployment decision may reference M3D.4R or M3ER as valid strategy metrics.
- **M3D.4R2** is established as the sole authoritative baseline for Development research.
