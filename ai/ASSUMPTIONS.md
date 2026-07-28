# TradeCraft — Assumptions

> Last Updated: 2026-07-28
>
> These are explicit assumptions. Each must be validated before depending on it.

## Validated Assumptions

| # | Assumption | Validated By | Date |
|---|------------|-------------|------|
| 1 | User has a Zerodha Kite Connect developer account | User statement | 2026-07-28 |
| 2 | Starting paper capital is ₹50,000 | Constitution | 2026-07-28 |
| 3 | Primary development platform is Windows | Constitution | 2026-07-28 |
| 4 | User is comfortable with Python and React | Constitution (experienced developer) | 2026-07-28 |

## Unvalidated Assumptions

| # | Assumption | Risk if Wrong | Validation Method | Blocks |
|---|------------|---------------|-------------------|--------|
| 5 | Zerodha Kite Connect provides sufficient daily OHLCV historical data for Nifty 50 | Need alternative data provider | Test with API subscription | M1 |
| 6 | NSE publicly accessible corporate action data is adequate for initial needs | Need paid data provider | Test during M1 data collection | M1 |
| 7 | `exchange_calendars` library accurately reflects NSE trading days | Calendar errors in backtesting | Validate against 2+ years of official NSE holidays | M1 |
| 8 | Docker Desktop is available on user's Windows machine | Need alternative PostgreSQL setup | User confirmation | M1 |
| 9 | Python 3.11+ is available on user's machine | Need installation | User confirmation | M1 |
| 10 | Zerodha equity delivery brokerage is ₹0 | Incorrect cost model | Verify on zerodha.com/charges | M2 |
| 11 | STT rate for equity delivery is 0.1% (buy+sell) | Incorrect cost model | Verify from SEBI/Zerodha | M2 |
| 12 | Personal API-based systematic trading does not require SEBI algo trading registration | Major compliance issue | Research SEBI regulations | M6 |
