# NEXT STEPS — GETTING TO REAL DATA

> Companion to [REPO_AUDIT_2026-08-06.md](./REPO_AUDIT_2026-08-06.md).
> Status as of 2026-08-06: **Phase 0 and Phase 2 complete. Phase 1 is yours to run.**

---

## WHAT HAS ALREADY BEEN DONE

| | Change |
|---|---|
| ✅ | Graveyard bans **voided** — all four strategy families are eligible again |
| ✅ | Cycle 1 / Cycle 2 verdicts annotated `VOID — SYNTHETIC DATA` across 16 documents |
| ✅ | `config/research_governance_state.json` rewritten; open engine defects recorded |
| ✅ | `ai/CURRENT_STATE.md` and `docs/CURRENT_PROJECT_STATE.md` corrected |
| ✅ | `MISTAKE #0` added to `known_mistakes.md` |
| ✅ | Synthetic seeder quarantined → `scratch/generate_synthetic_fixture.py`, requires an explicit flag, stamps `SYNTHETIC_FIXTURE`, refuses non-obvious DB paths |
| ✅ | Old `seed_real_market_bars.py` path now raises loudly instead of regenerating fake data |
| ✅ | **Data authenticity gate** built: `src/tradecraft/market_data/authenticity.py` |
| ✅ | Gate wired into `core/preflight.validate_research_data` |
| ✅ | Test suite: `tests/integration/test_data_authenticity.py` |
| ✅ | `NIFTY100` universe added (`instruments/universes.py`), survivorship-reduced superset of 153 symbols |
| ✅ | `data backfill` **now actually dispatches** — the subparser existed but `main()` never routed to it, so the command silently did nothing |
| ✅ | New commands: `data verify`, `data purge-synthetic` |

### Gate verification (already run)

Against your live `data/tradecraft.db`:

```
DATA_AUTHENTICITY_FAILED   (gate v1.0.0)
instruments=10  bars=19490  range=2016-08-01 -> 2024-06-28

[FAIL] cross_sectional_correlation   mean pairwise r = 1.0000 (45 pairs)
[FAIL] volatility_dispersion         all names 29.2% - 29.2% (spread 0.01pp)
[FAIL] open_differs_from_close       0.00% of bars have open != close
[FAIL] intrabar_range_varies         stdev of (H-L)/C = 0.000008
[FAIL] fat_tails_present             0 moves >= 6% (largest 3.06%)
[FAIL] return_kurtosis               excess kurtosis = -1.24
[FAIL] volume_realism                100% of instruments monotonic
[FAIL] universe_size                 10 instruments
[FAIL] stress_window[COVID-19]       median drawdown 6.5%, expected >= 25%
[FAIL] stress_window[IL&FS]          median drawdown 6.5%, expected >= 10%
[PASS] no_synthetic_source_stamps    ← the source column says ZERODHA_KITE_EOD
```

That last line is the point of the whole exercise. **The provenance string passes. The
numbers do not.** A gate that trusted `source` would have certified this database, which is
exactly what happened for two research cycles.

The gate was also validated in the other direction against a realistic synthetic universe
(dispersed vols, imperfect correlation, gaps, fat tails, a crash) — it passes cleanly, so it
will not block legitimate data.

---

## PHASE 1 — RUN THIS (needs your Kite session)

```bash
# 0. Confirm the gate fails today (should exit 1)
python -m tradecraft data verify

# 1. Authenticate with Zerodha (daily token)
python -m tradecraft auth login
python -m tradecraft auth token <request_token_from_redirect>

# 2. Remove the fabricated bars.
#    This matters: run_backfill resumes from the earliest EXISTING bar per instrument,
#    so leaving synthetic rows in place would silently interleave real and fake data —
#    much harder to detect than the original problem.
python -m tradecraft data purge-synthetic              # dry run, shows what it would delete
python -m tradecraft data purge-synthetic --confirm

# 3. Ingest real NIFTY 100 history (153 symbols incl. delisted/renamed names)
python -m tradecraft data backfill --universe NIFTY100 --start 2015-01-01

# 4. Prove the data is real
python -m tradecraft data verify
```

Step 3 will take a while — roughly 153 symbols × ~11 years in 60-day chunks, with a 0.4s
delay for Kite's rate limit. Tune with `--chunk-delay`. It is resumable and idempotent, so
a failure part-way through is safe to re-run.

### Expect some symbols to fail

`--universe NIFTY100` deliberately requests a **superset** including names removed from the
index during 2015-2026 (HDFC, LTI, MINDTREE, SRTRANSFIN, CADILAHC, YESBANK, ZEEL...). Some
will not resolve against the current Kite instrument dump. That is reported, not fatal.

Fetching them is the point: omitting delisted names is textbook survivorship bias. The audit
found the previous universe had only survivors, so every historical backtest was measuring
"how did today's winners perform" — always flattering.

### If Kite cannot reach 2015

Kite's historical depth is subscription-dependent. If the backfill returns nothing before
some cutoff, take whatever it gives, note the true start date, and either accept the shorter
window or source deep history separately. **Do not** pad the gap. Padding is how this
happened the first time.

---

## PHASE 3 — ENGINE DEFECTS ✅ FIXED 2026-08-06

All four are fixed and covered by 29 hand-computed fixture tests in
`tests/unit/test_r_multiple_and_sizing.py`. Summary of what changed:

| Defect | Fix |
|---|---|
| **F2** | `stop_loss_level` + `initial_risk_per_share` now passed at **all three** `ledger.record_trade` sites. R is computed once at close from entry-time risk. |
| **F2b** | Risk distance captured at entry and never re-derived from a trailed stop. Distances below 0.5% of price are marked `DEGENERATE_RISK` and **excluded**, not scored 0.0. New `r_multiple_coverage_pct`; `expectancy_r` reports `INSUFFICIENT_R_COVERAGE` below 90%. |
| **F3** | `max_holding_days` is now a first-class `SignalIntent` field enforced by the engine. `SignalIntent.__post_init__` **rejects** any signal with no exit path unless `intentional_buy_and_hold=True`. Engine warns `EXIT_RULES_NOT_FIRING` above 5% force-closes. |
| **F4** | `RiskBasedSizingCalculator` is now the default: `qty = (equity × risk_pct) / (entry − stop)`, capped at 20% notional. `max_concurrent_positions` is **enforced in the engine**. Legacy notional sizing retained behind `use_legacy_notional_sizing` and flagged in warnings. |

Two behaviour changes worth knowing about:

**A legacy test was asserting the bug.** `test_zero_risk_or_invalid_risk_r_handling` in
`test_m3b_research_lab.py` asserted `expectancy_r == 0.0` for a *winning* trade whose stop
equalled its entry price. Scoring winners 0.0R is precisely what made the metric structurally
negative. It now asserts exclusion. The other known-answer test (`0.5R`) still passes
unchanged.

**The notional cap breaks exact risk parity on tight stops.** With `risk_pct=1%` and
`max_position_pct=20%`, the cap binds whenever the stop is tighter than 5% of price, so those
positions under-risk. This is deliberate — uncapped risk sizing concentrates capital in
whichever name has the tightest stop, which is how one instrument came to contribute 42.9% of
Cycle 1 P&L. Documented in `test_notional_cap_binds_before_risk_budget_on_tight_stops`.

**Not fixed, deliberately:** `BreakoutConfirmV3` declares no `max_holding_days`, so it still
exits only via stop or force-close. Inventing a holding period would silently change the
hypothesis. The new `EXIT_RULES_NOT_FIRING` warning surfaces it instead.

<details>
<summary>Original defect descriptions (for reference)</summary>

**F2 — `expectancy_r` cannot be positive.**
`engine.py` calls `ledger.record_trade(...)` in three places; only the protective-stop path
(~line 266) passes `stop_loss_level`. The `ExitSignal` path (~line 200) and the
`END_OF_BACKTEST` path (~line 371) omit it, so those trades get `r_multiple = 0.0`. Combined
with F3 every winner is force-closed, so every winner scores R = 0 while every loser scores a
real negative R. Fix: pass `stop_loss_level=pos.current_stop` at all three sites.

**F2b — R denominator collapses on gaps.**
`|entry_price − stop_loss_level|` where the stop is anchored to the signal-day close but the
fill is the T+1 open. Gap opens shrink the denominator toward zero (observed −40R on a single
trade). Fix: persist `initial_risk_per_share` on `TradeRecord` at entry; treat R as `None`
(excluded) when `|entry − stop| < 0.25 × ATR`, and report `r_multiple_coverage_pct` alongside
`expectancy_r`. Refuse to gate on the metric below ~90% coverage.

**F3 — no strategy emits an exit.**
Zero `ExitSignal`, zero `target_level`, no trailing stop; `max_holding_days` sits in
`SignalIntent.metadata` and is never read. Only `STOP_LOSS` and `END_OF_BACKTEST` can fire.
Fix: require every strategy to declare stop, target-or-trailing-rule, and time stop, and add
an invariant test asserting `END_OF_BACKTEST` exits are **< 5%** of all trades. Anything
higher means exits are not firing.

**F4 — sizing is notional, not risk-based.**
`ResearchSizingCalculator(allocation_pct=0.10)` is constructed without
`max_concurrent_positions`, and the engine never enforces a position cap — the 10-holding
constraint in `DEC-002` does not exist in code. Every position gets 10% of equity regardless
of stop distance, so realised risk per trade varies several-fold and R-multiples are not
comparable. Fix: `qty = (equity × risk_pct) / (entry − stop)`, and enforce the cap.

</details>

---

## PHASE 4 — BASELINE BEFORE HYPOTHESES

Once real data is in and F2-F4 are fixed, re-run the four voided families **unchanged** on
DEVELOPMENT only. This is **engine validation, not hypothesis testing** — record it as such.

Sanity bands for a working engine on real data:

| Metric | Expected |
|---|---|
| Win rate | 30-55% (not 10-14%) |
| Payoff ratio | 1-2× (not 11×) |
| `END_OF_BACKTEST` exits | < 5% of trades |
| `r_multiple_coverage_pct` | > 90% |
| Mean pairwise return correlation | 0.3-0.6 |

If win rates come back at 10-14% again, the exits are still broken — do not interpret it as a
strategy result. That misreading cost two research cycles.

Only after this baseline looks sane should Cycle 3 / ALPHA-015 begin.

---

## A NOTE ON PROCESS

The repository holds ~250 governance documents, 21 ADRs, immutable graveyards, sealed dataset
splits and SHA-256 certificates. Underneath sat 10 fabricated instruments.

Every control tested **internal consistency** — does the report match the JSON, did the JSON
come from `BacktestEngine.run()`. None tested **external validity** — do these prices resemble
the NSE. `AUTHENTICITY_GUARANTEE.md` verified prices came *from the database*; it never asked
what was in the database.

The discipline was not wrong. Pre-registration, cost realism, out-of-sample sealing and
refusing to relax gates post-hoc are all correct, and rare. The failure was that none of it
pointed at the inputs.

The rule worth keeping: **no metric may gate a decision unless a unit test proves it returns
the correct value on a hand-computed fixture** containing known winners, known losers, and a
force-closed position. `expectancy_r` had no such test, and it terminated every strategy you
have ever run.
