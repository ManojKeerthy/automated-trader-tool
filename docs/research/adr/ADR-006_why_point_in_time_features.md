# ADR-006: WHY POINT-IN-TIME FEATURE ACCESS VIA DATAPORTAL IS MANDATORY

## Status
Accepted

## Context
Strategies that access future price bars, restated financial statements, or future index constituent membership introduce subtle, catastrophic lookahead bias.

## Decision
All market data access during research backtesting MUST occur through `DataPortal`, which gates queries to the current simulation clock date `_current_date`. Index membership queries use `PointInTimeUniverse`.

## Consequences
- **Positive**: Complete programmatic protection against forward-looking data leakage.
- **Enforcement**: Any query attempting to access dates $> \text{\_current\_date}$ raises `LookAheadError`.
