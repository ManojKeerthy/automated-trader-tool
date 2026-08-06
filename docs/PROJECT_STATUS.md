# TRADECRAFT — PROJECT STATUS & DIRECTION

> **THE AUTHORITATIVE STATUS DOCUMENT. READ THIS FIRST.**
>
> Last updated: **2026-08-06**
> Supersedes: all prior status summaries, cycle-closure certificates, and narrative
> milestone reports. Where this document and any other disagree, this one is correct.

---

## 0. THE GOAL

Build a swing-trading system that **places real trades on Zerodha Kite, under human
approval, and makes money net of costs.**

Everything in this repository is instrumental to that. The research platform is not the
product; it is the machinery for finding something worth trading. A research platform that
never produces a deployable strategy has failed, however elegant it is.

Two hard constraints follow from the goal:

1. **Real money means real data.** Every result must come from prices that actually
   occurred, net of costs actually charged.
2. **Real money means real execution.** A strategy that works in a backtest but cannot be
   traded — because of liquidity, slippage, order rejection, or the fact that nothing in
   this repository can place an order yet — is not an asset.

---

## 1. HONEST STATUS IN ONE PARAGRAPH

The platform is well engineered and, until 2026-08-06, had never been run on real market
data. Research Cycles 1 and 2 were conducted entirely against a synthetic price series
produced by a generator inside the repository, so their conclusions — "no strategy survived
development", "PEAD V1 does not work" — are not findings. They are artifacts. Real NSE data
was ingested on 2026-08-06 (142 instruments, 387,874 bars, 2014-08-11 to 2026-08-06) and
passed the new authenticity gate. Four engine defects that would have corrupted results on
real data have been fixed. **No strategy has been validly tested. No order-placement code
exists. There is currently no evidence for or against any hypothesis.**

---

## 2. CORRECTION OF THE INHERITED NARRATIVE

A previous summary described the project as *"Platform: Mature and validated. Research
methodology: Mature and frozen. Profitable alpha: Not yet discovered."* That summary is
retained for history but is **materially wrong**. The corrections below matter because they
were feeding directly into Cycle 3 planning.

| Inherited claim | Correction |
|---|---|
| "The platform succeeded. The hypothesis failed." | **Inverted.** The platform had four further defects beyond the one found, and the hypothesis was never tested — the prices were fabricated. |
| "❌ PEAD V1 does not work" | **Unsupported.** PEAD V1 has not been evaluated. The −8.72% CAGR is what a zero-edge series returns after costs. |
| "₹0.0000 residual gives confidence returns aren't caused by bugs" | **Category error.** It confirms the arithmetic. It cannot see fabricated prices. Internal consistency was repeatedly mistaken for validity. |
| Cycle 1 failed due to "over-filtering, few trades, no regime awareness, poor robustness" | **All four are invented.** Actual causes: zero-edge synthetic data, an `expectancy_r` that could not return a positive number, and strategies with no exit rule. These fictions became `known_mistakes.md` entries and drove the V2/V3 revisions. |
| "Point-in-time database, survivorship protection, corporate actions" | The database held 10 synthetic instruments and 10 placeholder dividends. Survivorship protection was never exercised. |
| "Platform: Mature and validated" | Mature, **unvalidated**. Validated only for internal consistency. |
| Dataset splits "SEALED_UNTOUCHED" | Vacuous — the FINAL TEST range contained zero rows. Sealing an empty range is trivially satisfied. |

### 2.1 The near-miss worth remembering

Cycle 2's forensic audit found a genuine defect: `active_positions` never reached
`generate_signals`, so the 30-session time exit never fired and positions were held for
years. That was good work.

It was fixed as a **single instance** rather than as a **class**. The identical defect was
present in all four Cycle 1 strategies, which emitted no exit signals at all. One further
question — *where else does this pattern exist?* — would have unwound the entire edifice a
cycle earlier.

**Standing rule adopted:** when a defect is found, the remediation is not complete until
every other site exhibiting the same pattern has been searched for and either fixed or
explicitly cleared.

---

## 3. WHAT IS ACTUALLY TRUE TODAY

### 3.1 Data — real for the first time

```
DATA_AUTHENTICITY_PASSED   (gate v1.0.0)
instruments=142  bars=387,874  range=2014-08-11 -> 2026-08-06
mean pairwise correlation = 0.2546      (synthetic store was 1.0000)
annualised vol spread     = 53.07pp     (synthetic store was 0.01pp)
COVID median drawdown     = 42.9%       (synthetic store was 6.5%)
excess kurtosis           = 156.34
```

Stored in PostgreSQL — the configured store, now shared by ingestion and research.

### 3.2 Open data issues — blocking

| Issue | Status |
|---|---|
| **Corporate action adjustment** | Largest daily move is **+190.67%**; excess kurtosis 156. `backfill.py` writes `is_adjusted=False` and the provider performs no adjustment. Unadjusted bonuses/splits create overnight gaps that never happened, which stop out every long in that name. **This would reproduce the Cycle 1 symptom on real data.** |
| **Corporate actions table** | Effectively empty. `NSECorporateActionsProvider.get_corporate_actions()` returns `[]` — the NSE fetch was never implemented. Until populated, adjustment defects cannot be distinguished from real events. |
| **Stale instrument(s)** | `price_granularity` WARN: lowest distinct-close ratio 42.3%. At least one name repeats the same close on ~58% of its bars. |
| **4 truncated symbols** | ONGC, COALINDIA, PETRONET, NMDC. Both underlying bugs fixed; a plain re-run now repairs them. |
| **11 unresolved symbols** | Successions recorded in `instruments/universes.py`. `TATAMOTORS` and `PEL` are demergers with no single successor — their history must not be spliced. Four effective dates remain `UNCONFIRMED`. |

### 3.3 Engine — defects fixed 2026-08-06

| | Fix | Tests |
|---|---|---|
| **F2** | `stop_loss_level` now passed at all three `record_trade` sites; R computed once at close from entry-time risk. Force-closed winners previously scored `0.0`. | 29 hand-computed fixtures in `tests/unit/test_r_multiple_and_sizing.py` |
| **F2b** | Degenerate risk distances **excluded**, not scored zero. `r_multiple_coverage_pct` added; `expectancy_r` flagged ungateable below 90% coverage. | ✅ |
| **F3** | `max_holding_days` is a first-class `SignalIntent` field enforced by the engine. Signals with no exit path are **rejected at construction**. `EXIT_RULES_NOT_FIRING` warning above 5% force-closes. | ✅ |
| **F4** | Risk-based sizing is now default (`qty = equity × risk_pct / (entry − stop)`), capped at 20% notional. `max_concurrent_positions` enforced in the engine. | ✅ |
| **Split store** | Ingestion wrote to PostgreSQL while 12 research runners hardcoded `sqlite:///data/tradecraft.db`. All repointed. Pinned SHA-256 preflights — which would have blocked ingesting real data — removed. | `tests/unit/test_db_provenance.py` |
| **Backfill resume** | Only ever fetched history *older* than the earliest bar, so a truncated symbol could never be repaired. Now diffs the exchange calendar to find leading, trailing and interior gaps. | ✅ |
| **Backfill duplicates** | Per-bar `SELECT` could not see pending unflushed inserts, so duplicate dates in one Kite response tripped `uq_instrument_date_adj` and abandoned the whole symbol. Three defences added. | ✅ |

### 3.4 What does not exist

- ❌ **Any validated strategy.** Zero. Cycles 1 and 2 produced no evidence.
- ❌ **Order placement.** No paper broker, no live broker. `broker/zerodha/` is an empty package.
- ❌ **Risk engine.** RISK LOCK and KILL SWITCH are documented in ADR-009; no code.
- ❌ **Approval workflow.** ADR-008 documented; no code.
- ❌ **Position reconciliation** against actual broker holdings.
- ❌ **Live scheduling / daily auth automation.**
- ❌ **Corporate action adjustment pipeline.**

---

## 4. WHERE WE ARE HEADING

Seven phases. Each has an exit criterion that must be met before the next begins. The
ordering is deliberate: **do not build execution before there is something worth executing,
and do not trade capital before execution has been proven on paper.**

```
  A. Data integrity          <- WE ARE HERE
  B. Engine baseline
  C. Alpha discovery              (expect several failed cycles)
  D. Validation & final test      (one shot, ever)
  E. Execution stack              (build only if D survives)
  F. Paper trading                (3-6 months, live data, simulated fills)
  G. Live capital, approved       (start small)
```

### Phase A — Data integrity *(current)*

**Exit criterion:** `data quality-report` reports no blocking defects.

The corporate action pipeline is **built** (`src/tradecraft/corporate_actions/`, 32 tests).
The convention is settled: **raw bars are immutable** (`is_adjusted=false`, what actually
printed, used for execution reasoning); **adjusted bars are derived** (`is_adjusted=true`,
regenerated on demand, used for research). The schema already permits both via the
`uq_instrument_date_adj` constraint.

Remaining work is verification, which needs a human:

```bash
# 1. Find candidate splits/bonuses and pre-fill a verification sheet
python -m tradecraft data corporate-actions detect \
    --write-template docs/research/ca_candidates.csv

# 2. Check each row against its NSE circular, set verified=true, then
python -m tradecraft data corporate-actions import docs/research/ca_candidates.csv

# 3. Build the adjusted series (dry run first)
python -m tradecraft data corporate-actions apply
python -m tradecraft data corporate-actions apply --apply

# 4. Repair the four truncated symbols, then re-check
python -m tradecraft data backfill --universe NIFTY100 --start 2015-01-01
python -m tradecraft data quality-report
```

Then: resolve the stale instrument(s) behind the 42.3% granularity warning, and confirm the
four `UNCONFIRMED` succession dates in `instruments/universes.py` against NSE circulars.

> **Only `verified=true` actions adjust prices.** Detector output is `verified=false` by
> default and is skipped. Applying an unverified inference would replace one silent data
> corruption with another — the precise failure that cost two research cycles.

### Phase B — Engine baseline

**Exit criterion:** the four voided Cycle 1 families, re-run unchanged on real DEVELOPMENT
data, produce *plausible trade distributions* — regardless of profitability.

| Metric | Sane band |
|---|---|
| Win rate | 30–55% (not 10–14%) |
| Payoff ratio | 1–2× (not 11×) |
| `END_OF_BACKTEST` exits | < 5% |
| `r_multiple_coverage_pct` | > 90% |

This is **engine validation, not hypothesis testing.** Record it as such. If win rates come
back at 10–14% again, exits are still broken — do not read it as a strategy result.

### Phase C — Alpha discovery

**Exit criterion:** a strategy passing the pre-registered development gate on real data.

ALPHA-015 (Dual Momentum RS & Sector Leadership) is the ranked candidate, but two of its
inputs need redoing: its feasibility was assessed against a database with correlation 1.0
where relative strength was mathematically vacuous, and it belongs to the momentum-RS family
that the graveyard had banned on synthetic evidence. Both assessments are void. The same
applies to the data-requirement notes across the ALPHA-014→048 backlog.

The good news: with 0.25 mean correlation and 53pp vol dispersion across 136 usable names,
cross-sectional research is genuinely feasible for the first time.

**Set expectations honestly.** Most hypotheses fail. Professional teams test many ideas per
survivor. Several failed cycles here would be a normal outcome, not evidence the platform is
broken — but this time the failures will be real information rather than artifacts.

### Phase D — Validation, then final test

**Exit criterion:** survives validation, then survives the final test. Once.

The FINAL TEST split now holds ~2 years of genuinely untouched real data. It is the most
valuable asset in this project and can be spent exactly once. Freeze an explicit end date in
the run config before it is ever used — daily ingestion keeps extending the window, so it
must not silently grow between runs.

### Phase E — Execution stack

**Build only after Phase D succeeds.** Building it earlier is speculative work on behalf of
a strategy that will probably not exist.

Required:

- `PaperBroker` and `ZerodhaBroker` behind one `BrokerInterface` (ADR-003)
- Order state machine: submitted → open → partial → filled / rejected / cancelled; AMO
  handling; idempotent client order IDs so a retry cannot double-submit
- **Position reconciliation** against actual Kite holdings on every startup. Divergence
  between believed and actual positions is the classic way automated systems lose money
- Pre-trade risk engine: position limits, exposure caps, per-trade risk, daily loss limit
- **RISK LOCK** (auto-halt at drawdown threshold) and **KILL SWITCH** (ADR-009)
- Approval workflow (ADR-008): proposed orders surfaced for explicit human approval;
  protective stops autonomous
- Crash recovery: what happens if the process dies holding positions
- Daily Kite token refresh; alerting when it fails

### Phase F — Paper trading

**Exit criterion:** 3–6 months of live-data paper trading whose results track the backtest.

This is where backtest-only strategies die. Watch for: signals that fire on data unavailable
at decision time, slippage worse than modelled, orders that would not have filled,
liquidity limits at real size.

### Phase G — Live capital, under approval

**Start small — an amount whose total loss would not matter.** Scale only on evidence.

Before the first live order, verify: SEBI's retail algorithmic trading framework and
Zerodha's API algo requirements (registration, algo ID tagging, order-rate limits, static IP)
— these have changed recently and must be checked against current documentation, not
assumed. Also settle STCG treatment and record-keeping.

---

## 5. STANDING RULES

Adopted from failures that actually occurred here.

1. **Provenance is a property of the numbers, never of a label.** A `source` column saying
   `ZERODHA_KITE_EOD` is worth nothing. The authenticity gate is blocking.
2. **No metric may gate a decision unless a unit test proves it correct on a hand-computed
   fixture** with known winners, losers, and a force-closed position. `expectancy_r` had no
   such test and terminated every strategy ever run here.
3. **Fix defects as classes, not instances.** Search for every other site with the same
   pattern before closing.
4. **Every result names its source database.** `BacktestResult.data_provenance` is populated
   automatically; artifacts without it are not auditable.
5. **Prefer assertions in code to certificates in prose.** ~250 governance documents did not
   catch what one 20-line test would have.
6. **Never pin a content hash of the data.** It cannot distinguish tampering from
   correction, and here it enforced the latter.
7. **A strategy must declare how it exits.** Enforced at construction.
8. **Unmeasurable is not zero.** Excluding is honest; scoring zero is a silent lie.

---

## 6. IMMEDIATE NEXT ACTIONS

```bash
# 1. Find out what the real data actually contains
python -m tradecraft data quality-report --json > docs/research/quality_report.json

# 2. Repair the four truncated symbols (plain re-run now works)
python -m tradecraft data backfill --universe NIFTY100 --start 2015-01-01 \
    > docs/research/backfill.log 2>&1

# 3. Confirm still clean
python -m tradecraft data verify
```

Then Phase A item 2 — corporate action ingestion and adjustment — which is the single
blocking piece of work between here and trustworthy backtests.

---

## 7. A NOTE ON EXPECTATIONS

This is not investment advice, and nothing here guarantees a profitable strategy exists to
be found. Swing trading Indian large caps net of STT, GST, exchange fees, stamp duty, DP
charges and slippage is a genuinely hard problem, and the friction is substantial —
roughly 0.24% round-trip on the observed cost model before slippage.

What can be said: the previous two cycles proved nothing, so the question is still open. The
machinery to answer it properly now exists and, as of today, is pointed at real data for the
first time.

---

## RELATED

- [research/REPO_AUDIT_2026-08-06.md](./research/REPO_AUDIT_2026-08-06.md) — full audit with line references
- [research/NEXT_STEPS.md](./research/NEXT_STEPS.md) — remediation detail
- [research/known_mistakes.md](./research/known_mistakes.md) — MISTAKE #0 is the important one
- `config/research_governance_state.json` — machine-readable current state
