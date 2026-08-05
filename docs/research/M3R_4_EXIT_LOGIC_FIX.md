# M3R.4 — EXIT LOGIC DEFECT REMEDIATION & INTERFACE CONTRACT SPECIFICATION

> **REMEDIATION STATUS**: **`INTERFACE_CONTRACT_REPAIRED_AND_VERIFIED`**  
> **AUTOMATED REGRESSION TESTS**: **`6/6 PASSED (100% PASS)`**  
> **CODE MINIMALITY**: **`MINIMAL ARCHITECTURAL REPAIR (ZERO STRATEGY PARAMETER EDITS)`**

---

## 1. PREVIOUS VS CORRECTED INTERFACE CONTRACT

### Previous Interface Contract (Defective)
- `Strategy.evaluate(current_date: date, data_portal: DataPortal) -> Any`
- `EarningsDriftV1Strategy.evaluate(current_date, data_portal)` called `self.generate_signals(current_date, data_portal)` without passing `active_positions`.
- `BacktestEngine.run()` invoked `strategy.evaluate(current_date, portal)` without position context.
- **Defect Result**: `active_positions` defaulted to `None`, `self._bars_held` counter was never incremented, and 30-session time exits were bypassed.

### Corrected Interface Contract (Remediated)
- `Strategy.evaluate(current_date: date, data_portal: DataPortal, active_positions: list[uuid.UUID] | None = None) -> Any`
- `EarningsDriftV1Strategy.evaluate(current_date, data_portal, active_positions=active_positions)` propagates `active_positions` to `generate_signals()`.
- `BacktestEngine.run()` passes `active_positions = list(portfolio.positions.keys())` on daily simulation steps.
- **Remediation Result**: Active positions increment `self._bars_held` by 1 per trading session, emitting `ExitSignal(reason="MAX_HOLDING_PERIOD")` on session 30 and deleting the counter entry upon exit.

---

## 2. AFFECTED FILES & BACKWARD COMPATIBILITY

- [src/tradecraft/strategy/base.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/strategy/base.py#L143): Added `active_positions: list[uuid.UUID] | None = None` to `Strategy.evaluate` Protocol.
- [src/tradecraft/strategy/earnings_drift_v1.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/strategy/earnings_drift_v1.py#L60): Updated `evaluate()` and emitted `ExitSignal(reason="MAX_HOLDING_PERIOD")` on session 30 with counter reset (`del self._bars_held[sec_uuid]`).
- [src/tradecraft/backtesting/engine.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/backtesting/engine.py#L315): Passed `active_position_uuids = list(portfolio.positions.keys())` during daily signal evaluation.

**Backward Compatibility Assessment**: 100% Backward Compatible. Optional `active_positions` default (`None`) preserves functionality across all existing platform strategy classes.
