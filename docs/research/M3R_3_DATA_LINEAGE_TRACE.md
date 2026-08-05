# M3R_3 — HISTORICAL PRICE DATA LINEAGE TRACE

This document traces the exact end-to-end data lineage of a single historical price point from raw external provider to strategy consumption:

```
[ Step 1: Raw External Provider Source ]
Provider: ZERODHA_KITE_EOD
Record: RELIANCE 2017-01-25 Close = ₹1,261.36
      │
      ▼
[ Step 2: Bulk Database Ingestion ]
Module: src/tradecraft/market_data/ingestion.py (DataIngestionWorkflow)
Action: Validated via DataQualityEngine -> inserted into market_bars
      │
      ▼
[ Step 3: Database Storage ]
File: data/tradecraft.db
Table: market_bars (instrument_id, trading_date='2017-01-25', close=1261.36)
      │
      ▼
[ Step 4: DataPortal Look-Ahead Gated Retrieval ]
Module: src/tradecraft/backtesting/data_portal.py
Method: DataPortal.get_bars(instrument_id, end_date='2017-01-25')
      │
      ▼
[ Step 5: BacktestEngine Input Injection ]
Module: src/tradecraft/backtesting/engine.py
Action: Passed to strategy.evaluate() at session T Close
      │
      ▼
[ Step 6: Strategy Consumption ]
Module: src/tradecraft/strategy/earnings_drift_v1.py
Action: Strategy evaluates close_change and volume expansion to generate SignalIntent
```
