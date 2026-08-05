# M3ER.6 — EXIT LOGIC & HOLDING PERIOD VERIFICATION AUDIT REPORT

> **ENGINEERING VERDICT**: **`EXIT_LOGIC_REQUIRES_FIX`**  
> **DISCOVERED CODE DEFECT**: Interface parameter omission in `EarningsDriftV1Strategy.evaluate()`  
> **READ-ONLY COMPLIANCE**: **`100% READ-ONLY (ZERO SOURCE CODE EDITS)`**

---

## 1. EXECUTIVE SUMMARY & ROOT CAUSE DISCOVERY

Milestone **M3ER.6** completed a read-only engineering audit to resolve the 871-day holding period warning discovered in M3ER.5.

### Discovered Code Defect
In [earnings_drift_v1.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/strategy/earnings_drift_v1.py#L60):

```python
def evaluate(self, current_date: date, data_portal: DataPortal) -> list[SignalIntent]:
    return self.generate_signals(current_date, data_portal)
```

In [engine.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/backtesting/engine.py#L315):

```python
signals = config.strategy.evaluate(current_date, portal)
```

When `BacktestEngine` invokes `evaluate()`, `evaluate()` delegates to `generate_signals(current_date, data_portal)` **without passing `active_positions`**.

Consequently:
- `active_positions` defaults to `None`.
- `active_positions_set` evaluates to `set()`.
- Line 86 (`if sec_uuid in active_positions_set:`) is **NEVER satisfied**.
- `self._bars_held` counter was **NEVER incremented** during backtest simulation.
- The 30-session time exit (`MAX_HOLDING_PERIOD`) was **NEVER evaluated** for any trade in Development (M3D.4R) or Validation (M3ER).

---

## 2. IMPACT ON DEVELOPMENT & VALIDATION RESULTS

| Backtest Run | Total Trades | STOP_LOSS Exits | MAX_HOLDING_PERIOD Exits | FORCE_CLOSE Exits | Holding Period Explanation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Development (M3D.4R)** | 20 | 10 | **0** | 10 | 10 trades hit ATR stop; remaining 10 held until FORCE_CLOSE at end-of-backtest. |
| **Validation (M3ER)** | 10 | 0 | **0** | 10 | Zero trades hit ATR stop (100% win rate); all 10 held until FORCE_CLOSE (871 calendar days). |

---

## 3. ANSWERS TO AUDIT QUESTIONS

1. **Is 30-session exit logic functioning?**: Code logic exists in `generate_signals()`, but was **bypassed at runtime** because `evaluate()` omitted the `active_positions` parameter.
2. **Is FORCE_CLOSE acting as primary exit?**: Yes. For all winning trades, `FORCE_CLOSE` unintentionally became the sole exit mechanism.
3. **Is 871-day holding period explained?**: Fully explained. Positions entered in Feb 2022 and were never evaluated for time exits, holding until `FORCE_CLOSE` on June 28, 2024.
4. **Is there an implementation defect?**: Yes (`EXIT_LOGIC_REQUIRES_FIX`). Passing `active_positions` to `generate_signals()` will restore true 30-session time exits.

---

## 4. HARD STOP CONFIRMATION

- Zero source code changes made during M3ER.6. Codebase remains untouched.
- `VALIDATION` access count: `1` (Sealed).
- `FINAL TEST` access count: `0` (Sealed).
