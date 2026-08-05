# ADR-018 — VALIDATION GOVERNANCE LOCK & IMMUTABLE EXECUTION CONTRACT

## Context
Following the completion and permanent freezing of the `DEVELOPMENT` research phase (M3D.4.5, ADR-017), `EarningsDriftV1Strategy` (`hypo-cycle2-alpha013-v1`) is ready for Validation testing.

To prevent out-of-sample data leakage, parameter tuning, or goalpost moving, all versioned dependencies, software components, parameter values, and quantitative success criteria must be frozen into an immutable contract prior to unsealing the Validation dataset (`2022-01-01` to `2024-06-30`).

---

## Decision
1. **Validation Governance Lock**: Enact a permanent governance lock freezing the entire execution stack for `EarningsDriftV1Strategy`:
   - Strategy SHA-256: `a32d5a97cbf4dbefbb920ff782622021f6dc0a121b2bd1ab27a1945e618ca813`
   - Backtest Engine SHA-256: `d098affd9b5fb98a5274659688fdd62ef42e96404282606db43c7de06dcd551c`
   - Research SDK SHA-256: `adafb41c4923d8bac01fbc2ba7c4b7defab81aae8f3a9845636230a6426095df`
   - Feature Store SHA-256: `b5fcb96a8e1df5cccce25fdbf986322ae17894e5058859b6e255953bb777c375`
   - Security Master SHA-256: `b43262a836cee3a0992a2e1a6316521c68d1c12242061f668753ebee4e3a230e`
   - Audited Trade Ledger SHA-256: `72414b3adb3cc21f29a275a7ccc8819328b56e584ea80f0cc1801fc8cd1d4bd8`

2. **Immutable Gate Thresholds**:
   - Expectancy ($R$) $\ge +0.20\text{R}$
   - Profit Factor $\ge 1.25$
   - Sharpe Ratio $\ge 1.20$
   - Max Drawdown $\le 20.0\%$
   - Residual Cash Error $= ₹0.0000$ (Exact)
   - Executed Trades $\ge 30$

3. **One-Shot Evaluation Rule**: Validation testing is strictly ONE-SHOT. No parameter tuning, retries, or post-hoc adjustments are permitted. Failure to meet all gate criteria results in automatic locking of `strat_earnings_drift_v1` into the Research Graveyard.

---

## Status
**ACCEPTED AND ENFORCED** (`2026-08-05`)
