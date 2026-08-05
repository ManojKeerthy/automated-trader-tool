# DATA LINEAGE & TRACEABILITY SPECIFICATION

This document details the exact end-to-end data lineage for every quantitative research output produced by the TradeCraft platform:

```
+-------------------------------------------------------------+
| Raw Market Data Ingestion (Zerodha Kite / Market Data API) |
+-------------------------------------------------------------+
                              │
                              ▼
            +-----------------------------------+
            | SQLite / PostgreSQL Database      |
            | Table: market_bars                |
            +-----------------------------------+
                              │
                              ▼
            +-----------------------------------+
            | DataPortal & PointInTimeUniverse  |
            +-----------------------------------+
                              │
                              ▼
            +-----------------------------------+
            | BacktestEngine.run(BacktestConfig)|
            +-----------------------------------+
                              │
                              ▼
            +-----------------------------------+
            | BacktestResult Object             |
            |  - trades: List[BacktestTrade]    |
            |  - equity_curve: List[Snapshot]   |
            |  - metrics: Dict[str, float]      |
            +-----------------------------------+
                              │
                              ▼
            +-----------------------------------+
            | Exported Reports & JSON Artifacts |
            +-----------------------------------+
```
