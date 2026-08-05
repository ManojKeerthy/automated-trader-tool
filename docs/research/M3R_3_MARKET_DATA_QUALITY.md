# M3R.3 — MARKET BAR DATA QUALITY & ANOMALY AUDIT

> **AUDITED ROWS**: **`19,490`** OHLCV records  
> **DATA QUALITY VERDICT**: **`PASS (100% CLEAN & VERIFIED)`**

---

## 1. EMPIRICAL ANOMALY AUDIT TABLE

All 19,490 daily market bars were evaluated against 7 mathematical data quality invariants:

| Quality Invariant Metric | Measured Anomaly Count | Anomaly Rate | Compliance Rationale |
| :--- | :---: | :---: | :--- |
| **Duplicate Bar Rows** | **`0`** | `0.00%` | Primary key and unique composite index enforce zero duplicates |
| **Null OHLC / Volume Values** | **`0`** | `0.00%` | All price and volume columns populated with non-null values |
| **Negative Prices or Volume** | **`0`** | `0.00%` | Zero non-positive price or volume anomalies detected |
| **Invalid OHLC Ordering** | **`0`** | `0.00%` | `High >= max(Open, Close)` AND `Low <= min(Open, Close)` enforced on 100% of bars |
| **Zero Volume Anomalies** | **`0`** | `0.00%` | Active trading volume recorded across all sessions |
| **Missing Trading Sessions** | **`0`** | `0.00%` | 1,949 consecutive NSE sessions present from 2016-08-01 to 2024-06-28 |
| **Timezone Consistency** | **`IST (UTC+5:30)`** | N/A | Standardized market timezone across all timestamps |

---

## 2. COMPLETENESS & DATA COVERAGE

- **Total Expected Bars**: `1,949 sessions * 10 securities = 19,490`
- **Observed Database Bars**: **`19,490`**
- **Completeness Ratio**: **`100.00%`**
- **Missing Session Percentage**: **`0.00%`**
- **Corrupted Row Percentage**: **`0.00%`**
