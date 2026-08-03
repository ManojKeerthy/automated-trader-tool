# ADR-014: WHY THE AUTOMATED BENCHMARK SUITE IS MANDATORY

## Status
Accepted

## Context
Strategies that report positive absolute returns may be underperforming market benchmarks or simpler coin-flip / random entry baselines.

## Decision
Every backtest experiment is automatically evaluated against standard quantitative baselines (Buy & Hold NIFTY, Equal Weight, Random Entry, Coin Flip, SMA200 Trend, Previous Best).

## Consequences
- **Positive**: Prevents false optimism by proving true risk-adjusted excess alpha.
