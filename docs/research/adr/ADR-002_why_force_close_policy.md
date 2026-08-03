# ADR-002: WHY END_OF_BACKTEST_POLICY = FORCE_CLOSE FOR RESEARCH COMPARISON

## Status
Accepted

## Context
When a backtest simulation ends on date $T_{\text{end}}$, some positions may remain open. If open positions are valued using mark-to-market prices without liquidating, unrealized paper P&L is mixed with realized trade ledger P&L, creating accounting residuals and distorting trade-level metrics.

## Decision
All comparative research backtests strictly enforce `EndOfBacktestPolicy.FORCE_CLOSE`, liquidating any open positions on the final session of the backtest period with explicit sell fees and slippage applied.

## Consequences
- **Positive**: Guarantees exact double-entry accounting conservation: $\text{Final Equity} - \text{Initial Capital} \equiv \sum \text{TradeRecord.net\_pnl}$ ($\le ₹0.0001$).
- **Positive**: 100% of backtest P&L is realized and represented in completed trade ledger records.
- **Invariant Enforced**: `final_snapshot.open_positions == 0`.
