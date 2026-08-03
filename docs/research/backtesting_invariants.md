# TRADECRAFT PERMANENT BACKTESTING INVARIANTS

> **TECHNICAL SPECIFICATION**: Mandatory software and research invariants enforced across all TradeCraft backtesting components.

---

## 1. POINT-IN-TIME CLOCK GATING
- All market data, OHLCV bars, corporate action adjustments, and universe membership lookups MUST be accessed exclusively via `DataPortal`.
- `DataPortal` enforces `_current_date` clock gating. Any query attempting to access dates $> \text{\_current\_date}$ raises `LookAheadError`.

## 2. PIVOT & INDICATOR CONFIRMATION LAG
- Pivot high/low features or Donchian channel boundaries calculated over lookback windows must exclude the current session bar if the current bar is incomplete, or enforce a lag of $T + \text{right\_bars}$ sessions to prevent lookahead bias.

## 3. SIGNAL TO EXECUTION TIMING
- Signals generated at Date $T$ market close are submitted to the execution simulator for execution on Date $T+1$ or later.
- Every completed trade MUST satisfy `assert signal_date < entry_date <= exit_date`.

## 4. CAPITAL & POSITION SIZING
- No negative cash balances.
- No implicit or explicit leverage ($\text{Exposure} \le \text{Total Equity}$).
- Position sizing uses integer share quantities (`quantity >= 1`). Unsized signals default to 0 trades unless processed by `ResearchSizingCalculator`.

## 5. ACCOUNTING CONSERVATION IDENTITY
- All comparative backtests enforce `EndOfBacktestPolicy.FORCE_CLOSE`.
- Realised Net P&L across all trade ledger entries must strictly equal equity change:  
  $$\text{Final Equity} - \text{Initial Capital} \equiv \sum_{t \in \text{Trades}} \text{TradeRecord.net\_pnl}(t) \quad (\le ₹0.0001 \text{ residual})$$

## 6. TRANSACTION COSTS & SLIPPAGE
- Costs must use `IndianEquityDeliveryCostModel` (STT 0.1% buy/sell, Exchange turn charges 0.00345%, SEBI turnover fee 0.0001%, Stamp duty 0.015% buy, GST 18% on charges, DP charge ₹15.93 per sell transaction).
- Slippage uses `FixedBasisPointSlippage` (5 bps standard), embedded directly into execution fill prices.

## 7. DATASET FIREWALL
- `DevelopmentDataFirewall` enforces strict date boundary checks.
- `DEVELOPMENT`: `2016-08-01` $\rightarrow$ `2021-12-31`
- `VALIDATION`: `2022-01-01` $\rightarrow$ `2024-06-30` (SEALED)
- `FINAL TEST`: `2024-07-01` $\rightarrow$ `2026-07-28` (SEALED)
- Queries to Validation or Final Test during Development research raise `DataBoundaryViolationError`.
