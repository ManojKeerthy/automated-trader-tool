# TRADECRAFT AUTHENTICITY GUARANTEE & SCIENTIFIC INTEGRITY CONTRACT

> **GUARANTEE LEVEL**: **`100% EXECUTION-DERIVED`**  
> **VERIFIER MODULE**: `src/tradecraft/research/authenticity_verifier.py`

---

## 1. THE TRADECRAFT AUTHENTICITY PRINCIPLE

TradeCraft guarantees that **zero reported performance figures, P&L amounts, trade ledgers, or decision gate outcomes are illustrative, synthetic, mocked, or hard-coded**.

Every research report generated after Milestone M3R.0 is mathematically bound to historical market data executed through `BacktestEngine.run(config)`.

---

## 2. FOUR-POINT INDEPENDENT AUDIT VERIFICATION

An independent auditor can verify any published research output by checking four immutable invariants:

1. **Database Price Invariant**: Every price used during backtesting originates from `market_bars` database records.
2. **Engine Invocation Invariant**: Every backtest execution invokes `BacktestEngine.run(config)` under `FORCE_CLOSE` policy.
3. **Trade Ledger Invariant**: Every trade record originates from `BacktestResult.trades`.
4. **Metric Derivation Invariant**: Every metric (Profit Factor, Sharpe, Expectancy, Drawdown) is derived dynamically from `BacktestResult`.

---

## 3. ARCHIVED PROTOTYPE REPORT NOTICE

All milestone reports generated prior to Milestone M3R.0 (`m3d_4_development_backtest.md`, `m3d_4_5_forensic_audit.md`, `m3e_validation_report.md`) are retained strictly for engineering timeline history and are explicitly marked **`INVALID FOR RESEARCH`**.
