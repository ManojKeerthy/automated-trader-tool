# M3D.4.5R2 — STATISTICAL ROBUSTNESS & MONTE CARLO REVIEW

> **ANALYSIS TYPE**: 1,000-Run Monte Carlo Bootstrap Resampling & Winner Sensitivity Audit

---

## 1. 1,000-RUN MONTE CARLO BOOTSTRAP PERCENTILES

| Metric | 5th Percentile (P5) | 50th Percentile (Median) | 95th Percentile (P95) |
| :--- | :---: | :---: | :---: |
| **Net Realized P&L** | -₹476,047.73 | -₹389,008.80 | -296,098.66 |
| **CAGR** | -11.25% | -8.70% | -6.28% |
| **Profit Factor** | 0.34 | 0.43 | 0.53 |

---

## 2. OUTLIER WINNER REMOVAL SENSITIVITY AUDIT

| Sensitivity Scenario | Net P&L (INR) | Impact Description |
| :--- | :---: | :--- |
| **Baseline (All 330 Trades)** | -₹389,893.56 | Complete execution-derived baseline |
| **Without Top 1 Winner** | -₹396,985.11 | Net P&L degrades by -₹7,091.55 |
| **Without Top 3 Winners** | -₹410,581.23 | Net P&L degrades by -₹20,687.67 |
| **Without Top 5 Winners** | -₹423,577.73 | Net P&L degrades by -₹33,684.17 |

---

## 3. STATISTICAL CONCLUSION

Across all 1,000 bootstrap iterations, the 95th percentile CAGR remains negative (-6.28%), proving that the negative edge is statistically robust and not caused by isolated outlier trades.
