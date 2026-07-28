# TradeCraft — Known Limitations

> Last Updated: 2026-07-28

## Current Limitations (M0)

### 1. No Executable Code
The project currently contains only documentation and empty module stubs. No trading logic, data ingestion, database schema, or UI exists.

### 2. Historical Nifty 50 Composition
Reliable free sources for point-in-time historical Nifty 50 constituent lists are limited. This is a prerequisite for survivorship-bias-free backtesting.

**Impact**: Backtests (M2) may have survivorship bias unless historical composition data is obtained.

**Mitigation**: Collect NSE index reconstitution notices; if insufficient, evaluate paid data sources.

### 3. Zerodha Historical Data Quality
Zerodha Kite Connect historical data has not been validated for backtesting suitability. Known potential issues:
- Corporate action adjustments may be inconsistent
- Very old historical data may have gaps
- Data quality for delisted stocks is unknown

**Impact**: Research quality (M2) depends on data quality.

**Mitigation**: Data quality checks designed; if inadequate, propose paid provider.

### 4. Transaction Cost Rates Unverified
Approximate transaction cost rates are documented but not verified against current Zerodha and regulatory fee schedules.

**Impact**: Backtest cost model (M2) may be slightly inaccurate.

**Mitigation**: Verify before production use; rates are adequate for initial paper research.

### 5. SEBI Algo Trading Classification Unknown
Whether personal systematic trading via Kite Connect API constitutes "algorithmic trading" under SEBI's current framework is unresolved.

**Impact**: May require additional compliance measures before live trading.

**Mitigation**: Research before M6 (Compliance System) and M11 (Live Integration).

### 6. Small Capital Constraints
₹50,000 starting capital limits:
- Number of positions (stocks cost ₹100–₹3,000+ per share)
- Diversification potential
- Minimum position size economics

**Impact**: Some strategies may not be viable at this capital level.

**Mitigation**: Position sizing accounts for minimum quantity; strategies must work with available capital.

### 7. Cross-Platform Numerical Determinism
Floating-point arithmetic may produce slightly different results across Windows/Linux/macOS due to compiler/library differences.

**Impact**: Trading decisions could theoretically differ across platforms.

**Mitigation**: Use `decimal.Decimal` for financial calculations; document tolerances; test cross-platform equivalence.
