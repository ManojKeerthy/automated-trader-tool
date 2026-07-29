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

## 4. M2 Research & Backtesting Limitations

### Configurable DP Charges & Settlement Simplification
- **Limitation**: DP charges are modeled as once per ISIN/security per trading day for normal delivery sells (configurable per `BrokerCostProfile`, e.g. standard ₹13+GST=₹15.34 or primary holder ₹12.75+GST=₹15.05). Real Zerodha settlement behavior has exceptional edge cases where multiple DP debits could theoretically occur (such as auction market clearing, physical delivery shortages, or multi-settlement holiday scenarios).
- **Resolution**: These exceptional settlement edge cases are OUT OF SCOPE for the current EOD swing backtester and are recorded as a known simplification. Account-level profiles allow configuring the base DP rate while recording the assumption in backtest metadata.

### Historical Risk-Free Rate Assumptions
- **Limitation**: Historical 91-day Government of India Treasury Bill yield data before 2026 is currently evaluated using the current rate assumption (~5.35% per annum) unless point-in-time rates are explicitly provided.
- **Impact**: Backtests record `CURRENT_RATE_ASSUMPTION` in metrics metadata until point-in-time RBI time-series yields are ingested.

### Historical Universe Membership Gating
- **Limitation**: Universe membership prior to verified constituent tracking dates carries `UNVERIFIED` confidence.
- **Impact**: Backtests executed over unverified universe date ranges are automatically classified as `UNVERIFIED` or `RESEARCH_ONLY` research quality and cannot produce `TRUSTWORTHY` classification until historical constituent additions/deletions are verified against authoritative exchange circulars.

## 5. M3A Research & Screening Limitations

### Liquidity Threshold Provisional Default
- **Limitation**: The ₹5 Crore 20-session average daily traded-value threshold is a provisional research default. It has not been validated as an industry-standard or optimal threshold.
- **Impact**: Screening results may exclude viable mid-cap opportunities or include illiquid micro-caps under different market regimes.
- **Resolution**: `LiquidityScreenConfig` makes thresholds configurable and records the threshold version in screening metadata. Sensitivity analysis will be conducted in M3B.

### Fundamental and News Data Source Integration
- **Limitation**: Fundamental data (`AbstractFundamentalDataProvider`) and News data (`AbstractNewsDataProvider`) interfaces are defined with point-in-time enforcement (`available_from <= query_date`), but default to null providers (`NullFundamentalDataProvider`, `NullNewsDataProvider`).
- **Impact**: Fundamental metrics and news events return unavailable/empty results. No unreliable web scraping or unverified AI web search is permitted.
- **Resolution**: Interface schemas preserve point-in-time correctness. Real external provider integrations require explicit data source authorization.

### Pivot Point Confirmation Delay
- **Limitation**: Pivot highs and lows require `right_bars` future bars to confirm. Pivots are NOT available on the peak/trough date itself ($T$) but only on the confirmation date ($T + \text{right\_bars}$).
- **Impact**: Pivot-based support/resistance levels lag price movement by `right_bars` sessions. Attempting to access unconfirmed pivots at $T$ is gated as a look-ahead error.
- **Resolution**: Point-in-time semantics ensure support/resistance features only use confirmed pivots.

### Market Breadth Quality Dependencies
- **Limitation**: Market breadth calculation (% of constituents above MA) requires verified constituent universe membership.
- **Impact**: Computing breadth using current constituents for historical dates assigns `UNVERIFIED_UNIVERSE` quality to the breadth component, preventing the overall market regime from achieving `TRUSTWORTHY` classification.
- **Resolution**: Regime snapshots explicitly track `breadth_quality` and `overall_quality`.

