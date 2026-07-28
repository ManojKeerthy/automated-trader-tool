# TradeCraft — Known Limitations

> Last Updated: 2026-07-28
> Status: ACTIVE

Below are the known limitations of the TradeCraft platform identified during the Milestone M1 (Market Data Foundation) implementation and post-completion audit.

## 1. Broker API Limitations

### No Official Zerodha Sandbox
- **Limitation**: Zerodha Kite Connect does **not** provide an official sandbox, paper trading, or virtual testing environment.
- **Impact**: All direct API contract testing must be run against a live production account. Order placement tests cannot be run on a fake/simulated broker API without risking real capital unless placed after hours or with intentionally insufficient balance.
- **Resolution**:Differentiate strictly between:
  - **Internal Paper Broker**: Fully local, offline, deterministic simulations of order fills and P&L tracking (Default mode).
  - **Kite Connect Integration**: Only used for real-money execution in Milestone M11 after rigorous shadow trading validation.

## 2. Market Data Limitations

### Point-in-Time Nifty 50 Membership
- **Limitation**: `POINT-IN-TIME NIFTY 50 MEMBERSHIP NOT YET VERIFIED`. The system currently retrieves and tracks active (current) Nifty 50 constituent lists.
- **Impact**: Running historical backtests using today's constituents introduces **survivorship bias** (the backtest artificially benefits from selecting companies that survived and succeeded, skewing results higher).
- **Resolution**: Point-in-time membership tracking (historical index additions/deletions) is a blocker and must be engineered in Milestone M2 before conducting historical backtests.

### Corporate Actions Data Scraping
- **Limitation**: Scraping the official NSE corporate actions circulars and JSON endpoints is highly fragile due to Cloudflare protection, rate-limiting, and frequent structural changes to the exchange site.
- **Impact**: Live automated corporate action ingestion might fail or yield empty sets under strict network protections.
- **Resolution**: The schema and provider interface support splits, dividends, bonuses, rights, and symbol changes. However, live ingestion is a foundation only. Robust live action feeds require manual loading circular checks or upgrading to a paid data vendor subscription (requires user budget approval).

## 3. Platform Limitations

### Multi-OS Compatibility
- **Limitation**: Development occurs on Windows, while production deployment target is Linux (Docker).
- **Impact**: File path handling, timezone settings, and subprocesses must remain strictly OS-independent.
- **Resolution**: Always use Python's `pathlib` for absolute path concatenation and enforce timezone awareness explicitly on all datetimes.
