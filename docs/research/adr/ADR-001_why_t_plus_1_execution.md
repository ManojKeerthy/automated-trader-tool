# ADR-001: WHY T+1 EXECUTION FOR DAILY SIGNAL STRATEGIES

## Status
Accepted

## Context
In daily swing trading backtesting, strategies evaluate technical indicators at the close of trading session $T$. A common backtesting bug involves filling orders at session $T$ close price, which requires knowing the close price before the close occurs (lookahead bias).

## Decision
All daily strategy signals generated at session $T$ close are strictly executed at session $T+1$ open or later (`signal_date < entry_date <= exit_date`).

## Consequences
- **Positive**: Eliminates lookahead bias completely. Guarantees physical executability in real market conditions.
- **Negative**: Exposes the strategy to overnight gap risk between session $T$ close and session $T+1$ open fill.
- **Invariant Enforced**: `assert signal_date < entry_date <= exit_date` across all completed trades.
