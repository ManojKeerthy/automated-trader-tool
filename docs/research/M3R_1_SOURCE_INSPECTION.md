# M3R.1 — INDEPENDENT SOURCE CODE INSPECTION REPORT

This document presents the detailed line-by-line inspection evidence for all 3 active research runner scripts in the TradeCraft repository.

---

## 1. `scratch/run_m3d_4_development_backtest.py`

- **Line 46**: `engine = BacktestEngine(db_session=db_session, calendar=calendar)`
- **Line 47**: `result = engine.run(config)`
- **Line 50**: `trades = result.trades`
- **Line 58**: `gross_profit_sum = sum((t.net_pnl for t in winning_trades_list), Decimal("0"))`
- **Line 59**: `gross_loss_sum = abs(sum((t.net_pnl for t in losing_trades_list), Decimal("0")))`
- **Line 62**: `profit_factor_ratio = round(float(gross_profit_sum / gross_loss_sum), 2)`
- **Line 72**: `residual_error_val = float(abs(equity_diff - net_pnl_realized))`
- **Verdict**: 100% Execution-Derived via `BacktestEngine.run(config)`.

---

## 2. `scratch/run_m3d_4_5_forensic_audit.py`

- **Line 47**: `engine = BacktestEngine(db_session=db_session, calendar=calendar)`
- **Line 48**: `result = engine.run(config)`
- **Line 49**: `trades = result.trades`
- **Line 52-69**: Exports `trade_ledger` directly from `trades` list attributes (`t.instrument_symbol`, `t.direction`, `t.net_pnl`, `t.total_fees`, `t.slippage_cost`).
- **Line 86-98**: Deterministic cyclic permutation resampling on actual `t["net_pnl_inr"]` values (Zero `random.seed` or `random.choices`).
- **Verdict**: 100% Execution-Derived from `BacktestResult.trades`.

---

## 3. `scratch/run_m3e_validation_backtest.py`

- **Line 33-46**: Cryptographic checksum verification against `m3e_0_validation_manifest.json` before execution.
- **Line 67**: `engine = BacktestEngine(db_session=db_session, calendar=calendar)`
- **Line 68**: `result = engine.run(config)`
- **Line 71**: `trades = result.trades`
- **Line 81-85**: Calculates `profit_factor`, `expectancy_r`, `residual_error`, `max_drawdown_pct`, and `sharpe_ratio` directly from `result`.
- **Verdict**: 100% Execution-Derived via `BacktestEngine.run(config)` on sealed VALIDATION split.
