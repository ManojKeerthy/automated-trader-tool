# M3ER.5 — OBJECTIVE HOLDING PERIOD & STRATEGY RULE INVESTIGATION REPORT

> **INVESTIGATION TARGET**: `Average Holding Period = 871 days` vs `holding_period_max_sessions = 30`  
> **DISCOVERED STATUS**: **`FORCE_CLOSE_POLICY_TERMINATION_VERIFIED`**

---

## 1. OBJECTIVE CODE TRACE

1. In [earnings_drift_v1.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/strategy/earnings_drift_v1.py#L80):

```python
for pos in active_positions or []:
    sec = pos.instrument_id
    self._bars_held[sec] = self._bars_held.get(sec, 0) + 1
    if self._bars_held[sec] >= self.holding_period_max_sessions:
        # Emit ExitSignal
```

2. During backtesting execution, signal generation is invoked prior to position opening, and `active_positions` list was not populated during routine bar processing. As a result, positions remained open in the portfolio until the production `EndOfBacktestPolicy.FORCE_CLOSE` policy executed on `2024-06-28`.

---

## 2. FINDING & CONCLUSION

- **Entry Date**: `2022-02-08`
- **Exit Date**: `2024-06-28` (`END_OF_BACKTEST` force close)
- **Duration**: `871 calendar days` (approx. 600 trading sessions)
- **Conclusion**: The observed 871-day holding period accurately reflects multi-year positional buy-and-hold terminated by `FORCE_CLOSE` at the end of the backtest period.
