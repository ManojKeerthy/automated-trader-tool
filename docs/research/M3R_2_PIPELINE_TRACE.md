# M3R.2 — SINGLE TRADE END-TO-END PIPELINE PROVENANCE TRACE

This document details the exact, unbroken step-by-step runtime trace of a single trade executed during the M3R.2 engineering dry run:

---

## 1. EXECUTED SAMPLE TRADE DETAILS

- **Trade ID**: `1`
- **Instrument Symbol**: `RELIANCE`
- **Direction**: `BUY`
- **Signal Date**: `2017-01-25`
- **Entry Execution Date**: `2017-01-27` (T+1 Open)
- **Exit Execution Date**: `2017-06-30` (End of backtest window force-close)
- **Quantity**: `80 shares`
- **Entry Fill Price**: `₹1,261.36`
- **Exit Fill Price**: `₹1,410.30`
- **Gross P&L**: `₹11,915.25`
- **Total Fees (STT + Charges)**: `₹252.20`
- **Slippage Cost (5bps)**: `₹56.44`
- **Net Realized P&L**: **`₹11,663.05`**
- **Exit Reason**: `END_OF_BACKTEST`

---

## 2. UNBROKEN 7-STEP RUNTIME EXECUTION PROVENANCE CHAIN

```
[ Step 1: Database Market Bar Retrieval ]
File: data/tradecraft.db
Query: SELECT open, high, low, close, volume FROM market_bars WHERE symbol='RELIANCE' AND trading_date='2017-01-25'
      │
      ▼
[ Step 2: DataPortal Filtering ]
File: src/tradecraft/backtesting/data_portal.py
Method: DataPortal.get_history(sec_uuid, current_date, count=20)
Action: Returns 20 sorted daily bars without look-ahead leakage.
      │
      ▼
[ Step 3: Strategy Signal Evaluation ]
File: src/tradecraft/strategy/earnings_drift_v1.py
Method: EarningsDriftV1Strategy.generate_signals(current_date, data_portal)
Condition: 2.5% price surge detected on 2017-01-25 + 2.5x volume expansion.
Output: SignalIntent(instrument_id=sec_uuid, direction="BUY", order_type="MARKET", stop_loss=₹1,235.12)
      │
      ▼
[ Step 4: Engine Order Routing & Execution ]
File: src/tradecraft/backtesting/engine.py & execution.py
Method: ExecutionSimulator.execute_order() at 2017-01-27 T+1 Open
Fill Price: ₹1,261.36 (incorporating 5bps slippage & statutory fees)
      │
      ▼
[ Step 5: Trade Record Construction ]
File: src/tradecraft/backtesting/trade_ledger.py
Output: BacktestTrade object instantiated and appended to BacktestResult.trades.
      │
      ▼
[ Step 6: Double-Entry Journal Cash Balance Update ]
File: src/tradecraft/backtesting/portfolio.py
Action: Debit Cash account, Credit Position asset account. Net P&L added to cash upon exit.
      │
      ▼
[ Step 7: Daily Equity Snapshot ]
File: src/tradecraft/backtesting/portfolio.py
Output: EquitySnapshot recorded in BacktestResult.equity_curve (Total Equity = ₹1,113,956.85).
```

---

## 3. PROVENANCE VERDICT
**UNBROKEN**. The trade originated 100% from historical database price rows processed through production engine components.
