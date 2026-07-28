# SD-001: Initial Trading Universe — Nifty 50

**Status**: ACCEPTED
**Date**: 2026-07-28

## Decision

The initial trading universe is the **Nifty 50** — the 50 largest and most liquid stocks on the National Stock Exchange of India.

## Rationale

1. **Liquidity**: Nifty 50 stocks are the most liquid on NSE, minimising slippage
2. **Data quality**: Best data coverage and reliability
3. **Manageable scope**: 50 stocks is large enough for diversification, small enough for a beginning system
4. **Benchmark**: Nifty 50 TRI serves as a natural performance benchmark
5. **Corporate actions**: Well-documented corporate action history

## Survivorship Bias Defense

The universe must be **point-in-time correct** for backtesting:
- Historical backtests use the Nifty 50 composition as it was at each point in time
- Stocks that were removed from the index must be included in historical universes
- Stocks that were delisted must be included (with appropriate handling)

### Challenge
Reliable free sources for historical Nifty 50 composition changes are limited. This is a known data quality risk.

### Mitigation
- NSE publishes index reconstitution notices
- Collect and persist historical composition changes
- If reliable point-in-time data cannot be obtained, document the limitation in backtest results

## Future Universe Expansion

After the Nifty 50 system is validated:
- Nifty Next 50
- Nifty 100
- Sector-specific screening
- Broad-market Indian ETFs (after regulatory validation)

Each expansion requires its own strategy decision record.
