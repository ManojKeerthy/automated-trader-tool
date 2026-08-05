# M3R.1 — FINANCIAL METRIC PROVENANCE TRACE

This document traces the exact, unbroken mathematical provenance of a single reported metric (**Profit Factor**) through the TradeCraft software stack:

```
[ Step 1: Historical Market Data ]
SQLite Database Table: market_bars
Columns: (instrument_id, trading_date, open, high, low, close, volume)
      │
      ▼
[ Step 2: Data Portal Query ]
File: src/tradecraft/market_data/portal.py
Function: DataPortal.get_daily_bars(instrument_id, date)
      │
      ▼
[ Step 3: Backtest Engine Event Loop ]
File: src/tradecraft/backtesting/engine.py
Function: BacktestEngine.run(config)
Process: Evaluates strategy rules on daily bars -> fills orders -> records BacktestTrade
      │
      ▼
[ Step 4: BacktestResult Creation ]
File: src/tradecraft/backtesting/engine.py
Attribute: BacktestResult.trades = List[BacktestTrade]
Each BacktestTrade object contains:
  - gross_pnl: Decimal
  - total_fees: Decimal
  - net_pnl = gross_pnl - total_fees - slippage_cost
      │
      ▼
[ Step 5: Metric Calculation in Runner ]
File: scratch/run_m3d_4_development_backtest.py
Code:
  winning_trades = [t for t in trades if t.net_pnl > 0]
  losing_trades = [t for t in trades if t.net_pnl <= 0]
  gross_profit_sum = sum(t.net_pnl for t in winning_trades)
  gross_loss_sum = abs(sum(t.net_pnl for t in losing_trades))
  profit_factor = float(gross_profit_sum / gross_loss_sum)
      │
      ▼
[ Step 6: JSON Output ]
File: scratch/m3d_4_development_results.json
Field: "performance_metrics": { "profit_factor": 2.28 }
      │
      ▼
[ Step 7: Markdown Research Report ]
File: docs/research/m3d_4_development_backtest.md
Table: | Profit Factor | 2.28 | >= 1.30 | SURVIVOR |
```

---

## Provenance Verification Result
The chain is **100% UNBROKEN**. No step injects hard-coded values, random generation, or mock fallbacks.
