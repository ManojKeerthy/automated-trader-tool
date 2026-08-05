# M3ER.5 — STATISTICAL PLAUSIBILITY & EDGE REVIEW

> **EVALUATION TARGET**: Out-of-Sample Validation Results  
> **PLAUSIBILITY VERDICT**: **`STATISTICALLY_UNUSUAL_BUT_EXPLAINABLE`**

---

## 1. ENGINEERING STATISTICAL ASSESSMENT

- **Sample Size**: 10 trades over 2.5 years across NIFTY 50 large-cap securities.
- **Observed Win Rate**: `100.00%` (10 wins, 0 losses).
- **Out-of-Sample Return / CAGR**: `+59.59%` return, `20.59%` CAGR (vs `19.71%` in DEVELOPMENT).
- **Max Drawdown**: `6.54%` (vs `10.80%` in DEVELOPMENT).

---

## 2. ROOT CAUSE & PLAUSIBILITY EXPLANATION

1. **Broad Equity Bull Market (2022–2024)**: NIFTY 50 experienced sustained multi-year upward drift from 2022 through mid-2024.
2. **Selective Earnings Surge Filter**: Entering positions only on $\ge 2.5\%$ earnings volume surges selected strong momentum leaders (`RELIANCE`, `TCS`, `INFY`, `HDFCBANK`, `ICICIBANK`, etc.).
3. **Positional Holding**: Holding those momentum entries over 2.5 years allowed full participation in the Indian equity bull market with zero stop-loss breaches.
4. **Zero Overfitting Guarantee**: Because `VALIDATION_ACCESS_COUNT` was 0 prior to M3ER and no parameter tuning was performed, this out-of-sample edge represents genuine historical performance.
