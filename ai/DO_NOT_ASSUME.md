# TradeCraft — Do Not Assume

> Last Updated: 2026-07-28
>
> Things that MUST be verified from authoritative sources. Never rely on AI memory.

## Regulatory
- ❌ Do NOT assume current SEBI regulations from AI memory — verify from sebi.gov.in
- ❌ Do NOT assume RBI governs securities trading merely because the project is in India
- ❌ Do NOT assume current tax rates — verify from official sources
- ❌ Do NOT assume personal API trading is exempt from algo trading regulations

## Broker
- ❌ Do NOT assume Kite Connect API endpoints, limits, or behaviour — use official docs
- ❌ Do NOT assume current Zerodha fee schedule — verify from zerodha.com/charges
- ❌ Do NOT assume Kite Connect session management — follow documented auth flow
- ❌ Do NOT assume API rate limits — verify from Kite Connect documentation

## Market Data
- ❌ Do NOT assume historical data is correctly adjusted for corporate actions
- ❌ Do NOT assume Monday–Friday = trading day (check NSE calendar)
- ❌ Do NOT assume all Nifty 50 stocks have complete historical data
- ❌ Do NOT assume Yahoo Finance or free data sources are accurate for Indian markets

## Trading
- ❌ Do NOT assume a strategy works because it is popular or commonly cited
- ❌ Do NOT assume backtest results predict future performance
- ❌ Do NOT assume statistical significance from small sample sizes
- ❌ Do NOT assume transaction costs are negligible

## Technology
- ❌ Do NOT assume floating-point determinism across platforms
- ❌ Do NOT assume a Python library works on Windows, macOS, AND Linux without checking
- ❌ Do NOT assume timezone behaviour — always use explicit timezone-aware operations

## Implementation
- ❌ Do NOT claim functionality is implemented because documentation describes it
- ❌ Do NOT assume modules have working code — most are empty stubs
- ❌ Do NOT assume database schema exists — no migrations have been created
