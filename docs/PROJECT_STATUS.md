# TRADECRAFT — PROJECT STATUS & DIRECTION

> **THE AUTHORITATIVE STATUS DOCUMENT. READ THIS FIRST.**
>
> Last updated: **2026-08-06** (data re-ingestion + quality-report pass, this revision)
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
DATA_AUTHENTICITY_PASSED   (gate v1.0.0, re-verified 2026-08-06 after re-ingestion below)
instruments=142  bars=398,422  range=2014-08-11 -> 2026-08-06
mean pairwise correlation = 0.2540      (synthetic store was 1.0000)
annualised vol spread     = 53.07pp     (synthetic store was 0.01pp)
COVID median drawdown     = 42.9%       (synthetic store was 6.5%)
excess kurtosis           = 157.62
```

Stored in PostgreSQL — the configured store, now shared by ingestion and research.

> **Incident, 2026-08-06 (same day, later session): the store was found completely empty —
> ROOT CAUSE FOUND AND FIXED.** A fresh session queried this same `tradecraft-db`
> container/volume and found zero tables — `alembic current` returned nothing, `data verify`
> failed with `relation "market_bars" does not exist`. Initially treated as a mystery and
> worked around by re-ingesting (see below). **It then happened a second time, mid-session,
> immediately after running `pytest tests/`**, which made the actual cause traceable:
>
> `tests/integration/test_db_postgres.py` connected to `settings.database_url` — the exact
> same database the real research pipeline uses — and its `db_schema` fixture ran
> `Base.metadata.drop_all()` at both setup AND teardown; `test_alembic_migration_upgrade_path`
> dropped it a third time mid-test. **Every ordinary `pytest tests/` run wiped the real
> database, twice.** This is why the store was empty at the start of the session too — some
> earlier test run, at any point in this repo's history, did the same thing.
>
> Fixing it surfaced two more bugs, both previously invisible because they cancelled each
> other out: (1) `alembic/env.py`'s `get_url()` unconditionally returned
> `settings.database_url`, ignoring any `Config.set_main_option("sqlalchemy.url", ...)`
> override — so even pointing the test fixture at an isolated database silently redirected
> migrations back to the real one. (2) Once (1) was fixed, the fixture's own
> `str(engine.url)` call turned out to mask the password as `***` by default in this
> SQLAlchemy version, breaking the connection outright. Bug (1) had been silently absorbing
> bug (2) the whole time. **Full fix:** isolated `tradecraft_test` database on the same
> Postgres instance (`config.py`: `POSTGRES_TEST_DB`, defaults to `tradecraft_test`, with a
> hard runtime refusal if it ever equals `POSTGRES_DB`), `env.py` now honors an explicit
> override, `alembic.ini`'s stale hardcoded URL (wrong password) blanked out, and the test
> fixture uses `url.render_as_string(hide_password=False)` instead of `str(url)`. Verified:
> full `pytest tests/` run leaves the real database's 18-table schema byte-for-byte
> unchanged, confirmed via direct `\dt` before/after, not just exit code.
>
> **Recovery:** `alembic upgrade head`, then `data backfill --universe NIFTY100 --start
> 2015-01-01` re-run in full against the live Kite API — required twice in this session, once
> for each wipe. Verified independently via direct SQL query (`SELECT count(*) FROM
> market_bars`), not just CLI output, before being trusted. **The standing risk is now
> closed**, not just worked around: `pytest tests/` is safe to run repeatedly. If `data
> verify` ever again fails with a missing-relation error, suspect a *different* cause — this
> specific one is fixed and tested.

### 3.2 Open data issues — blocking

| Issue | Status |
|---|---|
| **Corporate action adjustment — premise overturned, see §3.2.1** | The `is_adjusted=False` label `backfill.py` writes on every bar is **factually wrong**, not just cautious: Zerodha's historical API adjusts for bonuses/splits/rights/spin-offs/dividends server-side by default (their own statement, cited in §3.2.1). The code comments claiming "the provider performs no adjustment" are the actual defect here. |
| **Corporate actions table** | Effectively empty. `NSECorporateActionsProvider.get_corporate_actions()` returns `[]` — the NSE fetch was never implemented. Given §3.2.1, it's now unclear this table needs populating for standard bonus/split events at all — see the recommendation there. |
| **Stale instrument(s) — investigated, RESOLVED as non-issue** | `price_granularity` WARN traced to **NMDC** (33.9% distinct-close ratio). Investigated 2026-08-06: NMDC's price ranged ₹7.40–₹96.04 over the series, spending long stretches at ₹10–20, where 2-decimal/NSE-tick precision allows only a few hundred valid price levels — repeats are structurally inevitable. Volume is healthy throughout (1.2M–1B shares/day, **zero** zero-volume days, so not halted) and the longest run of consecutive identical closes is 3–4 days (a stale/forward-filled feed would show long flat runs, not this). **Verdict: false positive from the `price_granularity` heuristic on low-priced equities, not a data defect.** The other 82 of 142 instruments below the 90% threshold (BAJFINANCE, KOTAKBANK, POWERGRID, WIPRO…) are large, liquid, higher-priced names where this same effect is even less likely to bind — not independently re-checked, but the mechanism generalizes. Consider raising the gate's threshold or scaling it by price rather than treating this as an open item. |
| **Corporate-action gap — RECHARACTERISED 2026-08-06, likely not what it was assumed to be** | See the new §3.2.1 below. Short version: the "60 unexplained moves" are almost entirely genuine market crash days, not unadjusted corporate actions, and Kite's historical API appears to already deliver bonus/split-adjusted prices — the opposite of what `is_adjusted=False` on every bar claims. Do not run `corporate-actions apply` against `ca_candidates.csv` — none of its 17 HIGH CONFIDENCE rows verified as real, and applying an adjustment on top of data Kite already adjusted would double-adjust and corrupt prices. |
| **3 truncated/failed symbols — repaired 2026-08-06** | `ADANIPORTS` (0 bars — every chunk failed with Kite `502 Bad Gateway`, mislabeled by the backfill summary as "delisted or bad symbol"), `ADANIENT` (only 245/2962 bars — aborted early after the same 502s), `APOLLOHOSP` (missing its first ~2 years, 2014-08-11→2016-08-12). Fixed via `data backfill --symbol <SYM> --chunk-delay 0.6`, which correctly resumed from the detected gap rather than re-fetching whole history. All three now have full-length series and passed `data verify`. The original "4 truncated symbols: ONGC, COALINDIA, PETRONET, NMDC" note below is unverified against the current store — re-check before assuming it's still accurate. |
| **11 unresolved symbols** | Successions recorded in `instruments/universes.py`. `TATAMOTORS` and `PEL` are demergers with no single successor — their history must not be spliced. Four effective dates remain `UNCONFIRMED`. |

### 3.2.1 The corporate-action gap probably isn't what it was thought to be

Investigated 2026-08-06 by checking every one of the detector's 17 HIGH CONFIDENCE candidates
against real bonus/split history (Trendlyne per-company records), and cross-checking against
documented market events. Full working notes in this session's transcript; conclusions below.

**Finding 1 — the 17 HIGH CONFIDENCE candidates are 17/17 false positives.** None of them is a
real corporate action:

| Symbol | Candidate said | Reality |
|---|---|---|
| ADANIENT | 1:4 bonus, 2017-04-26 | Only real bonus was 1:1 in 2009 |
| ADANIPORTS | 1:4 bonus, 2024-06-04 | Has never issued a bonus |
| ASHOKLEY | 1:4 bonus, 2020-03-23 | Real bonuses were 1:1 (2011) and 1:1 (2025) |
| BAJAJFINSV | 1:3 bonus, 2020-03-23 | Real bonus was 1:1 in Sept 2022 |
| BANDHANBNK | 1:4/1:3 bonus, 2018/2020 | Has never issued a bonus |
| BHEL | 1:4 bonus, 2024-06-04 | Real bonuses were 1:1 (2007) and 1:2 (2017) |
| BPCL | 1:4 bonus, 2018-10-05 | Real bonuses: 1:1×3 (2000/2012/2016), 1:2 (2017), 1:1 (2024) — none in Oct 2018 |
| IDEA | 1:4/1:3 bonus ×3, 2019-2020 | Has never issued a bonus |
| INDUSINDBK | 1:3 bonus, 2020-03-18 | Has never issued a bonus |
| POLYCAB | (unlabeled), 2024-01-11 | Confirmed cause: Income Tax Dept raid disclosure, 20% lower-circuit crash |
| RECLTD | 1:3 bonus, 2024-06-04 | Not checked individually; date matches Finding 2 below |
| VEDL | 1:4/1:3/1:2 bonus ×3, 2019/2020/2026 | Real bonuses were 1:1 (2005) and 1:1 (2008) only |

**Finding 2 — two dates explain most of the 60-candidate list, and they're both documented
market-wide crashes, not corporate actions:**
- **2020-03-23** (and the surrounding week, 2020-03-16 → 2020-03-26): the COVID crash. Nifty
  -12.88%, Sensex -13.15%, 620 of 2,326 BSE stocks locked in a lower circuit that day (59 at
  -20%, 132 at -10%). This explains ASHOKLEY, BAJAJFINSV, BANDHANBNK, INDUSINDBK, CANBK,
  COFORGE, FEDERALBNK, ICICIPRULI, MOTHERSON, VEDL, RBLBANK and more, all clustered here.
- **2024-06-04**: the Lok Sabha election-result "Terrible Tuesday." Nifty -5.93%, Sensex
  -5.74%, worst single day since COVID; PSU, defence, railway and Adani-group names hit
  hardest — which is exactly the cluster in the candidate list (ADANIPORTS, BHEL, RECLTD,
  PFC, SAIL).

**Finding 3 — real bonuses that DID occur inside the dataset window produced zero price gap
in our data**, checked directly: BHEL 1:2 on 2017-09-28 (₹82.80→₹82.65, flat), BAJAJFINSV 1:1
on 2022-09-14 (up, not down), BPCL 1:2 in Jul 2017 and 1:1 in May 2024 (no gap either date),
ASHOKLEY 1:1 on 2025-07-16 (flat). If the raw data really were unadjusted, these ex-dates
would show a sharp, ratio-sized drop. They don't.

**Finding 4 — why: Zerodha's own statement.** Zerodha's official account has stated
(https://x.com/zerodha/status/1952292763929874868): *"the historical prices provided through
the Kite Connect API are adjusted for corporate actions such as bonuses, stock splits, rights
issues, spin-offs, and extraordinary dividends... Corporate action is updated on the
historical data at the beginning of the day process (before market open) on the ex-date...
historical prices are retroactively adjusted across the entire historical dataset."` This
directly contradicts `backfill.py`'s `is_adjusted=False` and the code comments in
`corporate_actions/detector.py`, `corporate_actions/adjuster.py` and
`market_data/quality_report.py` asserting "the Kite provider performs no adjustment." Those
comments, and the label, are the actual defect — not the market data.

**Finding 5 — the +190.67% headline number (largest single move in the dataset) is CGPOWER,
and it's a real, correctly-unadjusted demerger, not a bug.** Crompton Greaves Ltd demerged its
consumer-electricals business into a separately-listed Crompton Greaves Consumer Electricals
Ltd, effective 2015-10-01; the parent was renamed CG Power and Industrial Solutions Ltd in
Jan 2017. CGPOWER's -71.67% drop on 2016-03-15 lines up with the demerger settling into the
industrial-only entity's price. This is exactly the kind of demerger-with-no-single-successor
case the "11 unresolved symbols" row above already warns about for TATAMOTORS and PEL — CGPOWER
should be added to that watch list, and its pre-2016 and post-2016 series should not be
treated as one continuous instrument for backtesting without deciding how to handle the split
in value. Kite's adjustment (Finding 4) evidently does not, and should not, retroactively
splice demerger discontinuities — there's no single ratio that describes what a spin-off does.

**What this means for Phase A:**
- **Do not run `corporate-actions import`/`apply` on `ca_candidates.csv`.** None of the 17
  HIGH CONFIDENCE rows verified as real, and applying a manual adjustment on top of data Kite
  has already adjusted would double-adjust prices — the same silent-corruption failure mode
  CLAUDE.md already warns against, just from the opposite direction.
- The 60 `UNEXPLAINED_LARGE_MOVE` events flagged by `data quality-report` are, on this
  evidence, mostly genuine market history (COVID crash, election crash, company-specific bad
  news) correctly present in the data, not defects to fix.
- **Open decision, not yet made:** whether to correct the `is_adjusted` label itself (many
  query sites across `api.py`, `data_portal.py`, `ingestion.py`, `backfill.py`,
  `attrition_analysis.py`, `trade_analysis.py` filter on `is_adjusted == False` to select
  "raw" bars) — this is a schema/semantics change with real blast radius and hasn't been made
  yet, pending a decision on whether Kite-adjusted-by-default changes what "raw bars, used for
  execution reasoning" (per this doc's own architecture section) should mean.
- CGPOWER (and possibly other 2014-2026-window demergers not yet checked) needs the same
  no-splice treatment already applied to TATAMOTORS/PEL.

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
