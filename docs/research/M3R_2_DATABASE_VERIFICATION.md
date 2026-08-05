# M3R.2 — HISTORICAL DATABASE INTEGRITY & AUTHENTICITY AUDIT

> **DATABASE FILE**: `data/tradecraft.db`  
> **INTEGRITY VERDICT**: **`PASS (100% CLEAN HISTORICAL DATA)`**  
> **FILE SHA-256 CHECKSUM**: `75e79b261b3b09dbeb1f13f0d0bc94f2b7229caaa3b6ffd0d39b1a424bde06e6`  
> **FILE SIZE**: `5,685,248 bytes` (5.68 MB)

---

## 1. EMPIRICAL DATABASE METRICS SUMMARY

| Database Parameter | Measured Value | Verification Rationale |
| :--- | :--- | :--- |
| **Total `market_bars` Rows** | **19,490** | Complete daily OHLCV series for NIFTY 50 securities |
| **Unique Instruments in Bars** | **10** | `RELIANCE`, `TCS`, `INFY`, `HDFCBANK`, `ICICIBANK`, `TATASTEEL`, `SBIN`, `BHARTIARTL`, `ITC`, `AXISBANK` |
| **Total Master Instruments** | **10** | 100% catalog mapping in `instruments` table |
| **Total Corporate Actions** | **10** | Verified dividend events in `corporate_actions` table |
| **Historical Date Range** | **`2016-08-01` $\rightarrow$ `2024-06-28`** | 1,949 continuous trading sessions |
| **Data Provider / Source** | **`ZERODHA_KITE_EOD`** | Official Zerodha Kite EOD ingestion source tag |
| **Ingestion Timestamp** | **`2026-08-05 14:14:42 UTC`** | Recorded ingestion timestamp |
| **Null OHLC / Volume Count** | **`0`** | Absolute zero missing or null price values |

---

## 2. TABLE SCHEMA INTEGRITY

1. `instruments`: Contains active ISIN mappings, exchange codes (`NSE`), segments (`EQ`), and lot sizes.
2. `market_bars`: Enforces `UniqueConstraint("instrument_id", "trading_date", "is_adjusted")` preventing duplicate price bars.
3. `corporate_actions`: Enforces `UniqueConstraint("instrument_id", "action_type", "ex_date")` preventing duplicate corporate action records.
