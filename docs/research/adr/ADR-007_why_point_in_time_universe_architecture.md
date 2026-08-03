# ADR-007: WHY POINT-IN-TIME UNIVERSE ARCHITECTURE IS MANDATORY

## Status
Accepted

## Context
Standard backtesting engines use current index constituent lists for historical backtests, introducing severe survivorship bias (companies that were demoted or went bankrupt are ignored).

## Decision
TradeCraft enforces a Point-in-Time Universe Architecture where index membership queries on date $T$ return strictly the securities that were constituents on date $T$.

## Consequences
- **Positive**: Complete elimination of survivorship bias.
- **Positive**: Out-of-sample research results reflect true historical investability.
