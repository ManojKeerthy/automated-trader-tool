# INDEPENDENT REPO AUDIT — 2026-08-06

> **AUDIT SCOPE**: Full repository, memory files, research documentation, backtest artifacts, and `data/tradecraft.db`.
> **HEADLINE VERDICT**: **`ALL RESEARCH RESULTS TO DATE ARE INVALID — THE MARKET DATABASE IS SYNTHETIC`**

---

## 0. EXECUTIVE SUMMARY

You have not failed to find a profitable strategy. You have never tested a strategy against real market data.

`data/tradecraft.db` contains 19,490 deterministically generated price bars produced by
`scratch/seed_real_market_bars.py`. No Zerodha data has ever entered the research pipeline,
despite every bar being stamped `source = 'ZERODHA_KITE_EOD'`.

Every number in Research Cycle 1 (M3A–M3C.0), Research Cycle 2 (M3R–M3G.0), the strategy
lineage registry, the research graveyard, and all 100+ audit certificates is an artifact of
that synthetic series.

Three independent defects compound this:

| # | Defect | Effect |
|---|--------|--------|
| **F1** | Synthetic market database | No alpha can exist; all results are noise from a sawtooth generator |
| **F2** | `expectancy_r` cannot be positive by construction | Killed all 4 Cycle 1 families at the gate |
| **F3** | No strategy ever emits an exit | Manufactured the identical ~10–14% win rate across all 4 "independent" families |

Additionally, the narrative documentation reports numbers that **do not match** the raw
artifacts they claim to summarise (see §5).

---

## 1. FINDING F1 — THE MARKET DATABASE IS SYNTHETIC

### 1.1 The generator

`scratch/seed_real_market_bars.py` (name is misleading — it generates, it does not fetch):

```python
daily_var = Decimal(str(1.0 + (((idx * 17 + 3) % 21) - 10) * 0.003))
close_p = round(curr_price * daily_var, 2)
high_p  = round(close_p * Decimal("1.012"), 2)
low_p   = round(close_p * Decimal("0.988"), 2)
open_p  = round((high_p + low_p) / Decimal("2.0"), 2)
volume  = 500000 + ((idx * 131) % 400000)
curr_price = close_p * (Decimal("1.0") + drift)
```

### 1.2 What this produces

| Property | Value in DB | Implication for research |
|---|---|---|
| Instruments | **10**, not 50 | Cycle 1 docs claim `active_instruments: 50` and 44 instruments with attributed P&L |
| Daily return series | `((idx*17+3) % 21 - 10) * 0.003` | A **repeating 21-day sawtooth**, identical for every stock |
| Cross-sectional correlation | **1.0** | Relative-strength / momentum ranking is mathematically meaningless |
| Annualised volatility | **29.2% for all 10 names** | Identical to 1 decimal place across every symbol |
| Max daily move | **±3.0%**, hard-bounded | No COVID crash, no earnings gaps, no fat tails |
| Open vs Close | `open == close` **every single day** | Zero overnight gaps — the T+1 open execution model is untested |
| High / Low | Fixed `close × 1.012` / `close × 0.988` | **ATR is a constant 2.4% of price forever** — every ATR-based stop is a fixed % stop |
| Volume | Linear counter `500000, 500131, 500262, …` | RVOL / volume-expansion filters are testing a ramp function |
| Corporate actions | 10 rows, all identical `DIVIDEND ₹15.50 on 2021-06-15` | Corporate-action handling is untested |
| Coverage end | **2024-06-28** | See §1.4 |

Empirically confirmed:

```
AXISBANK   n=1949  ann.vol=29.2%  max=+3.0%  min=-3.0%
BHARTIARTL n=1949  ann.vol=29.2%  max=+3.1%  min=-3.0%
HDFCBANK   n=1949  ann.vol=29.2%  max=+3.0%  min=-3.0%
... (all 10 identical)

RELIANCE, March 2020 (COVID crash week):
  2020-03-12  close 2492.17   (-3.0%)
  2020-03-13  close 2545.52   (+2.1%)
  2020-03-23  close 2549.39   (+1.2%)
```
Real RELIANCE fell ~40% in that window. Largest single-day move anywhere in the DB: 3.1%.

### 1.3 Why this guarantees unprofitability

The generator has no autocorrelation structure, no cross-sectional dispersion, and no
volatility clustering. Expected gross edge for **any** rule is exactly zero. Net of the
(correctly implemented) Indian delivery cost model, expected P&L is **exactly minus friction**.

Observed Cycle 2 result: gross −₹324k, fees −₹66k, net −₹390k. That is the cost model
working correctly on a zero-edge series. It is not evidence about PEAD.

### 1.4 The "sealed" datasets do not exist

`config/research_governance_state.json` declares:

```
final_test_range : 2024-07-01 -> 2026-07-28
final_test_status: SEALED_UNTOUCHED
```

The database ends **2024-06-28**. The FINAL TEST split contains **zero rows**. It is not
sealed; it was never populated. `FINAL_TEST_ACCESS_COUNT = 0` is trivially true.

The VALIDATION split (2022-01-01 → 2024-06-28) exists but is the same synthetic series.

### 1.5 Why the authenticity audits passed

`docs/research/AUTHENTICITY_GUARANTEE.md` defines four invariants. All four are about
*plumbing*, not *provenance*:

> 1. Database Price Invariant: every price used during backtesting originates from `market_bars`.

The guarantee verifies that prices came **from the database**. It never verifies that the
database contains real market data. `M3R_3_DATABASE_AUTHENTICITY.md` certifies a SHA-256
checksum of the synthetic file and stamps it `DATABASE_CERTIFIED`.

The `source` column reads `ZERODHA_KITE_EOD` because the seeder wrote that string.

---

## 2. FINDING F2 — `expectancy_r` IS STRUCTURALLY INCAPABLE OF BEING POSITIVE

This is the metric that failed every single Cycle 1 family at the gate.

### 2.1 Winners are assigned R = 0

`metrics.py` computes the R-multiple from `TradeRecord.stop_loss_level`:

```python
if (t.stop_loss_level is not None and t.stop_loss_level > 0 and t.stop_loss_level != t.entry_price):
    ...  r_multiples.append(t.net_pnl / initial_trade_risk)
else:
    r_multiples.append(Decimal("0.0"))
```

`engine.py` calls `ledger.record_trade(...)` in **three** places. Only one passes
`stop_loss_level`:

| Exit path | `engine.py` | Passes `stop_loss_level`? | Resulting R |
|---|---|---|---|
| Protective stop / target | line ~266 | ✅ yes | real (negative for stop-outs) |
| Strategy `ExitSignal` | line ~200 | ❌ **no** | forced to `0.0` |
| `END_OF_BACKTEST` force close | line ~371 | ❌ **no** | forced to `0.0` |

Given F3 (below), **every winning trade exits via force-close** and is therefore recorded
with R = 0.0, while every losing trade exits via stop-loss and records a real negative R.
The mean R multiple is arithmetically guaranteed to be ≤ 0.

### 2.2 The denominator collapses on gaps

`initial_risk_per_share = abs(entry_price − stop_loss_level)`.

The stop is anchored to the **signal-day close** (`c_curr − 1.5 × ATR` in
`mean_reversion_v3.py`), but `entry_price` is the **T+1 open** fill. When T+1 opens near the
stop level, the denominator collapses toward zero and R explodes.

The guard only tests exact equality (`!= t.entry_price`), not near-equality.

Observed in `scratch/m3b_3_decision_evidence.json` (Trend Pullback V2):

```
r_percentiles: min -40.06R,  p25 -1.83R,  median -1.15R,  p75 -1.06R,  p90 +0.17R
```

A −40R trade is impossible if stops are honoured. The stop **was** honoured — the
denominator was wrong.

### 2.3 The resulting absurdity

`scratch/m3b_4_development_results.json`:

```json
"strat_mean_reversion_v3": {
  "net_pnl": 204624.68,          //  +20.5% return
  "profit_factor": 1.776,
  "expectancy_r": -101.85        //  mean R of -101.85
}
```

A strategy returning +20% cannot have a mean R-multiple of −101.85. The gate that read this
value and returned `FAIL → ABANDON_FAMILY` was reading garbage.

---

## 3. FINDING F3 — NO CYCLE 1 STRATEGY EVER EXITS A POSITION

Verified across `v2_strategies.py`, `mean_reversion_v3.py`, `breakout_confirm_v3.py`,
`trend_pullback.py`, `momentum_rs.py`:

- Zero occurrences of `ExitSignal` in any Cycle 1 strategy.
- Zero occurrences of `target_level=` — no profit target is ever set.
- No trailing stop exists anywhere (`portfolio.py` sets `current_stop` once at entry and never updates it).
- `max_holding_days` is written into `SignalIntent.metadata` and **never read by anything**.

### 3.1 Consequence

The only two exit paths that can fire are:

1. `STOP_LOSS` (protective stop, checked each bar)
2. `END_OF_BACKTEST` (force close on the final date)

So the trade distribution is mechanically:

- ~87–90% of trades → stopped out at ≈ −1R
- ~10–13% of trades → held for **years**, force-closed on the last bar of a rising synthetic series

### 3.2 This explains the "low win rate mystery"

| Family | Win rate | Payoff ratio |
|---|---|---|
| Trend Pullback V2 | 10.56% | — |
| Momentum RS V2 | 10.0% | — |
| Breakout Confirm V3 | 10.27% | — |
| Mean Reversion V3 | 12.5% | ~12.4× |

Four "structurally independent" hypotheses producing win rates within 2.5 percentage points
of each other is not four findings — it is **one artifact observed four times**. The win rate
is a property of the exit machinery, not of the entry logic.

A mean-reversion strategy producing a 12.4× payoff ratio is a contradiction in terms.
Mean reversion should produce high win rate / low payoff. The observed profile is
"stopped out constantly, one multi-year buy-and-hold winner" — which is exactly what
"no exit rule + force close" produces.

Confirming evidence: Trend Pullback V2 lost money in 2016, 2017, 2018, 2019 and 2020, then
made +₹214k in **2021 alone** (win rate jumps 5% → 23%). 2021 is the force-close year.
`top1_share = 42.9%` of all P&L came from a single position.

### 3.3 Cycle 2 hit the same class of bug and it was correctly diagnosed

`M3ER_6_EXIT_REASON_ANALYSIS.md` found `MAX_HOLDING_PERIOD` fired **0 times** because
`active_positions` was not forwarded to `generate_signals()`. That was fixed for Cycle 2 —
but the equivalent Cycle 1 defect (strategies that emit no exits at all) was never
identified, and the Cycle 1 verdicts were never revisited.

---

## 4. FINDING F4 — POSITION SIZING IS NOTIONAL, NOT RISK-BASED

`engine.py`:

```python
sizing_calculator = ResearchSizingCalculator(allocation_pct=Decimal("0.10"))
```

- `max_concurrent_positions` is a constructor parameter of `ResearchSizingCalculator` but is
  **never passed here and never enforced anywhere in the engine**. The 10-position cap
  documented in `DEC-002` does not exist in code; concurrency is limited incidentally by cash.
- Every position gets 10% of equity regardless of stop distance. A name with a 2% stop and a
  name with an 8% stop both receive 10% of capital → **realised risk per trade varies 4×**.
- This makes R-multiples non-comparable across trades and makes portfolio results dominated
  by whichever names happened to have tight stops.
- When cash is short, `simulate_entry_execution` silently decrements quantity share-by-share,
  producing ragged position sizes (observed notionals ₹60,072 → ₹103,562 in the Cycle 2 ledger).

For research, sizing should be **fixed-fractional risk**: `qty = (equity × risk_pct) / (entry − stop)`.

---

## 5. FINDING F5 — DOCUMENTATION DOES NOT MATCH THE ARTIFACTS

The narrative documents report numbers that are absent from — and contradicted by — the JSON
artifacts they claim to summarise.

**Mean Reversion V3:**

| Metric | `strategy_lineage_registry.md`, `research_graveyard.md`, `gate_methodology_review.md` | `scratch/m3b_4_development_results.json` (actual) |
|---|---|---|
| Win rate | 14.2% | **12.5%** |
| Profit factor | 1.54 | **1.776** |
| Expectancy R | **+0.28R** | **−101.85R** |
| Trades | 198 | **136** |

`gate_methodology_review.md` builds an entire governance argument on Mean Reversion V3 having
"passed Profit Factor and Expectancy R and failed only on Win Rate." Per the actual artifact
it failed Expectancy R by 102 R. The prose is not a summary of the data; it is unrelated to it.

**Universe size:** `research_cycle_1_summary.md` states "Verified 50 NIFTY instruments clean."
`m3b_4_signal_viability.json` states `active_instruments: 50`.
`m3b_3_decision_evidence.json` attributes P&L across 44 instruments (7 profitable, 37 losing),
including `ADANIENT` contributing +₹136,124.

**ADANIENT is not in the database.** The database has 10 instruments and ADANIENT is not one
of them. Those figures were not produced by the backtest engine reading `market_bars`.

---

## 6. FINDING F6 — PROCESS: THE GOVERNANCE LAYER OUTGREW THE RESEARCH

The repository contains ~250 markdown documents, 21 ADRs, an immutable graveyard, a dataset
firewall, hypothesis pre-registration with SHA-256 hashes, cycle-closure certificates,
authenticity certificates, forensic audits, and independent-verification reports.

Under all of it sit **10 synthetic instruments and zero validated strategies**.

The governance apparatus is not wrong in principle — pre-registration and out-of-sample
sealing are correct discipline. The failure is that **none of the controls were pointed at
the input data**. Every audit verified internal consistency (does the number in the report
match the number in the JSON? does the JSON come from `BacktestEngine.run()`?) and none
verified external validity (do these prices resemble the NSE?).

A single 20-line test asserting that daily returns across 10 large caps are not perfectly
correlated would have caught this on day one and saved two entire research cycles.

### 6.1 Collateral damage

`research_graveyard.md` permanently prohibits four legitimate strategy families and explicitly
forbids "disguised retries":

> No future strategy may use SMA50 pullback + EMA20 resumption triggers on NIFTY 50.
> No future strategy may use raw 63-day price momentum ranking on NIFTY 50.
> No future strategy may use 20-day Donchian breakouts with RVOL filters on NIFTY 50.
> Mean Reversion V3 CANNOT be rescued.

These bans rest entirely on synthetic-data results. They must be **voided**, not honoured.
As written they would also block ALPHA-015 (Cycle 3), which is cross-sectional relative
strength — the graveyard already prohibits that family.

---

## 7. REMEDIATION PLAN

### Phase 0 — Void (do first, it is cheap)

1. Mark Cycle 1 and Cycle 2 verdicts `VOID — SYNTHETIC DATA`. Do not delete; annotate.
2. Void all four graveyard entries and lift the retry prohibitions.
3. Rename `scratch/seed_real_market_bars.py` → `scratch/generate_synthetic_fixture.py` and
   move any synthetic seeding behind an explicit `--synthetic` flag that stamps
   `source = 'SYNTHETIC_FIXTURE'`.
4. Correct `docs/CURRENT_PROJECT_STATE.md` and `ai/CURRENT_STATE.md` (the latter is stale at
   M3A / 2026-07-29, six milestones behind).

### Phase 1 — Real data (the actual blocker)

5. Ingest real NSE daily bars via Kite Connect. `market_data/provider.py` and
   `market_data/backfill.py` already implement chunked, resumable, rate-limit-aware backfill —
   the machinery works, it was simply never pointed at the API.
6. Minimum viable research dataset: **NIFTY 100+, 2010→present**. Ten large caps over eight
   years cannot support cross-sectional research; there is no cross-section.
   - Note: Kite `historical_data` depth is subscription-dependent. If it cannot reach 2010,
     source the deep history separately and use Kite for the recent window and live trading.
7. Verify adjustment handling. `is_adjusted` is currently written `False` for all rows; decide
   the convention and enforce it, and populate real corporate actions.

### Phase 2 — Data authenticity gate (blocking; must pass before any backtest)

8. Add `tests/integration/test_data_authenticity.py` asserting, on the live DB:
   - Mean pairwise cross-sectional return correlation **< 0.9** (catches lockstep series)
   - Cross-sectional dispersion of annualised vol **> 3 percentage points**
   - `open != close` on **> 95%** of bars (catches the midpoint bug)
   - `high/close` and `low/close` ratios are **not constant**
   - At least one daily move **< −6%** exists in any window containing 2020-03
   - Volume is not monotonically increasing; volume distribution is right-skewed
   - Known event checks: e.g. NIFTY drawdown ≥ 25% between 2020-01 and 2020-04
9. Make this gate a precondition inside `core/preflight.py` — no backtest may run against a
   database that fails it.

### Phase 3 — Engine fixes

10. Pass `stop_loss_level=pos.current_stop` in **all three** `ledger.record_trade` call sites
    in `engine.py`.
11. Guard the R denominator: if `|entry − stop| < 0.25 × ATR_at_entry`, record R as `None`
    (excluded), not `0.0`. Report `r_multiple_coverage_pct` alongside `expectancy_r` and
    refuse to gate on it below ~90% coverage.
12. Persist `initial_risk_per_share` on `TradeRecord` at entry time rather than recomputing it
    from the stop at exit.
13. Make exits first-class. Every strategy must declare stop, target (or trailing rule), and
    time stop, and the engine must enforce them. Add an invariant test:
    `END_OF_BACKTEST` exits must be **< 5%** of all trades — anything higher means exits aren't firing.
14. Switch research sizing to fixed-fractional risk and enforce the concurrent-position cap in
    the engine.

### Phase 4 — Re-run

15. Re-run the four Cycle 1 families **unchanged** on real data as a sanity baseline, purely to
    confirm the engine produces sane trade distributions (win rate 30–55%, payoff 1–2×,
    `END_OF_BACKTEST` < 5%). This is engine validation, not hypothesis testing — do it on
    DEVELOPMENT only and record it as such.
16. Only then start Cycle 3 / ALPHA-015.

### Phase 5 — Governance right-sizing

17. Keep: pre-registration, dataset firewall, cost realism, immutable trade ledgers.
18. Drop or automate: per-milestone prose certificates. Replace narrative audit documents with
    assertions in code. A test that fails is worth more than a document that says `VERIFIED`.
19. Rule: **no metric may gate a decision unless a unit test proves it returns the correct
    value on a hand-computed fixture** with known winners, losers, and a force-closed position.

---

## 8. WHAT IS ACTUALLY GOOD HERE

Worth stating plainly, because the above is uniformly negative and the platform is not:

- **The cost model is excellent.** `backtesting/costs.py` implements effective-dated STT,
  exchange charges, SEBI fees, stamp duty, GST-on-brokerage, and per-ISIN-per-day DP charges.
  Most retail backtests ignore DP charges entirely. This is institutional quality.
- **The execution simulator is sound.** T+1 fills, gap-through-stop at open, conservative OHLC
  ambiguity resolution, integer share enforcement, cash-constrained sizing.
- **Look-ahead protection is real.** `DataPortal` raises `LookAheadError` on future access;
  pivot confirmation delay is handled correctly.
- **Accounting reconciles exactly.** ₹0.0000 residual between portfolio cash deltas and ledger
  net P&L is a genuine achievement and most backtesters never verify it.
- **The research discipline is right in shape** — pre-registration, single-config budgets, and
  refusal to relax gates post-hoc are correct instincts, rare in retail algo work.

The engine is largely ready. It has been running on nothing.

---

## 9. ONE-LINE ANSWER

You have not been unable to find an edge. You have been searching for an edge in a
21-day sawtooth wave generated by `scratch/seed_real_market_bars.py`, scored by a metric
that cannot return a positive number, using strategies that have no exit rule.
