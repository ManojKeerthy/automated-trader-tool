# KNOWN RESEARCH MISTAKES WE NEVER REPEAT

> **RESEARCH SCARS REGISTRY**: Institutional memory of research mistakes, cognitive traps, and methodological errors discovered during Research Cycle 1.

---

## MISTAKE #0: NEVER VERIFYING THAT THE MARKET DATA WAS REAL

> **THE MISTAKE THAT INVALIDATED TWO ENTIRE RESEARCH CYCLES.** Discovered 2026-08-06.

- **Symptom**: Two full research cycles, ~250 governance documents, 21 ADRs, SHA-256 database
  certificates, dataset firewalls, and an "Authenticity Guarantee" — all reporting that no
  strategy could be made profitable.
- **Reality**: `data/tradecraft.db` was populated by `scratch/seed_real_market_bars.py`, a
  deterministic price generator. Every bar was synthetic while stamped
  `source = 'ZERODHA_KITE_EOD'`. The generator emits a repeating 21-day sawtooth,
  **identical across all 10 instruments**, with `open == close` on every bar, a constant
  2.4%-of-price ATR, and volume as a linear counter. Expected gross edge is exactly zero for
  any rule; net P&L is therefore exactly minus friction. Failure was guaranteed by construction.
- **Why every audit missed it**: `AUTHENTICITY_GUARANTEE.md` verified that prices came *from
  the database* and that metrics came *from `BacktestEngine.run()`*. It never verified that the
  database contained real market data. Every control tested **internal consistency**; none
  tested **external validity**.
- **Permanent Lesson**: Provenance is not a string column. Before any hypothesis is evaluated,
  the input data must pass an adversarial authenticity gate that a synthetic series would fail:
  cross-sectional return correlation < 0.9, dispersion in per-symbol volatility, `open != close`
  on >95% of bars, non-constant high/low ratios, fat tails, and known historical events present
  (e.g. a ≥25% index drawdown in Q1 2020). Make it a blocking precondition in `preflight.py`.
- **Meta-Lesson**: The volume of governance documentation was inversely correlated with the
  validity of the research. A 20-line test would have caught this on day one; 250 markdown
  files did not. **Prefer assertions in code over certificates in prose.**

---

## MISTAKE #1: ASSUMING MORE INDICATOR FILTERS PRODUCES BETTER SIGNALS
- **Symptom**: Combining multiple strict technical filters (RSI <= 45 AND ATR distance <= 1.0 AND Close > SMA50 AND Donchian High on a single daily bar).
- **Reality**: Caused extreme **signal scarcity** and filter collision. Most trading sessions yielded 0 signals, starving the strategy of sample size.
- **Permanent Lesson**: Structural context filters (trend) and entry trigger filters (resumption/reversal) must operate as sequential state transitions rather than simultaneous single-bar AND constraints.

---

## MISTAKE #2: INTERPRETING GROSS EDGE BEFORE CHECKING TRANSACTION FRICTION
- **Symptom**: Celebrating positive gross P&L (+₹108.90k in Breakout V2, +₹138.55k in Mean Reversion V2) prior to subtracting Indian equity delivery costs and slippage.
- **Reality**: Transaction costs (STT, exchange fees, SEBI, GST, stamp duty, DP charges) and 5 bps slippage eroded 49.1% of Breakout V2's gross gains, reducing net P&L to +₹55.45k (PF 1.09).
- **Permanent Lesson**: Never evaluate signal edge without full, explicit friction deduction embedded in the execution pipeline.

---

## MISTAKE #3: TRUSTING ZERO-TRADE BACKTESTS WITHOUT PIPELINE INSTRUMENTATION
- **Symptom**: Assuming a strategy had 0 trades because "no signals occurred" or "market conditions were unsuitable".
- **Reality**: Forensic audit (M3B.2.1) revealed 32,822 confirmed signals were generated, but dropped to 0 executed trades because `SignalIntent.quantity_hint = None` defaulted to 0 quantity in the execution simulator.
- **Permanent Lesson**: Always log signal-to-trade attrition counters (`CONFIRMED_SIGNALS == SUM(TERMINAL_OUTCOMES)`). Never accept zero-trade output without pipeline instrumentation verification.

---

## MISTAKE #4: INTERPRETING STRATEGY P&L BEFORE VERIFYING ACCOUNTING INTEGRITY
- **Symptom**: Analyzing trade profitability while an unexamined residual existed between portfolio cash changes and ledger trade P&L.
- **Reality**: Buy-side brokerage fees were deducted from `Portfolio.cash` but omitted from `TradeRecord.total_fees` and `net_pnl`, creating an accounting discrepancy.
- **Permanent Lesson**: Engineering correctness and exact accounting reconciliation ($\text{Final Equity} - \text{Initial Capital} \equiv \sum \text{Net PnL}$) MUST precede statistical P&L interpretation.

---

## MISTAKE #5: RESCUING STRATEGIES POST-HOC AFTER OBSERVING RESULTS
- **Symptom**: Attempting to lower gate thresholds (e.g. relaxing Win Rate from 35% to 15% or Expectancy from +0.25R to +0.15R) because Mean Reversion V3 achieved +20.46% return.
- **Reality**: Retroactively relaxing thresholds after seeing backtest output destroys out-of-sample statistical validity and constitutes curve-fitting.
- **Permanent Lesson**: Gate thresholds are pre-declared and immutable. A strategy that fails a pre-declared gate is abandoned. Gate threshold modifications can only occur prospectively for future research cycles.

---

## MISTAKE #6: PEEKING AT VALIDATION OR FINAL TEST DATASETS
- **Symptom**: Querying 2022–2026 price bars or market regimes to check if a Development strategy would work out-of-sample.
- **Reality**: Peeking contaminates the un-sampled dataset, destroying its ability to act as a true double-blind validation benchmark.
- **Permanent Lesson**: Validation and Final Test datasets remain 100% sealed (`VALIDATION_ACCESS_COUNT = 0`, `FINAL_TEST_ACCESS_COUNT = 0`) until formal, approved validation milestones.
