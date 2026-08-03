# ADR-005: WHY THREE STRICTLY SEPARATED HISTORICAL DATASETS ARE REQUIRED

## Status
Accepted

## Context
Evaluating quantitative trading strategies on the same historical data used for hypothesis generation leads to severe curve-fitting and out-of-sample failure in live trading.

## Decision
TradeCraft enforces three strictly separated, chronological historical datasets:
1. `DEVELOPMENT` (`2016-08-01` $\rightarrow$ `2021-12-31`): Used for hypothesis testing and gate evaluation.
2. `VALIDATION` (`2022-01-01` $\rightarrow$ `2024-06-30`): **SEALED**. Used ONLY for single out-of-sample validation of Development survivors.
3. `FINAL TEST` (`2024-07-01` $\rightarrow$ `2026-07-28`): **SEALED**. Used ONLY for final pre-production validation.

## Consequences
- **Positive**: Strict protection against out-of-sample data contamination and curve-fitting.
- **Enforcement**: Runtime `DevelopmentDataFirewall` raises `DataBoundaryViolationError` for unauthorized date queries.
