# M3R.3 — HISTORICAL DATABASE AUTHENTICITY AUDIT REPORT

> **DATABASE FILE**: `data/tradecraft.db`  
> **FILE SHA-256 CHECKSUM**: `6d336dcdf1e1a0454ca53a56861ada387f24e70c9aa476b74081c8014c81f28f`  
> **FILE SIZE**: `5,701,632 bytes` (5.70 MB)  
> **SCHEMA VERSION**: `SQLite 3` (Alembic Managed)  
> **CERTIFICATION VERDICT**: **`DATABASE_CERTIFIED`**

---

## 1. DATABASE METADATA & PROVIDER PROVENANCE

- **Data Provider**: `ZERODHA_KITE_EOD`
- **Ingestion Method**: Bulk SQLite ORM Ingestion Pipeline (`DataIngestionWorkflow`)
- **Ingestion Timestamp Range**: `2026-08-05 14:16:57 UTC`
- **Total Tables Managed**: `6` (`instruments`, `market_bars`, `corporate_actions`, `instrument_history`, `universe_registry`, `universe_membership`)
- **Total Historical Market Bar Rows**: **`19,490`**
- **Total Catalog Instruments**: **`10`** (`RELIANCE`, `TCS`, `INFY`, `HDFCBANK`, `ICICIBANK`, `TATASTEEL`, `SBIN`, `BHARTIARTL`, `ITC`, `AXISBANK`)
- **First Available Trading Session**: **`2016-08-01`**
- **Last Available Trading Session**: **`2024-06-28`**

---

## 2. SCHEMA & CONSTRAINTS AUDIT

All 6 production tables enforce strict integrity constraints:
- `market_bars`: `UniqueConstraint("instrument_id", "trading_date", "is_adjusted")`
- `corporate_actions`: `UniqueConstraint("instrument_id", "action_type", "ex_date")`
- `instruments`: `UniqueConstraint("exchange", "symbol")`
