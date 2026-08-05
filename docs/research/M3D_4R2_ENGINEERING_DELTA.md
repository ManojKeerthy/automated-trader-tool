# M3D.4R2 — SCIENTIFIC ENGINEERING DELTA ANALYSIS

> **COMPARISON**: `M3D.4R (Defective Original)` vs `M3D.4R2 (Repaired Corrected)`  
> **ANALYSIS TYPE**: **`CAUSAL ENGINEERING EXPLANATION`**

---

## 1. COMPARATIVE PERFORMANCE & METRIC DELTA MATRIX

| Metric | Original M3D.4R (Defective) | Corrected M3D.4R2 (Repaired) | Absolute Delta | Causal Engineering Explanation |
| :--- | :---: | :---: | :---: | :--- |
| **Total Trades** | 20 | **330** | +310 | Active position parameter repair enabled continuous signal evaluation across all constituents instead of stalling after initial entry. |
| **Win Rate** | 100.0% | **32.12%** | -67.88% | 30-session `MAX_HOLDING_PERIOD` time exit closed trades after 30 sessions rather than allowing positions to sit open indefinitely across 5+ years of market drift. |
| **Net P&L** | +₹1,648,593.90 | **-₹389,893.56** | -₹2,038,487.46 | The defective M3D.4R holding behavior passively rode secular bull market drift on NIFTY 50 blue chips over 5.4 years. Re-entering on every PEAD surge with 30-session exits exposes the true strategy edge on large caps. |
| **CAGR** | +19.71% | **-8.72%** | -28.43% | Annualized return reflects realistic 30-session momentum drift performance. |
| **Profit Factor** | 999.99 | **0.42** | -999.57 | Realized gross profits (₹286,894.36) vs realized gross losses (₹676,787.92). |
| **Expectancy ($R$)** | +82.43R | **-0.10R** | -82.53R | Net loss per trade under active trading rules. |
| **Max Drawdown** | 10.80% | **43.82%** | +33.02% | Peak-to-trough decline resulting from sequential losing trades during market pullbacks. |
| **Avg Holding Days** | 960.0 | **24.9** | -935.1 | Holding period dramatically reduced from multi-year `FORCE_CLOSE` holding to true 30 trading sessions (~42-45 calendar days). |
| **MAX_HOLDING_PERIOD Exits** | 0 | **180** | +180 | Time exits successfully executed at session 30 as pre-registered. |
| **STOP_LOSS Exits** | 10 | **150** | +140 | ATR stop-loss exits triggered dynamically during adverse price movements. |
| **FORCE_CLOSE Exits** | 10 | **0** | -10 | Zero positions required liquidating at end-of-backtest boundary because all positions exited naturally. |

---

## 2. KEY ENGINEERING TAKEAWAY

In the defective M3D.4R implementation, omitting `active_positions` prevented the strategy from tracking session counts, causing 10 positions to remain open for 1,300+ trading sessions until `FORCE_CLOSE` at dataset end. Because NIFTY 50 blue-chip equities appreciated substantially over 2016–2021, passive holding produced an artificial +19.71% CAGR.

When the pre-registered 30-session exit logic was activated in M3D.4R2, the strategy executed 330 trades with a 32.12% win rate and -8.72% CAGR. This proves that raw single-factor PEAD momentum entry without market regime filters fails to generate positive alpha on NIFTY 50 large-cap stocks over 30-session holding windows.
