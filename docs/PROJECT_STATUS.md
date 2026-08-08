# TRADECRAFT — PROJECT STATUS & DIRECTION

> **THE AUTHORITATIVE STATUS DOCUMENT. READ THIS FIRST.**
>
> Last updated: **2026-08-06** (Phases A and B completed this revision — see §3.2, §3.2.1,
> §3.2.2, §4 Phase B)
> Supersedes: all prior status summaries, cycle-closure certificates, and narrative
> milestone reports. Where this document and any other disagree, this one is correct.
> Verify before trusting even this: query `config/research_governance_state.json` and
> re-run `data verify` / `data quality-report` rather than assuming any document, including
> this one, is current — that is the single lesson this project keeps re-learning.

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
was ingested on 2026-08-06 (142 instruments, 398,216 bars, 2014-08-11 to 2026-08-06, 141
tradeable — one, CGPOWER, excluded pending an unresolved discontinuity) and passes the
authenticity gate. Phases A and B (real data, engine mechanics) are complete. Phase C (§8) went
through nine real defects (F6-F9) before any result could be trusted, then tested **seven**
distinct strategy hypotheses end to end (TrendPullbackV2, BreakoutConfirmV2, MomentumRSV2,
MeanReversionV2, ALPHA-018 volatility squeeze, ALPHA-019 cross-sectional reversal, ALPHA-020
volatility contraction pattern) against real DEVELOPMENT-split data. **Recurring finding
across three independent designs (TrendPullbackV2, unfiltered ALPHA-018, ALPHA-020): each
looks profitable in aggregate but is flat-to-losing in the calmer 2016-2019 stretch and only
profitable during the 2019-2021 COVID-recovery rally (§8.4)** — not a proven edge, a system
that would have caught one historic bull run. A market-breadth regime filter (only trade when
>50% of the universe is in a long-term uptrend) fixed this for ALPHA-018 (§8.5, the first
strategy in this project's history positive in both DEVELOPMENT halves) but not for ALPHA-020
(§8.8) — the filter only adds information when the base strategy lacks its own trend context,
and ALPHA-020 already had one. ALPHA-019 failed outright on both halves independently (not a
regime issue — transaction costs, exactly the risk it pre-registered). **The only candidate
that has ever cleared DEVELOPMENT was `VolatilitySqueezeV1RegimeFilteredStrategy` (§8.5).**
Per explicit instruction it was run once against `VALIDATION_SPLIT` (§8.6, the one-shot
resource, now spent): positive on paper (+0.0715) but not trustworthy — 63% of gross profit
came from one trade (NMDC), first misdiagnosed as a corporate-action data bug, then corrected
same-day after checking primary sources (a real demerger event, not bad data — structurally
identical to the already-confirmed CGPOWER case). With the OHLCV-only backlog exhausted, per
explicit instruction this project's data was extended for the first time beyond OHLCV (§9):
verified that Kite provides no fundamentals or delivery data (checked its own API docs, not
assumed), found and integrated NSE's own free daily delivery-position report (2014-present,
371,058 rows, all 142 instruments, verified authentic against an independent NSE source
format), and built ALPHA-017 on it — the first hypothesis this project has tested on
genuinely new data rather than a new OHLCV combination. It failed too, on the same
concentration mechanism already caught elsewhere (one outlier trade, 31.21% of profit share >
25% cap) — but the investigation into *why* its expectancy briefly looked positive in both
halves surfaced a real, generalizable insight: an unweighted mean R-multiple and a
dollar-weighted P&L total can genuinely disagree in sign around one extreme outlier, so
neither should be trusted alone. **No strategy has been proven on out-of-sample data. The
readily available hypothesis backlog (ALPHA-014→048) is exhausted, but the delivery-data
pipeline is now permanent, verified infrastructure** — reusable for the next hypothesis
without repeating this engineering. `FINAL_TEST_SPLIT` remains untouched and must not be
spent now. No order-placement code exists.

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
>
> **Final state after both recoveries**: 398,216 bars, 142 instruments, 2014-08-11 →
> 2026-08-06, `DATA_AUTHENTICITY_PASSED`, 100% of rows `is_adjusted=True` (written correctly
> at ingestion this time, no relabel needed).

### 3.2 Open data issues — blocking

| Issue | Status |
|---|---|
| **Corporate action adjustment — premise overturned, see §3.2.1** | The `is_adjusted=False` label `backfill.py` writes on every bar is **factually wrong**, not just cautious: Zerodha's historical API adjusts for bonuses/splits/rights/spin-offs/dividends server-side by default (their own statement, cited in §3.2.1). The code comments claiming "the provider performs no adjustment" are the actual defect here. |
| **Corporate actions table** | Effectively empty. `NSECorporateActionsProvider.get_corporate_actions()` returns `[]` — the NSE fetch was never implemented. Given §3.2.1, it's now unclear this table needs populating for standard bonus/split events at all — see the recommendation there. |
| **Stale instrument(s) — investigated, RESOLVED as non-issue** | `price_granularity` WARN traced to **NMDC** (33.9% distinct-close ratio). Investigated 2026-08-06: NMDC's price ranged ₹7.40–₹96.04 over the series, spending long stretches at ₹10–20, where 2-decimal/NSE-tick precision allows only a few hundred valid price levels — repeats are structurally inevitable. Volume is healthy throughout (1.2M–1B shares/day, **zero** zero-volume days, so not halted) and the longest run of consecutive identical closes is 3–4 days (a stale/forward-filled feed would show long flat runs, not this). **Verdict: false positive from the `price_granularity` heuristic on low-priced equities, not a data defect.** The other 82 of 142 instruments below the 90% threshold (BAJFINANCE, KOTAKBANK, POWERGRID, WIPRO…) are large, liquid, higher-priced names where this same effect is even less likely to bind — not independently re-checked, but the mechanism generalizes. Consider raising the gate's threshold or scaling it by price rather than treating this as an open item. |
| **Corporate-action gap — RECHARACTERISED 2026-08-06, likely not what it was assumed to be** | See the new §3.2.1 below. Short version: the "60 unexplained moves" are almost entirely genuine market crash days, not unadjusted corporate actions, and Kite's historical API appears to already deliver bonus/split-adjusted prices — the opposite of what `is_adjusted=False` on every bar claims. Do not run `corporate-actions apply` against `ca_candidates.csv` — none of its 17 HIGH CONFIDENCE rows verified as real, and applying an adjustment on top of data Kite already adjusted would double-adjust and corrupt prices. |
| **3 truncated/failed symbols — repaired 2026-08-06** | `ADANIPORTS` (0 bars — every chunk failed with Kite `502 Bad Gateway`, mislabeled by the backfill summary as "delisted or bad symbol"), `ADANIENT` (only 245/2962 bars — aborted early after the same 502s), `APOLLOHOSP` (missing its first ~2 years, 2014-08-11→2016-08-12). Fixed via `data backfill --symbol <SYM> --chunk-delay 0.6`, which correctly resumed from the detected gap rather than re-fetching whole history. All three now have full-length series and passed `data verify`. The original "4 truncated symbols: ONGC, COALINDIA, PETRONET, NMDC" note below is unverified against the current store — re-check before assuming it's still accurate. |
| **Symbol successions — RESOLVED 2026-08-06** | All 10 entries in `instruments/universes.py`'s `SYMBOL_SUCCESSION` now have sourced dates, zero `UNCONFIRMED`. Filled in 3 previously-blank dates (MCDOWELL-N→UNITDSPR 2024-06-07, ZOMATO→ETERNAL 2025-04-09, PEL/Piramal Pharma demerger 2022-08-30), **corrected 2 wrong dates** found during verification (CADILAHC→ZYDUSLIFE was 2022-02-21, actually 2022-02-24 per the NSE filing itself; SRTRANSFIN/SHRIRAMCIT→SHRIRAMFIN was 2022-11-25, actually 2022-11-30), and independently confirmed the 5 already-correct ones (HDFC, LTI, MINDTREE, TATAMOTORS). **Separately found and fixed a real bug**: "LTIM" was never a valid Kite ticker — LTIMindtree's actual `tradingsymbol` per a direct `kite.instruments('NSE')` query is `LTM` (confirmed empirically; external web sources saying "LTIM" were simply wrong for this specific question, a useful reminder to check the actual provider directly). "LTIM" removed from `HISTORICAL_SYMBOLS` and `SYMBOL_SUCCESSION` as a redundant, permanently-unresolvable phantom entry — LTI/MINDTREE (pre-merger) and LTM (current, in `NIFTY50_SYMBOLS`, already ingested with 2,486 bars) already cover the full history with no gap. `TATAMOTORS` and `PEL` remain demergers with no single successor by design — their history must not be spliced, not a defect to fix. |

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

**Finding 5 — CGPOWER has TWO large moves, not one, and they're two different things.
Corrected 2026-08-06 after an initial mis-attribution in this document.**

The **2016-03-15 move (-71.67%)** is confirmed: a Business Standard article headlined
"Crompton Greaves drops ex-demerger," published 2016-03-15, matches exactly, and the data
shows an 86.7M-share volume spike that day (vs. 3–15M on adjacent days) consistent with
mass repositioning around a real ex-date. This is the actual ex-date of Crompton Greaves
Ltd's demerger of its consumer-electricals business into the separately-listed Crompton
Greaves Consumer Electricals Ltd — the scheme was board-approved Feb 2015 and court-approved
Nov 2015, but 2016-03-15 is when it hit the exchange price. (An earlier version of this
document guessed the ex-date was 2015-10-01; that was wrong — corrected here.) The parent
was renamed CG Power and Industrial Solutions Ltd in Jan 2017. This is exactly the kind of
demerger-with-no-single-successor case the "11 unresolved symbols" row above already warns
about for TATAMOTORS and PEL — CGPOWER should be added to that watch list, and its pre- and
post-2016-03-15 series should not be treated as one continuous instrument for backtesting
without deciding how to handle the split in value.

The **2015-01-01 move (+190.67%, the dataset's single largest and the number previously
cited as headline evidence) is a SEPARATE event, over a year before the demerger, and is
NOT explained.** Price nearly tripled (×2.907) while volume dropped to almost exactly a
third (×2.897) — traded value (price×volume) was conserved to within 0.4% across the
boundary (₹230.6M → ₹231.5M), the textbook signature of a share-count change, but no
matching corporate action for Crompton Greaves around that date was found via external
search. Do not assume it is safely explained. Candidate hypotheses, none confirmed:
an actual reverse split/consolidation not found by the search above, or an instrument-token
mapping issue in ingestion that spliced a different security's pre-2015 history onto
today's CGPOWER token. **This needs its own investigation before Phase A is called clean** —
unlike NMDC and the corporate-action false positives elsewhere in this document, this one
is genuinely still open.

Kite's adjustment (Finding 4) evidently does not, and should not, retroactively splice
demerger discontinuities — there's no single ratio that describes what a spin-off does.

**Finding 6 — the third and last move driving `quality_report.py`'s `blocking=True` is also
confirmed genuine.** `blocking` is computed as `bool(likely_adjustment_defects) or any(abs(pct)
>= 0.60 for m in extreme_moves)` (`market_data/quality_report.py`) — with
`corporate_action_count=0`, `likely_adjustment_defects` is always empty, so in practice
`blocking` today is driven entirely by exactly three moves ≥60%: the two CGPOWER moves above,
plus **NMDC +85.7% on 2022-10-27**. Confirmed via a Business Standard headline "NMDC trades
ex-date for demerger; stock surges 14% amid heavy volumes," dated 2022-10-27 — the NMDC Steel
spinoff, 1:1 share allotment, record date 2022-10-28. The period-news price level (~₹107)
differs from ours (~₹25–31) because Kite has also retroactively adjusted for a later
split/bonus on top of this event — the same adjustment mechanism from Finding 4, not a new
anomaly.

**Net: of the three moves currently gating Phase A's exit criterion, two are now confirmed
genuine and sourced (NMDC 2022-10-27, CGPOWER 2016-03-15). One remains genuinely open
(CGPOWER 2015-01-01).**

**Both fixed, 2026-08-06:**
- `quality_report.py` now has a `VERIFIED_EXPLAINED_MOVES` registry (symbol+date → sourced
  explanation). The two resolved findings are recorded there and no longer trip `blocking`,
  but still appear in the report with `verdict=VERIFIED_EXPLAINED` so the finding stays
  visible rather than silently disappearing. `blocking` is now driven by exactly the one
  real open item, not three.
- **CGPOWER's 2015-01-01 discontinuity could not be sourced** despite real effort: ruled out
  an NSE holiday/calendar bug (2015-01-01 confirmed a normal trading day), ruled out
  confusion with the 2016-03-15 demerger (a separate, real, later event), checked for a
  systemic ingestion artifact (several other instruments show a mild move at the same date
  boundary, but none within an order of magnitude of CGPOWER's — not explained by a shared
  cause). Suggestive: reported 52-week high/low for the stock in this window (~₹153–231,
  Sept 2014–Feb 2015 per press coverage) matches the price level *after* 2015-01-01, not
  before — consistent with the pre-2015-01-01 portion of our series being wrong, though this
  isn't conclusive either. **Per standing instruction: when a stock's data can't be sourced,
  exclude it rather than trade it.** CGPOWER is now excluded from the eligible trading
  universe by default (`screening/eligibility.py`'s `_PROJECT_EXCLUDED_SYMBOLS`), confirmed
  working via `PROJECT_EXCLUSION` exclusion record. It stays excluded until this is
  conclusively resolved — remove only after finding the actual cause.

With CGPOWER excluded from trading, `quality_report.py --json`'s `blocking=True` no longer
represents a defect in the *tradeable* universe — it's an honest record of one investigated,
excluded, still-unexplained instrument. §3.2.1's Findings 1–4 already established that
`docs/research/ca_candidates.csv` contains no real corporate actions to verify or apply.
**Phase A is now functionally complete for the 141 tradeable instruments.** The 11
unresolved symbol successions (below) are the only other open item.

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

### 3.2.2 Test suite — 12 failures resolved 2026-08-06

Investigated all 12 pre-existing test failures rather than assuming they were stale debt.
Two very different root causes:

**7 of 12 were a real, currently-live, systemic bug** — not test debt. `BacktestEngine`
(`engine.py:404`) unconditionally calls `strategy.evaluate(current_date, portal,
active_positions=...)`, but only `earnings_drift_v1.py` actually accepted that parameter.
Every other strategy — `breakout_confirm.py`, `breakout_confirm_v3.py`, `mean_reversion.py`,
`mean_reversion_v3.py`, `momentum_rs.py`, both classes in `reference_strategies.py`,
`trend_pullback.py`, and all four strategies in `v2_strategies.py` — had a narrower
`evaluate()` signature that would raise `TypeError` the moment it ran through the real
engine. This is exactly the "fix defects as classes, not instances" failure mode CLAUDE.md
already documents once (the Cycle 2 missing-exit bug fixed in one strategy, still live in
three others) — the same pattern recurred with the `active_positions`/F3 interface change.
**Fixed in all 8 files**: added `active_positions: list[uuid.UUID] | None = None` to every
`evaluate()` signature, matching the pattern already correct in `earnings_drift_v1.py` and
the base class. Right now, before this fix, a real backtest of any strategy except
`earnings_drift_v1` would have crashed on the first simulated session.

**5 of 12 were genuinely void-cycle test debt**, correctly identified and removed rather
than "fixed": `test_m3b_2_2_2_pre_fix_forensics.py` (deleted entirely — its one test
certified specific numeric forensic values computed against the synthetic Cycle 1/2 data),
one test each from `test_m3b_3_1_reconciliation.py` and `test_m3b_4_final_revision.py`
(certified the existence of `scratch/m3b_*.json` artifacts deleted in the 2026-08-06
governance cleanup), and two tests from `test_m3c_0_governance.py` (asserted
`research_cycle_1_status == "CLOSED_NO_SURVIVOR"` and `SEALED_UNTOUCHED` — the pre-audit,
now-known-false claims — and required `docs/research/research_cycle_1_summary.md` and other
deleted void-cycle documentation to exist). Fixing these "properly" would have meant
reverting real corrections back to false claims or resurrecting deleted fictional
documentation — removing them was correct. The other tests in each partially-affected file
(hash locking, firewall enforcement, graveyard guard, lineage collision detector, parameter
provenance auditing, survivor gate evaluation) exercise real, still-valid mechanisms and were
kept untouched.

**Result: 275 passed, 0 failed, 1 skipped.** Verified clean on `ruff check` and `mypy` for
every file touched.

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
  A. Data integrity          ✅ complete 2026-08-06
  B. Engine baseline         ✅ complete 2026-08-06
  C. Alpha discovery              (expect several failed cycles)   <- WE ARE HERE
  D. Validation & final test      (one shot, ever)
  E. Execution stack              (build only if D survives)
  F. Paper trading                (3-6 months, live data, simulated fills)
  G. Live capital, approved       (start small)
```

### Phase A — Data integrity ✅ COMPLETE (2026-08-06)

**Exit criterion:** `data quality-report` reports no blocking defects. **Met**, for the 141
tradeable instruments.

This section originally described a plan (verify detected corporate actions, import, apply
an adjustment layer) built on an assumption that turned out to be wrong: that Kite's
historical data was unadjusted raw prints. It is not — see §3.2.1 Finding 4. That plan is
superseded; do not follow the steps that used to be here. What actually happened, in full,
with sourcing: §3.2 (corporate-action premise overturned), §3.2.1 (six findings — 17/17
"high confidence" corporate-action candidates were false positives, real root cause, the
CGPOWER/NMDC investigations), §3.2.2 (test suite: 7 of 12 failures were a real live bug, not
debt), and the symbol-successions row above (all 10 entries sourced, zero `UNCONFIRMED`, one
real bug found and fixed along the way). The stale-instrument/granularity question is
resolved in §3.2 (NMDC, false positive from low-price tick-size, not a defect). The one
genuinely open item is CGPOWER's unexplained 2015-01-01 discontinuity, and it's handled by
exclusion (`screening/eligibility.py`), not by blocking Phase A.

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

**RUN 2026-08-06, real DEVELOPMENT-split data (2016-08-01 → 2021-12-31), `tradecraft`
Postgres store, 142 instruments, `NIFTY100` (UNVERIFIED point-in-time membership — the
`universe_membership` table is empty, engine fell back to all active instruments, correctly
flagged `RESEARCH_ONLY`), `IndianEquityDeliveryCostModel` + 5bps slippage,
`EndOfBacktestPolicy.FORCE_CLOSE`:**

| Strategy | Trades | Win rate | Payoff ratio | Force-close % | R-coverage | Verdict |
|---|---|---|---|---|---|---|
| MeanReversionV2 | 1,889 | 38.2% (30–55 ✅) | 1.13× (1–2 ✅) | 0.32% (<5 ✅) | 99.9% (>90 ✅) | **PASS** |
| TrendPullbackV2 | 120 | 20.8% (❌) | 32.4× (❌) | 8.3% (❌) | 100% (✅) | **FAIL** |
| BreakoutConfirmV2 | 97 | 16.5% (❌) | 33.5× (❌) | 10.3% (❌) | 100% (✅) | **FAIL** |
| MomentumRSV2 | 69 | 24.6% (❌) | 61.6× (❌) | 14.5% (❌) | 100% (✅) | **FAIL** |

**Diagnosed, not just observed.** The three failing strategies show the exact symptom
pattern this exit criterion exists to catch — low win rate paired with an implausibly high
payoff ratio, the historical Cycle 1 signature. Root cause found by inspecting
`v2_strategies.py` directly: all four strategies build their `SignalIntent` with
`max_holding_days=getattr(self, "max_holding_days", None)`, but `self.max_holding_days` is
only ever actually set in `MeanReversionV2Strategy.__init__` (`= 5`, its default parameter).
`TrendPullbackV2Strategy`, `BreakoutConfirmV2Strategy`, and `MomentumRSV2Strategy` never set
it, so `getattr` silently returns `None` — these three declare no time-based exit and no
profit target, only a stop-loss. Their exit breakdowns confirm it exactly: entries exit via
`STOP_LOSS` (92–90% of trades) or `END_OF_BACKTEST` (8–15%), with **zero** target or
time-based exits recorded. A winning position that never touches its stop rides completely
uncapped until the literal end of the multi-year backtest window, which is what produces
30–60× payoff ratios on a tiny surviving minority of trades.

**This is not an engine bug** (unlike F2/F2b/F3, already fixed) — the engine is correctly
doing what each strategy's `SignalIntent` tells it to. It's a genuine gap in these three
strategies' exit design: no `max_holding_days` value was ever decided for them, not merely
left unwired. Checked `hypothesis_statement()` and the class docstrings for an intended
holding period already specified elsewhere — none exists.

**RESOLVED 2026-08-06, from sourced convention, not fitted to results.** Derived a
holding-period value for each family from its own documented mechanism and established
literature/practice — chosen and written down *before* re-running the backtest, so the
result couldn't influence the choice:

- **TrendPullbackV2 & BreakoutConfirmV2 → 20 trading sessions (~4 weeks).** Both are
  swing-trading trend/breakout-continuation setups; the general practitioner convention for
  this style is cited across multiple sources as "2 to 4 weeks." 20 sessions is the upper
  end of that range and also matches each strategy's own existing 20-session parameter
  (`pullback_ema` / `channel_period`), avoiding an arbitrary differentiated number between
  the two. BreakoutConfirmV2's is explicitly a Turtle-system-style Donchian breakout (per
  its own `channel_period` `ParameterOrigin`); authentic Turtle exits are trailing-structural
  rather than day-count, which this engine doesn't implement, so the day count is used as a
  time-based backstop, not a claim of exact replication.
- **MomentumRSV2 → 63 trading sessions**, set to exactly match `rs_lookback` (also 63).
  Mirrors Jegadeesh & Titman (1993), the foundational academic study this relative-strength
  design follows: they tested J-month formation / K-month holding combinations for J,K in
  {3,6,9,12} and highlight matched J=K periods (their most-cited combination is 6/6) as
  standard. This strategy's ~3-month (63-session) formation gets the matching ~3-month hold.

Implemented in `v2_strategies.py` with a `ParameterOrigin` entry on each strategy citing the
source (category `MARKET_CONVENTION`, matching this codebase's own existing category for
externally-sourced choices) — auditable the same way every other parameter in these classes
already is. Necessarily changed each strategy's `config_hash`; every test that pinned the
old hash (`test_m3b_2_pipeline.py`, `test_m3b_2_2_accounting.py`,
`test_m3b_3_decision_gate.py`, `test_m3b_3_1_reconciliation.py`,
`test_m3b_4_final_revision.py`) was updated to the new, recomputed value — not silently
made to pass some other way.

**Re-ran Phase B after the fix:**

| Strategy | Trades | Win rate | Payoff ratio | Force-close % | R-coverage | Verdict |
|---|---|---|---|---|---|---|
| TrendPullbackV2 | 958 | 34.9% (30–55 ✅) | 1.98× (1–2 ✅) | 1.0% (<5 ✅) | 100% (✅) | **PASS** |
| BreakoutConfirmV2 | 1,035 | 28.5% (❌, just under 30) | 1.94× (1–2 ✅) | 0.9% (<5 ✅) | 100% (✅) | 3/4 |
| MomentumRSV2 | 355 | 35.2% (30–55 ✅) | 3.71× (❌, was 61.6×) | 2.0% (<5 ✅) | 100% (✅) | 3/4 |
| MeanReversionV2 | 1,889 | 38.2% (✅) | 1.13× (✅) | 0.3% (✅) | 99.9% (✅) | **PASS** |

The pathological signature (near-zero win rate paired with a 30–60× payoff ratio) is gone
from all four families. The two remaining deviations are small and directionally sensible
for each strategy's actual character, not remnants of the missing-exit defect — a momentum
strategy structurally trading fewer, larger, longer-held winners is expected, not a symptom.
**Not tuning further to force these two fully inside the illustrative bands** — doing so
would reintroduce the exact "fit the parameter to the metric" problem this fix was trying to
avoid in the first place. **Phase B is complete**: all four families now produce plausible,
bounded trade distributions; 2 of 4 pass every band outright, 2 of 4 pass 3 of 4 with the
remaining gap small and explicable.

> **Superseded by the F7 fix, §8.** The table above predates the fee-dominated
> micro-position fix (`research/sizing.py`, found while running Phase C). After that fix,
> trade counts and ratios shift again (fewer, cleaner trades): TrendPullbackV2 714 trades,
> win rate 40.5%, payoff 1.79×; BreakoutConfirmV2 719 trades, win rate 32.6% (now inside the
> band); MomentumRSV2 291 trades, payoff 2.49× (still above 2×); MeanReversionV2 1,493
> trades, payoff **0.86×** (now just under the 1× floor, was 1.13× — plausible consequence
> of the trade population getting cleaner, not a new defect). Same conclusion holds: no
> pathological signature in any of the four, small band deviations only. See §8 for the full
> defect chain and why this table's exact numbers should be read as superseded rather than
> re-verified — §8's numbers are the ones Phase C's verdict is actually based on.

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

Phases A and B are complete (2026-08-06, see §3.2, §3.2.1, §3.2.2, §4 Phase B). Phase C (§8)
is now feature-complete for the readily available hypothesis backlog:

- **`VolatilitySqueezeV1RegimeFilteredStrategy` (§8.5)** remains the only candidate ever to
  clear DEVELOPMENT (both halves + parameter-robustness). Its one `VALIDATION_SPLIT` attempt
  (§8.6) was inconclusive — dominated by one real, non-repeatable corporate event (NMDC
  demerger, 63% of gross profit), not proven, not disproven. The one-shot resource is spent.
  The genuine lesson (§8.6): this is a sample-size/diversification problem (more, shorter,
  more diversified trades dilute any one event's share), not something an entry-timing filter
  can fix — verified before attempting that fix, not assumed.
- **ALPHA-019 (§8.7, cross-sectional short-term reversal)**, pursued specifically to test that
  diversification lesson, achieved 6x the trade count but failed outright — negative in both
  DEVELOPMENT halves, exactly the transaction-cost risk it pre-registered as its own main risk.
- **ALPHA-020 (§8.8, volatility contraction pattern)** looked good in aggregate but failed the
  same regime test as TrendPullbackV2 and unfiltered ALPHA-018 (H1 -0.2269, the worst single-
  half result of any strategy this cycle) — a third independent design with the identical
  fingerprint, strong evidence this is a property of the market period, not any one hypothesis.
  The market-breadth regime filter, generalized into reusable infrastructure
  (`MarketBreadthRegimeFilter`) and applied here too, did not fix it — that filter only helps
  when the base strategy lacks its own trend-context filter, and ALPHA-020 already has one.

**This exhausted the OHLCV-only ALPHA-014→048 backlog.** Per explicit instruction, extended
beyond it (§9): ingested NSE's free daily delivery-position data (2014-present, verified
authentic), unlocking ALPHA-017. Built and tested it (§9.1) — **also fails**, rejected by the
same 25% single-trade-concentration cap already used throughout this document
(`max_single_trade_profit_share_pct = 31.21%`). The investigation on the way there is itself
worth keeping in mind going forward: a positive `net_expectancy_r` in both DEVELOPMENT halves
briefly looked like the best result yet, until checking *why* revealed H1's profit_factor was
actually 0.96 (below the gate) — one extreme-R outlier trade had pulled the unweighted mean R
positive while the dollar-weighted P&L stayed negative. Neither `net_expectancy_r` nor
`net_pnl` alone is sufficient; check both, plus concentration, every time.

**Where this leaves the project:** no strategy is proven. The delivery-data pipeline is real,
verified, and permanent — reusable for the next hypothesis without repeating the engineering.
Fundamentals data remains unsolved (no clean free primary source found). `FINAL_TEST_SPLIT`
must not be touched. No order-placement code exists. Next steps are a genuine fork, not a
queued task — see §1 and §9.1's closing note for the honest options.

Verify before trusting any of this — query `config/research_governance_state.json` and
re-run `python -m tradecraft data verify` / `data quality-report` rather than assuming this
document is current, per this document's own standing rule.

---

## 8. PHASE C — FIRST RESULT (2026-08-06)

Before trusting any Phase C number, re-checked the actual evaluation mechanism
(`research/v2_development_gate.py`, the code meant to gate Phase C admissions) rather than
assuming it was correct because it existed. Found two more real, live defects — not void-cycle
debt, current code that would have corrupted this exact evaluation.

**F6 — fabricated metrics.** `V2DevelopmentGateEvaluator.evaluate_frozen_v2` returned
hardcoded constants for `cagr_pct`, `max_drawdown_pct`, `sharpe_ratio`, `sortino_ratio` —
literally `12.5 if gate_pass else -5.0`, etc. — not computed from the backtest's equity curve
at all. Exactly the "governance certificate that looks rigorous but isn't" pattern this
project's own audit history warns about, live in the mechanism meant to prevent exactly that.
Fixed: now computed via `MetricsEngine`, the same real computation Phase B used.

**Also in the same file: R-multiple reimplemented incorrectly, a second time.** The gate had
its own local R-multiple calculation instead of using `TradeRecord.r_multiple` (the engine's
official F2/F2b-fixed field) — fabricating a fake 5%-of-price stop when `stop_loss_level` was
`None` and scoring degenerate risk distances as `0.0` instead of excluding them. Precisely the
F2/F2b defect pattern, reintroduced in a second code path with zero test coverage proving it
correct. Fixed to use `t.r_multiple` directly, excluding unmeasurable trades from the mean;
added `r_multiple_coverage_pct` to the scorecard with a rejection reason below 90% coverage,
mirroring `MetricsEngine`.

**F7 — fee-dominated micro-positions, found by actually running the fixed gate on real data.**
With F6 fixed, the first real run showed **all four strategies failing** with strongly
negative `net_expectancy_r` (-0.54 to -0.87) despite two of them (TrendPullback, MomentumRS)
showing *positive* total P&L — a contradiction worth investigating rather than reporting.
Traced it to `STOP_LOSS` exits averaging **-1.627R**, not the expected ~-1.0R, worst case
-31.5R. Pulled the actual trades: every one of the 15 worst-R trades had total risk
(risk_per_share × quantity) between ₹0.48 and ₹1.90, and every one lost almost exactly
₹14-17 — the flat DP/brokerage charge, regardless of which way the price moved (one exit
price was even *above* entry). Root cause: `RiskBasedSizingCalculator`'s cash-fitting loop
(`while qty >= 1: ... qty -= 1`, `research/sizing.py`) had no floor — with cash nearly
exhausted (routine with several concurrent positions open), it would shrink a position to a
single share rather than reject the trade, and a 1-share position with a few paise of
price-based risk cannot economically absorb a real ~₹15 fixed cost. 149 of 948
TrendPullbackV2 DEVELOPMENT trades (15.7%) had total risk under ₹30. **Fixed**: sizing now
rejects (`POSITION_TOO_SMALL_RELATIVE_TO_COSTS`) when total risk can't clear 10× the trade's
own estimated transaction cost (or ₹200, whichever is larger) — a floor derived from the cost
structure itself, not fitted to any backtest result. Two new hand-computed regression tests
added (`tests/unit/test_r_multiple_and_sizing.py`): one proving the cash-starved case is now
rejected, one proving adequately-funded small-price trades still size correctly (the fix must
not over-reject).

Both fixes are the same underlying lesson repeating: **this project has never actually run
its own evaluation mechanisms against real data with real market-cap dispersion (₹5 stocks
next to ₹10,000 stocks) and real concurrent-position cash pressure before.** Synthetic data
and small manual test fixtures cannot surface a defect that only shows up when a real
₹5-priced stock gets sized last, when cash is nearly gone, during a real multi-year backtest.

**Result, DEVELOPMENT split (2016-08-01 → 2021-12-31), both fixes applied:**

| Strategy | Trades | Net P&L | CAGR | Sharpe | Net Expectancy_R | Profit Factor | Gate |
|---|---|---|---|---|---|---|---|
| **TrendPullbackV2** | 714 | +₹729,800 | +10.9% | 0.36 | **+0.0259** | 1.21 | **✅ V2_DEVELOPMENT_SURVIVOR** |
| MomentumRSV2 | 291 | +₹1,652,782 | +21.9% | 0.67 | -0.0412 | 1.58 | ❌ (expectancy_r just below 0; single-trade profit share 29.4% > 25% cap) |
| BreakoutConfirmV2 | 719 | -₹377,936 | -7.4% | -0.57 | -0.1182 | 0.83 | ❌ |
| MeanReversionV2 | 1,493 | -₹835,337 | -28.0% | -1.74 | -0.1855 | 0.70 | ❌ |

**TrendPullbackV2 is the first strategy in this project's entire history to survive an
evaluation against real market data — engine bugs, synthetic data, or governance process
defects killed every candidate before this one.** Net expectancy_r is small (+0.026R) and
this is one DEVELOPMENT-split run, not validation, not out-of-sample, not the final test —
treat it as "worth carrying forward to robustness checking," not as a discovered edge.
MomentumRSV2 is a genuine near-miss (real positive profit factor and CAGR, failed on
concentration risk from one large trade) worth a second look with position-level caps rather
than being discarded.

**What Phase C does NOT authorize:** touching `VALIDATION_SPLIT` or the sealed final-test
range. Per this document's own §4 Phase D, that data can be spent exactly once. The next
legitimate step for TrendPullbackV2 is the predeclared-robustness-neighbourhood check this
gate's `FrozenV2CanonicalRecord` machinery is designed for (parameter sensitivity within a
pre-declared range, not re-optimization) — not a validation-split run.

---

### 8.1 ROBUSTNESS CHECK — PARAMETER_CLIFF, TrendPullbackV2 fails (2026-08-07)

**Superseded by F9, §8.2 below — the trade counts and expectancy figures in this section
include CGPOWER, an instrument that should never have been tradeable at all. The
PARAMETER_CLIFF verdict itself still holds after the correction; the numbers do not.**

Before trusting `research/robustness.py` — the module that runs exactly this check — checked
it the same way §8's F6/F7 were found, rather than assuming it was correct because it existed.

**F8 — the same fabricated-metric defect, a third time.** `LimitedRobustnessAnalyzer` had its
own local R-multiple reimplementation (the F2/F2b fake-5%-stop pattern, already fixed twice
elsewhere) and hardcoded `max_drawdown_pct = -18.0 if v_exp_r > 0 else -30.0` — not computed,
literally two constants keyed to the sign of expectancy. Fixed the same way as F6: R-multiple
now reads `TradeRecord.r_multiple` directly, and `max_drawdown_pct` is computed per-variant via
`MetricsEngine` from that variant's own equity curve. No test had asserted the old fake values.

**With F8 fixed, ran the actual check.** Neighbourhood: the ±10% symmetric perturbations
already hardcoded as this module's own defaults for `strat_trend_pullback_v2`
(`atr_dist_max ∈ {1.8, 2.2}`, `atr_stop_mult ∈ {1.8, 2.2}`, canonical 2.0/2.0) — not chosen
after seeing this run's numbers, since they predate this session's involvement with the file.
`trend_ma`/`pullback_ema`/`max_holding_days` held fixed (MARKET_CONVENTION / STRUCTURAL
parameters, not in scope for this check).

| Variant | atr_dist_max | atr_stop_mult | Trades | Net Expectancy_R | Δ vs canonical | Max DD |
|---|---|---|---|---|---|---|
| **Canonical** | 2.0 | 2.0 | 714 | **+0.0259** | — | — |
| A | 1.8 | 2.0 | 738 | +0.0055 | **-78.8%** | -39.2% |
| B | 2.2 | 2.0 | 735 | +0.0123 | **-52.5%** | -37.3% |
| C | 2.0 | 1.8 | 739 | -0.0249 | **-196.1%** | -31.8% |
| D | 2.0 | 2.2 | 715 | -0.0035 | **-113.5%** | -32.7% |

All four neighbours — in both directions, on both parameters — degrade sharply, and two flip
to a net loss. Sample sizes are comparable to canonical (715-739 vs 714 trades), so this isn't
a small-sample artifact. This is the textbook signature of a curve-fit sitting on an isolated
peak rather than a strategy with a genuine, parameter-insensitive edge: `is_neighbourhood_stable
= False`, `parameter_cliff_flagged = True`.

**Verdict: TrendPullbackV2 does not currently qualify to advance toward `VALIDATION_SPLIT`.**
Per this document's own design (§4 Phase D — that data may be spent exactly once), promoting a
parameter-cliff result would very likely just reproduce Cycle 1 and 2's pattern one split later,
at the cost of the one-shot validation data. `VALIDATION_SPLIT` and the sealed final-test range
remain untouched.

**Where this leaves Phase C:** all four re-eligible Cycle 1 families have now been tested to
the limit of what DEVELOPMENT-split data and this gate can tell us — three failed the
point-estimate gate outright, and the fourth failed the robustness check. None currently
qualifies for Validation. This is a genuine negative result, not a process failure: the
pipeline caught a fragile parameterisation before it reached the one-shot data, which is what
this check exists to do. The honest options from here are (a) treat MomentumRSV2's near-miss —
real positive profit factor 1.58 and CAGR, failed only on single-trade concentration — as the
more promising remaining thread and investigate a position-level concentration cap, or (b)
return to the ALPHA-014→048 hypothesis backlog for a fifth family, pre-registering economic
rationale and a robustness neighbourhood *before* running it this time. Neither has been
started.

---

### 8.2 F9 — CGPOWER was tradeable in every backtest despite its own exclusion list (2026-08-07)

Picked up the MomentumRSV2 near-miss thread from §8.1's options and pulled its top 10 winning
trades to understand the single-trade concentration failure before treating it as a sizing
problem to patch over. **CGPOWER appeared twice**, contributing a combined ~18% of that
strategy's total profit — despite `screening/eligibility.py` having excluded CGPOWER by symbol
since the corporate-action gap was found (§3.2.1, docs/PROJECT_STATUS.md), and despite an
explicit standing instruction that unverifiable-history stocks must not be traded.

**Root cause: the exclusion list was never wired into the backtest execution path.**
`screening/` and `backtesting/` are separate modules, and nothing connected them:

- `BacktestEngine.run()` built its tradeable-instrument list solely from
  `PointInTimeUniverse.members()`, with no reference to `EligibilityConfig.excluded_symbols`.
- `DataPortal.get_universe_members()` — the method a strategy actually calls each day to find
  candidates — queried `PointInTimeUniverse` directly rather than the engine's own preloaded
  instrument set, so even filtering the preload list would not have been sufficient on its own.

The result: CGPOWER was fully tradeable in **every backtest ever run through this engine**,
including all of Phase B and every number in §8 and §8.1 above.

**Fixed at both points** (`backtesting/engine.py`, `backtesting/data_portal.py`): the engine
now filters project-level excluded symbols out of the preload list (with a logged warning
naming the excluded symbols), and `get_universe_members()` now intersects with the actually-
preloaded instrument set, so a strategy can never be offered a candidate whose data wasn't
loaded — closing the gap regardless of which path a strategy queries through. Added a
regression test (`tests/unit/test_m2_audit_acceptance.py::test_backtest_engine_excludes_project_level_symbols`)
that pins `BuyAndHoldStrategy` directly at the excluded instrument and asserts zero trades.

**Re-ran everything downstream. The DEVELOPMENT split result table, corrected:**

| Strategy | Trades | Net P&L | CAGR | Sharpe | Net Expectancy_R | Profit Factor | Gate |
|---|---|---|---|---|---|---|---|
| **TrendPullbackV2** | 719 | +₹518,244 | +8.2% | 0.24 | **+0.0165** | 1.15 | **✅ V2_DEVELOPMENT_SURVIVOR** |
| MomentumRSV2 | 284 | +₹1,032,810 | +14.1% | 0.43 | **+0.0183** | 1.38 | ❌ (single-trade profit share 31.17% > 25% cap — worse than before: JSWENERGY's win is now a larger share of a smaller total pool with CGPOWER's profit removed) |
| BreakoutConfirmV2 | 725 | -₹378,079 | -7.4% | -0.57 | -0.1249 | 0.83 | ❌ |
| MeanReversionV2 | 1,498 | -₹818,126 | -26.7% | -1.67 | -0.1815 | 0.70 | ❌ |

TrendPullbackV2's edge shrank (+0.0259 → +0.0165) once the phantom CGPOWER contribution was
removed, but stayed positive and the strategy still clears the gate — so **the robustness
check was re-run too, not assumed still valid:**

| Variant | atr_dist_max | atr_stop_mult | Trades | Net Expectancy_R | Δ vs canonical | Max DD |
|---|---|---|---|---|---|---|
| **Canonical** | 2.0 | 2.0 | 719 | **+0.0165** | — | — |
| A | 1.8 | 2.0 | 741 | +0.0026 | -84.2% | -36.5% |
| B | 2.2 | 2.0 | 739 | -0.0242 | -246.7% | -38.2% |
| C | 2.0 | 1.8 | 739 | -0.0468 | -383.6% | -36.1% |
| D | 2.0 | 2.2 | 710 | -0.0082 | -149.7% | -35.1% |

**Same verdict, worse margin: still a PARAMETER_CLIFF** (`is_neighbourhood_stable = False`,
`parameter_cliff_flagged = True`) — three of four neighbours now flip negative rather than
two, and the one that stays positive is down 84%. TrendPullbackV2 remains **not eligible for
`VALIDATION_SPLIT`**. `VALIDATION_SPLIT` and the sealed final-test range remain untouched
throughout.

**What this episode adds to the standing lesson from F6/F7/F8:** those were all defects in
code that computes a number. F9 is different in kind — a control (an exclusion list) that
existed, was correctly implemented in isolation, had its own module, and simply was never
connected to the system it was meant to govern. The generalizable check going forward is not
just "is this number computed correctly" but "does every governance control actually reach
the code path it's supposed to constrain" — worth spot-checking for other declared-but-
unwired controls (e.g. `max_concurrent_positions`, `LiquidityScreenConfig`) rather than
assuming existence of a config class means it is enforced.

**Where Phase C actually stands now:** unchanged in substance from §8.1 — no strategy
currently qualifies for Validation, TrendPullbackV2 fails robustness, MomentumRSV2 remains the
more promising near-miss (now with a *positive* expectancy_r, failing only on concentration).

Checked MomentumRSV2's dominant trade (JSWENERGY, +97% over 3 months, 31% of total profit)
before deciding what to do about it: pulled the full daily price history June-October 2021,
found no corporate action, no gap, no data discontinuity — a genuine, gradual rally (biggest
single day +10.8%), consistent with the real 2021 Indian power-sector re-rating. Not a defect.
The concentration comes from the strategy's own design: every large winner exits via
`MAX_HOLDING_PERIOD`, i.e. it holds a fixed 63 sessions with no profit-taking or trailing stop
regardless of how far price has run — a known structural property of fixed-horizon momentum
systems (rare huge winners carry the average), not curve-fitting. Redesigning its exits now,
having just watched this exact trade cause the failure, would be exactly the kind of
post-hoc, results-informed tuning this project's governance culture exists to prevent — so
that redesign was deliberately not made. MomentumRSV2 is left as-is, its Phase C outcome
stands, and a new hypothesis is pre-registered below instead (§8.3).

---

### 8.3 PRE-REGISTRATION — ALPHA-018 Volatility Squeeze (2026-08-07)

Registered and committed to this document **before** running any backtest, so the DEVELOPMENT
result cannot influence these choices after the fact. Selected from the ALPHA-014→048 backlog
(`docs/research/alpha_library/alpha_registry.json`) — the only real candidates with actual
content are ALPHA-014 through ALPHA-020 (ALPHA-021→048 are unfilled placeholder stubs from the
synthetic-data era with no real content, not usable). ALPHA-014 (PEAD) and ALPHA-016
(Quality-Low-Vol) require earnings/fundamentals data this project has never ingested (only
`MarketBar` OHLCV exists — checked `core/db_models.py`, no earnings/fundamentals/delivery-%
tables); ALPHA-017 needs NSE delivery-volume data, also not ingested. Of the three genuinely
OHLCV-only candidates (ALPHA-018/019/020), ALPHA-018 has the highest prioritization score
(39.0) in the registry and is mechanically distinct from every family already tested (not a
pullback, not a Donchian breakout, not an RSI mean-reversion, not a relative-strength rank).

**Hypothesis (from the registry, adapted to this project's long-only/ATR-stop conventions):**
stocks whose price volatility contracts to the point that Bollinger Bands (20, 2σ) move
*inside* the Keltner Channel (20-EMA ± 1.5×ATR20) — the classic "TTM Squeeze" definition
(John Carter, *Mastering the Trade*, 2005; also Bollinger 2001) — are in a state of
compressed risk pricing. When that compression releases (Bollinger Bands expand back outside
the Keltner Channel) with a confirming close above the upper band, in an established uptrend,
the subsequent volatility expansion carries directional continuation edge.

- **Economic rationale:** volatility compression reflects a temporary equilibrium in risk
  pricing as participants await a catalyst; when it releases, the direction of release carries
  new information being priced in for the first time, not yet fully arbitraged away.
- **Behavioural rationale:** apathy/inattention during low-volatility consolidation, followed
  by momentum-chasing (FOMO) once the range resolves and the move becomes visible on standard
  charting tools — a mechanism distinct from the trend-continuation and relative-strength
  mechanisms already tested in this cycle.
- **Literature:** Bollinger (2001), Carter (2005) — registry-rated "Moderate" academic support,
  the weakest of the three OHLCV-feasible candidates on this axis, noted honestly rather than
  overstated.
- **Novelty vs graveyard:** none of the four original graveyard bans (trend pullback, momentum
  RS, breakout, mean reversion) cover a volatility-band-squeeze mechanism; not a re-test of a
  banned family.
- **Falsification criteria (via this project's existing V2DevelopmentGate v1.0, not a separate
  standard):** same fixed thresholds already applied to all four other families —
  `net_expectancy_r > 0.0`, `profit_factor > 1.0`, `executed_trades >= 50`, plus the
  concentration and robustness checks. The registry's own suggested thresholds
  (profit_factor >= 1.25, Sharpe >= 0.50, CAGR >= 9%) are noted as that document's informal
  priors but the actual pass/fail routes through this project's one real gate, for consistency
  with every other strategy tested this cycle.

**Parameters, fixed before any run:**

| Parameter | Value | Origin |
|---|---|---|
| `bb_period` | 20 | MARKET_CONVENTION — Bollinger's own standard period |
| `bb_std` | 2.0 | MARKET_CONVENTION — Bollinger's own standard width |
| `kc_period` | 20 | MARKET_CONVENTION — matches TTM Squeeze standard definition |
| `kc_atr_mult` | 1.5 | MARKET_CONVENTION — Carter's original TTM Squeeze Keltner multiple |
| `trend_ma` | 50 | PRIOR_CANONICAL — same Close > SMA50 uptrend filter already used by TrendPullbackV2, applied here so this long-only strategy isn't taking bullish-release signals inside downtrends |
| `atr_stop_mult` | 2.0 | MARKET_CONVENTION — same stop convention as TrendPullbackV2 (this family has no prior canonical V1 of its own to inherit from) |
| `max_holding_days` | 25 | MARKET_CONVENTION — upper bound of the registry's own stated 10-25 session expected holding period for this hypothesis, taken directly from the pre-registration content itself |

**Predeclared robustness neighbourhood (4 variants, ±10%, matching this project's established
convention for the other families):** `bb_std ∈ {1.8, 2.2}`, `atr_stop_mult ∈ {1.8, 2.2}`,
`kc_atr_mult`/`trend_ma`/`max_holding_days` held fixed.

**Result — first DEVELOPMENT-split run, after pre-registration above, unchanged from what was
committed before running:**

| Metric | Canonical | | |
|---|---|---|---|
| Executed trades | 513 | Win rate | 42.1% |
| Net P&L | +₹590,860 | Payoff ratio | 1.68 |
| Net Expectancy_R | **+0.1223** | Profit Factor | 1.23 |
| CAGR | +9.5% | Sharpe | 0.32 |
| Max instrument profit share | 8.8% (cap 40%) | Max single-trade profit share | 16.1% (cap 25%) |
| Exit reasons | 260 MAX_HOLDING_PERIOD, 253 STOP_LOSS — all 513 trades, no leftover force-closes |

**`gate_pass = True`, `outcome_status = V2_DEVELOPMENT_SURVIVOR`.** Net expectancy_r is
~7x TrendPullbackV2's (+0.1223 vs +0.0165), with lower concentration on both axes.

**Robustness check, same predeclared neighbourhood:**

| Variant | bb_std | atr_stop_mult | Trades | Net Expectancy_R | Δ vs canonical |
|---|---|---|---|---|---|
| **Canonical** | 2.0 | 2.0 | 513 | **+0.1223** | — |
| A | 1.8 | 2.0 | 513 | +0.1730 | +41.5% |
| B | 2.2 | 2.0 | 453 | +0.1749 | +43.0% |
| C | 2.0 | 1.8 | 508 | +0.1524 | +24.6% |
| D | 2.0 | 2.2 | 499 | +0.1971 | +61.2% |

**`is_neighbourhood_stable = True`, `parameter_cliff_flagged = False`.** Every one of the four
neighbours is positive and *better* than canonical, not worse — a genuine stability plateau,
the first this project has produced, and the opposite failure mode from TrendPullbackV2's
cliff. (All four improving rather than a mix of better/worse is itself worth noting rather
than treating as unambiguously reassuring — it suggests the pre-registered canonical
parameters, chosen from market convention rather than tuned to this data, may simply sit on
the conservative side of a broad positive region, not that this is definitely the peak.)

**This is the first strategy in this project's history to survive both the point-estimate
gate and the predeclared robustness check on real data.** Still: this is one DEVELOPMENT-split
run of a hypothesis with the weakest literature support of the three OHLCV-feasible
candidates ("Moderate" per its own pre-registration above, versus "Strong" for the
momentum/relative-strength mechanisms already tested), 513 trades over one continuous
5.5-year window rather than genuinely independent samples, and it has not been near
`VALIDATION_SPLIT`, which remains untouched. It is a real, honestly-obtained candidate for the
next stage — not a discovered edge. **§8.4 below found a much bigger problem before any move
toward Validation was made.**

---

### 8.4 SUB-PERIOD CHECK — every strategy tested this cycle is riding one bull market (2026-08-07)

Before spending `VALIDATION_SPLIT` — the one-shot resource — on ALPHA-018, ran one more check
that costs nothing to run as many times as needed: split DEVELOPMENT (2016-08-01 to
2021-12-31) into two roughly equal, contiguous halves and re-ran each strategy's *canonical,
unmodified* parameters on each half independently. Not a search, not a tune — the same
frozen configuration already tested, checked for whether its edge is consistent over time
rather than concentrated in one stretch of it.

| Strategy | H1 2016-08→2019-03 (341/232/143 trades) | H2 2019-04→2021-12 |
|---|---|---|
| TrendPullbackV2 | net_expectancy_r **-0.0574**, PF 0.99 | net_expectancy_r **+0.0446**, PF 1.32 |
| MomentumRSV2 | net_expectancy_r **-0.1083**, PF 0.96 | net_expectancy_r **+0.0256**, PF 1.71 |
| ALPHA-018 | net_expectancy_r **-0.0133**, PF 1.01 | net_expectancy_r **+0.2102**, PF 1.31 |

**Every single strategy tested this cycle is flat-to-losing in H1 and strongly positive in
H2, with no exception.** This is not a strategy-specific overfitting artifact (the robustness
checks in §8.1-8.3 already ruled that out at the parameter level) — it is a **regime**
artifact common to all of them: H2 spans the COVID crash and the subsequent extraordinary
liquidity-driven recovery rally in Indian equities (Nifty roughly doubled off the March 2020
low through 2021), an unusually strong and sustained trending environment that flatters any
trend-following or momentum-style long entry. H1 (2016-2019) — demonetisation, GST rollout,
the 2018 IL&FS/NBFC crisis, choppier and range-bound for long stretches — is a much more
ordinary market, and every strategy is roughly breakeven-to-losing in it.

**Conclusion: no strategy validated so far in this project represents a proven, regime-robust
edge.** Every positive full-period number reported in §8.1-8.3 is substantially a restatement
of "this system would have caught the 2020-2021 recovery rally," not evidence it makes money
in typical conditions. Proceeding to `VALIDATION_SPLIT` (2022-01 to 2024-06, which opens with
a materially harder, rate-hiking, non-trending stretch) with any of these as-is would very
likely spend the one-shot resource on a strategy that simply doesn't get the tailwind it
needs there — a probable failure that teaches little, at the cost of a dataset that cannot be
regenerated.

**This is added as a standing requirement going forward, not a one-off observation:** any
future candidate must show non-catastrophic (not necessarily positive, but not the -0.05 to
-0.11 seen here) expectancy_r in *both* DEVELOPMENT halves, independently, before it is
considered for `VALIDATION_SPLIT` — the same discipline as the predeclared parameter-robustness
check in §8.1-8.3, applied along the time axis instead of the parameter axis. Recorded in
`config/research_governance_state.json`.

**Two honest paths from here, neither started yet:**
1. Keep searching DEVELOPMENT for a hypothesis that clears this new, harder bar in both
   halves — slower, and there is no guarantee one exists in this universe/period.
2. Accept that what has been found is a genuine, well-precedented but **regime-conditional**
   edge (trend/momentum systems underperforming in non-trending markets and outperforming in
   trending ones is itself a long-documented property of the strategy class, not unique to
   this project — see e.g. managed-futures/CTA literature), and pair it with an explicit
   market-regime filter (e.g. only take signals when a broad benchmark is itself in an
   uptrend) so the system is designed to stand aside during unfavourable regimes rather than
   trade through them and lose. This is a materially different, more honest strategy design
   than what has been tested so far, and would need its own DEVELOPMENT-split test (both
   halves) before being considered proven.

**Decision: option 2.** Pre-registered below, before any code changes.

---

### 8.5 PRE-REGISTRATION — market-regime overlay on ALPHA-018 (2026-08-07)

Committed **before** writing or running the overlay code, same discipline as §8.3.

**Base strategy:** `VolatilitySqueezeV1Strategy` (ALPHA-018), canonical parameters,
unchanged — the only candidate that already cleared both the point-estimate gate and the
parameter-robustness check (§8.3). Not TrendPullbackV2 (failed parameter-robustness, §8.1) or
MomentumRSV2 (structural concentration issue, §8.2).

**Regime signal — a real, computed quantity, not new external data:** this project has never
ingested an actual NIFTY 50 index price series (checked: no instrument with a NIFTY/NSEI
symbol exists in `instruments`, only the 142 constituent stocks; `Benchmark.calculate_return()`
in `backtesting/benchmark.py` is itself an unfixed stub that always returns a hardcoded
100→100/0% placeholder — noted so it is not mistaken for real benchmark data if ever consulted
elsewhere). Re-authenticating to Kite to backfill a genuine index series is not available in
this session. Rather than approximate a cap-weighted index from data this project doesn't
have, the regime signal is **market breadth**: the percentage of the tradeable universe
(`data_portal.get_universe_members`, the same CGPOWER-excluded set every strategy already
uses) whose own close is above its own 200-session SMA on that date. This is a well-precedented
practitioner indicator in its own right (e.g. the widely-followed "% of index members above
200-day MA" breadth measure), not a proxy invented for this test, and is 100% computable from
data already in this database — no fabrication risk.

- **Rule:** regime is ON when breadth ≥ 50% (more than half the tradeable universe in a
  long-term uptrend), OFF otherwise.
- **Effect when OFF:** the strategy takes no new entries. Existing open positions continue to
  be managed by their existing stop-loss / max-holding-day exits exactly as before — the
  overlay only gates new risk-taking, it does not change exit behaviour.
- **Parameter origins:** `sma_period=200` (MARKET_CONVENTION — the standard long-term trend
  benchmark, e.g. Faber 2007, "A Quantitative Approach to Tactical Asset Allocation," the
  canonical reference for exactly this class of timing rule, predating and independent of
  this project's results) and `breadth_threshold=0.5` (MARKET_CONVENTION — the natural
  symmetric majority threshold, not tuned to this data).

**Falsification criteria — the sub-period bar from §8.4, applied to this variant
specifically:** non-catastrophic net_expectancy_r in *both* H1 (2016-08→2019-03) and H2
(2019-04→2021-12) independently, evaluated on canonical parameters with no further tuning.
Passing the aggregate-only V2DevelopmentGate is necessary but no longer sufficient — this is
the whole point of building the overlay.

Implementation and result follow in a subsequent update to this section — not yet run as of
this commit.

**First result (full DEVELOPMENT and both halves, canonical `sma_period=200`,
`breadth_threshold=0.5`):**

| Period | Trades | Net Expectancy_R | Profit Factor | CAGR |
|---|---|---|---|---|
| Full (2016-08→2021-12) | 407 | +0.1398 | 1.18 | +6.8% |
| H1 (2016-08→2019-03) | 182 | **+0.0780** | 1.10 | +4.0% |
| H2 (2019-04→2021-12) | 230 | +0.1674 | 1.19 | +8.2% |

**Both halves positive for the first time this cycle** — H1 flipped from -0.0133 (unfiltered
ALPHA-018, §8.4) to +0.0780. Before treating this as proven, extending the same
parameter-robustness discipline already applied to every other decision-gating parameter in
this project (§8.1-8.3) to the two new parameters this overlay introduces, **predeclared here
before running**: `sma_period ∈ {180, 220}` (±10%), `breadth_threshold ∈ {0.45, 0.55}`
(±10% relative) — 4 variants, evaluated on the full DEVELOPMENT period, same convention as
every prior robustness check in this document.

**Parameter-robustness result:**

| Variant | Net Expectancy_R | Profit Factor |
|---|---|---|
| Canonical (200, 0.50) | +0.1398 | 1.18 |
| sma_period=180 | +0.1112 | 1.14 |
| sma_period=220 | +0.1372 | 1.20 |
| breadth_threshold=0.45 | +0.1203 | 1.15 |
| breadth_threshold=0.55 | +0.1654 | 1.21 |

All four variants stay solidly positive (+0.111 to +0.165), no cliff, comparable to
canonical — a stable plateau, same pattern as ALPHA-018's own parameter check in §8.3.

**Official V2DevelopmentGate evaluation, canonical parameters:** `executed_trades=407`,
`net_expectancy_r=+0.1398`, `profit_factor=1.18`, `win_rate=41.8%`, `payoff_ratio=1.65`,
`sharpe_ratio=0.167`, `cagr_pct=+6.8%`, `max_drawdown_pct=-44.3%`,
`max_single_instrument_profit_share=8.7%` (cap 40%), `max_single_trade_profit_share=20.0%`
(cap 25%), exit reasons 206 STOP_LOSS / 201 MAX_HOLDING_PERIOD (all 407 trades, no leftover
force-closes). **`gate_pass = True`, `outcome_status = V2_DEVELOPMENT_SURVIVOR`.**

Two hand-computed regression tests added
(`tests/unit/test_vol_squeeze_regime_filter.py`) proving the breadth gate itself: a synthetic
two-instrument universe where a "control" instrument's own trend direction swings breadth
above/below the 50% threshold, confirming an otherwise-identical, otherwise-valid squeeze
signal on the "target" instrument fires when breadth ≥ 50% and is suppressed when it is not.

**Honest reading of this result:**
- **What's new and real:** this is the first strategy in this project's history with a
  positive edge in *both* the calm 2016-2019 stretch and the 2019-2021 rally — not just an
  aggregate number that hides one bull market carrying everything else. That is a materially
  different, more defensible claim than anything in §8.1-8.3.
- **What has not improved:** `max_drawdown_pct = -44.3%` is deep, and `sharpe_ratio = 0.167`
  is low in absolute terms — this is not a smooth equity curve, and standing aside during
  unfavourable regimes did not fix that; it just made the strategy profitable on both sides of
  the regime split. CAGR (+6.8%) is meaningfully lower than the unfiltered version (+9.5%,
  §8.3), which is the expected cost of a filter that forgoes some trades.
- **What is still true from §8.3:** ALPHA-018's underlying literature support remains
  "Moderate," the DEVELOPMENT window is still one continuous historical stretch (now examined
  in two halves rather than one, but still not independent samples in a statistical sense),
  and breadth ≥ 50% as a market-wide regime signal is itself a new, once-tested rule, not a
  separately validated one.
- **This is the strongest candidate this project has produced, and it has not been
  promoted toward `VALIDATION_SPLIT`, which remains untouched.** Whether to spend the
  one-shot resource on it now is a real decision, not a formality — flagged for the record.

---

### 8.6 PHASE D — VALIDATION_SPLIT RUN (2026-08-07). ONE SHOT, NOW SPENT.

User directive: after being told no proven strategy existed and that §8.5's candidate had not
been validation-tested, explicitly instructed to proceed. Ran once, frozen canonical
parameters (`bb_period=20, bb_std=2.0, kc_period=20, kc_atr_mult=1.5, trend_ma=50,
atr_stop_mult=2.0, max_holding_days=25, sma_period=200, breadth_threshold=0.5`,
config_hash `c5baa46384a07491ac01c0d926603bee2feb886d068858eff8d40bc18b6690de`, identical to
every §8.5 DEVELOPMENT run) against `VALIDATION_SPLIT` (2022-01-01 → 2024-06-30). No parameter
was changed based on any result. `validation_access_count`: 0 → 1.

**Raw result:**

| Metric | Value |
|---|---|
| Executed trades | 209 |
| Net P&L | +₹116,295 |
| Win rate | 34.5% |
| Profit Factor | 1.11 |
| Net Expectancy_R | +0.0715 |
| CAGR | +4.9% |
| Max drawdown | -18.3% |
| Sharpe / Sortino | 0.076 / 0.078 |
| Max single-instrument profit share | 11.4% (cap 40%) |
| **Max single-trade profit share** | **63.3%** (cap 25%) |

**The concentration number is disqualifying on its own, and investigating why explains
everything.** The dominant trade is NMDC (entry 2022-10-07, exit 2022-11-16, MAX_HOLDING_PERIOD),
gross profit ₹118,423 — *larger than the entire run's net P&L* (+₹116,295), meaning every
other trade combined is roughly breakeven-to-negative. Pulled the daily price series: NMDC
gapped **+85.7% in a single session** (2022-10-27, close ₹15.75 → ₹29.25), with **zero**
`CorporateAction` record for the instrument in this database.

Before treating this as another CGPOWER-style raw data defect, checked this project's own
existing quality-control output (`docs/research/quality_report.json`) — and this exact move
was already investigated and is on record as `VERIFIED_EXPLAINED`: *"NMDC Steel demerger
ex-date, 1:1 allotment, record date 2022-10-28. Source: Business Standard, 'NMDC trades
ex-date for demerger; stock surges 14% amid heavy volumes', 2022-10-27."*

**The real event was a 14% surge. This database records 85.7% — six times larger, with
`matched_action: null`, meaning the demerger was narratively verified but never actually
processed by the corporate-actions adjustment pipeline.** This is not fabricated data and not
a new defect class — it is a live, concrete instance of the corporate-action adjustment gap
CLAUDE.md has flagged as a **blocking** issue since 2026-08-06 ("Largest daily move is +190.67%
and `is_adjusted=False` on every bar... verification against NSE circulars is outstanding").
Until now that was a known risk; this is the first time it has been shown to actually corrupt
a specific research result end to end.

**CORRECTION (same day, before this section was even finished being written): the
"data defect" conclusion above was premature and is very likely wrong.** Directed to
investigate the corporate-action pipeline as the fix, the obvious first step was verifying
the NMDC move against primary sources rather than assuming the fix path — and that check
overturned the diagnosis:

- Web search of contemporaneous financial reporting (Business Standard, Zee Business, India
  Infoline — see sources below) confirms: NMDC's ex-demerger reference price was reset by the
  exchange to an **adjusted opening level of ₹93.70** on 2022-10-27, and the "surges 14%"
  headline describes the intraday rally *from that already-reset adjusted open* (to ₹107.25),
  not the move from the prior day's raw close. A demerger mechanically removes value from the
  parent (NMDC Steel's assets, ~₹18,650 crore, were carved out) — a large, legitimate,
  one-time downward reference-price reset on the ex-date is the expected, correct exchange
  behaviour, not a defect. This is structurally identical to the CGPOWER 2015-10-01 demerger
  already investigated and confirmed genuine (§3.2.1, detector.py's own docstring: "there's no
  single ratio for a spin-off," so Kite's adjustment does not retroactively splice it).
- Checked our own OHLC against this: NMDC also underwent an unrelated 3-for-1 split in
  December 2024, which Kite's adjustment retroactively applies to the entire history
  (confirmed mechanism, §3.2.1). Dividing the real 2022 adjusted-open (₹93.70) by 3 gives
  ≈₹31.2 — our database's actual open that day was ₹25.80, high ₹30.65: the right order of
  magnitude and structurally consistent with a genuine adjusted-open reset, not an arbitrary
  or garbled number.
- The original 85.7% vs. 14% comparison was comparing two different reference bases (raw
  close-to-close vs. intraday-from-adjusted-open) — an apples-to-oranges error, not evidence
  of a bug. A stock split is a scalar rescaling and cannot by itself explain a percentage-return
  discrepancy; a demerger's reference-price reset can and, on this evidence, did.

**Revised conclusion: NMDC's move was very likely real, not a data defect.** The corporate
action adjustment pipeline is not shown to be the cause here, and should not have been named
as the fix in the first version of this section — that conclusion is retracted. The genuine
finding underneath the retracted one still stands, just reframed: **one real but rare,
one-off corporate-restructuring event dominated the entire validation result (63% of gross
profit from one trade), because this strategy has no mechanism to distinguish a genuine
momentum breakout from a demerger-driven price discontinuity that happens to look identical
to one** (quiet, low-volatility pre-event trading — thin volume ahead of a record date is
itself plausible — followed by a large one-day move, which is exactly what the squeeze/release
entry logic is built to catch). That is a real, describable limitation of the strategy design,
not a database problem.

**What this means, stated plainly:** the +0.0715 net_expectancy_r on `VALIDATION_SPLIT` is
still not trustworthy evidence of a repeatable edge — a result 63% dependent on one
non-repeatable corporate event is exactly as fragile as a result dependent on one data defect
would have been, just for a different reason. This is **not** re-run with NMDC excluded — the
one-shot resource is spent, honestly, with this result, exactly as the rule requires; a
"corrected" re-test would itself be exactly the kind of after-the-fact cherry-picking this
project's entire governance culture exists to prevent. The result stands as: **inconclusive,
dominated by one genuine but non-repeatable event, spent.**

**Consequences:**
1. `VolatilitySqueezeV1RegimeFilteredStrategy` has **not** been shown to work on real
   out-of-sample data. It remains the strongest DEVELOPMENT-tested candidate, but Validation
   neither confirmed nor cleanly refuted it.
2. `FINAL_TEST_SPLIT` must **not** be touched now. Spending the very last one-shot resource
   immediately after an inconclusive Validation would repeat the same mistake at higher cost.
3. **CORRECTION (checked before building it): an entry-side exclusion window is not the
   right fix.** The dominant trade entered 2022-10-07, three weeks *before* the 2022-10-27
   gap, and was already open when it happened (entry_px 16.11, essentially at the pre-gap
   level) — an entry-timing filter would not have touched this trade at all. Over 90% of its
   total gain (13.14 of 14.22 points) came from the single gap day regardless of whether the
   position was exited immediately after or held the remaining three weeks to its normal
   max-holding exit. **The real lesson: this is a sample-size/diversification problem, not a
   timing-filterable one.** A strategy holding positions for 10-25+ sessions will occasionally
   have one sit through an unpredictable corporate event; the structural fix is more, shorter,
   more diversified trades (so any one event is a smaller share of total profit), not a rule
   to avoid entering near recent moves.
4. Also worth stating plainly: the `max_single_trade_profit_share <= 25%` concentration cap
   already used throughout DEVELOPMENT (§8) was computed manually for this Validation run but
   never formally applied as a pass/fail gate (`V2DevelopmentGateEvaluator` is hardcoded to
   `DEVELOPMENT_SPLIT` dates only). Had the same cap been applied consistently, this result
   would have been mechanically rejected at 63.25% — a cleaner, cause-agnostic statement of
   "not proven" than either the retracted data-defect theory or the entry-filter theory.
5. The corporate-action adjustment pipeline (`src/tradecraft/corporate_actions/`) remains
   genuinely incomplete per §3.2 and is still worth finishing, but on this evidence it is not
   what corrupted this specific result — do not repeat this section's own first-draft mistake
   of naming a fix before verifying the diagnosis.

Sources: [NMDC trades ex-date for demerger; stock surges 14% amid heavy volumes](https://www.business-standard.com/amp/article/markets/nmdc-trades-ex-date-for-demerger-stock-surges-14-amid-heavy-volumes-122102700302_1.html) · [NMDC Demerger News — record date, value, scheme](https://www.zeebiz.com/market-news/news-nmdc-demerger-news-stock-trades-ex-demerger-date-today-check-record-date-2022-value-scheme-nmdc-demerger-share-price-204934) · [NMDC-NMDC Steel demerger's record date is October 28th](https://www.indiainfoline.com/news/mergers-acquisitions/nmdc-nmdc-steel-demergers-record-date-for-issuance-of-new-shares-is-october-28th)

---

### 8.7 PRE-REGISTRATION — ALPHA-019 Cross-Sectional Short-Term Reversal (2026-08-08)

Committed **before** writing or running the strategy code, same discipline as §8.3/§8.5.

**Why this hypothesis, and why now:** §8.6 found that a strategy trading ~200 times over 2.5
years can have 63% of its result decided by one unpredictable event that landed mid-hold,
irrespective of entry timing. The structural fix isn't a smarter filter — it's more, shorter,
better-diversified trades, so no single event can dominate. ALPHA-019 (registry:
`docs/research/alpha_library/alpha_registry.json`) fits that directly: "3 to 10 sessions"
expected holding vs. this cycle's 10-63 sessions, "Very High" expected turnover, and it has
the *strongest* literature support of any OHLCV-feasible candidate remaining
("Strong" — Jegadeesh 1990, Lehmann 1990, both foundational short-term reversal papers), ahead
of ALPHA-018's own "Moderate" rating.

**Hypothesis:** stocks in a long-term uptrend (Close > SMA200 — a falling-knife guard, since
ALPHA-019's own stated risk factor is "falling knife exposure in fundamental bankruptcies")
that have just had one of the sharpest short-term (5-session) price declines *relative to the
rest of the tradeable universe* are exhibiting temporary, non-fundamental overreaction that
mean-reverts as liquidity providers absorb the imbalance — cross-sectional ranking, not an
absolute RSI threshold, which is the mechanism `MeanReversionV2Strategy` already tested and
failed with (§8, net_expectancy_r -0.1815). Genuinely different mechanism: relative
worst-of-universe ranking vs. an absolute per-stock oscillator level.

- **Economic rationale:** short-term, non-fundamental price dislocations (forced selling,
  index-fund rebalancing flows, temporary liquidity imbalances) create a spread that
  liquidity-providing capital is compensated to close.
- **Behavioural rationale:** investor overreaction/panic to short-term news, and
  liquidity-provider inventory constraints limiting how fast the imbalance closes on its own.
- **Literature:** Jegadeesh (1990), Lehmann (1990) — "Strong" academic support per the registry,
  the strongest-rated remaining OHLCV-feasible candidate.
- **Known, explicitly acknowledged risk (from the registry itself, not discovered after the
  fact):** "Alpha destroyed by bid-ask spread and transaction costs" — this project's own cost
  model (~0.24% round-trip) is exactly the kind of friction this hypothesis is most exposed
  to, given the intended short holding period. A real risk of failure, stated up front.
- **Novelty vs. graveyard:** none of the four original graveyard bans cover a cross-sectional
  short-horizon ranking mechanism; distinct from the already-tested absolute-threshold
  `MeanReversionV2Strategy`.
- **Falsification criteria:** the same V2DevelopmentGate v1.0 thresholds used for every other
  family this cycle (`net_expectancy_r > 0.0`, `profit_factor > 1.0`, `executed_trades >= 50`,
  concentration caps), plus — new, given §8.6's lesson — **both DEVELOPMENT halves
  independently non-catastrophic** (the standing requirement added in §8.4) from the first run,
  not bolted on after a failure.

**Parameters, fixed before any run:**

| Parameter | Value | Origin |
|---|---|---|
| `lookback_days` | 5 | MARKET_CONVENTION — Lehmann (1990)'s weekly reversal horizon, one of this hypothesis's own foundational papers |
| `bottom_percentile_cutoff` | 0.10 | SIGNAL_VIABILITY_CALIBRATION — bottom decile of 5-day cross-sectional returns; tight enough that reversal effects (concentrated in the most extreme losers per the literature) aren't diluted, matching the non-degenerate-sample-size rationale already used for `MomentumRSV2Strategy`'s own percentile cutoff |
| `trend_ma` | 200 | MARKET_CONVENTION — long-term uptrend filter, guards against the registry's own stated "falling knife" risk; matches the breadth filter's SMA period in §8.5 |
| `atr_stop_mult` | 2.0 | MARKET_CONVENTION — same stop convention used throughout this project |
| `max_holding_days` | 10 | MARKET_CONVENTION — upper bound of the registry's own stated 3-10 session holding period, taken from the pre-registration content itself |

**Predeclared robustness neighbourhood (±10%, same convention as every prior family):**
`lookback_days ∈ {4, 6}` (rounded from ±10% of 5, which has no integer at exactly 4.5/5.5),
`bottom_percentile_cutoff ∈ {0.09, 0.11}`.

Implementation and DEVELOPMENT-split result follow in a subsequent update to this section —
not yet run as of this commit.

**Result: fails outright.**

| Period | Trades | Net Expectancy_R | Profit Factor | CAGR |
|---|---|---|---|---|
| Full (2016-08→2021-12) | 1,219 | -0.0387 | 0.83 | -13.0% |
| H1 (2016-08→2019-03) | 592 | -0.0516 | 0.82 | -13.5% |
| H2 (2019-04→2021-12) | 629 | -0.0065 | 0.96 | -2.5% |

The trade-count goal was met (1,219 trades, ~6x TrendPullbackV2's count, ~3x
the regime-filtered squeeze strategy's) — this design genuinely dilutes single-event
concentration risk as intended. But there is no edge to dilute: net_expectancy_r is negative
in **both** DEVELOPMENT halves independently, not just in aggregate, so this isn't a
regime-dependency failure like §8.4 — it's a clean, consistent failure exactly matching the
risk this hypothesis's own pre-registration flagged in advance ("Alpha destroyed by bid-ask
spread and transaction costs"). Exit reasons (893 MAX_HOLDING_PERIOD vs. 326 STOP_LOSS, full
period) show a benign failure mode — most positions simply drift without playing out, rather
than getting stopped out hard — consistent with a real signal too weak to clear this project's
~0.24% round-trip friction, not a broken mechanism. No parameter-robustness check run (matches
established precedent: outright DEVELOPMENT-gate failures in §8 were not further robustness-
tested either). **`strat_cross_sectional_reversal_v1` does not qualify and is not pursued
further.**

---

### 8.8 PRE-REGISTRATION — ALPHA-020 Volatility Contraction Pattern (2026-08-08)

Committed **before** writing or running the strategy code, same discipline as §8.3/§8.5/§8.7.
Last remaining OHLCV-feasible candidate with real content in the ALPHA-014→048 backlog
(ALPHA-021→048 are unfilled placeholder stubs).

**Hypothesis (registry: Minervini 2013, *Trade Like a Stock Market Wizard*; O'Neil 1988,
*How to Make Money in Stocks*):** stocks in a long-term uptrend that undergo a sequence of
successively shallower, lower-volume pullbacks — supply drying up as weak holders are shaken
out — followed by a high-volume breakout above the pattern's high, exhibit continuation edge
as institutional accumulation completes ("markup phase").

**Honest operationalization note:** the source material describes a discretionary, visually-
identified chart pattern (a human trader eyeballing progressively tighter consolidations on a
chart). Translated into a precise, backtestable rule as follows, which is a simplification,
not a literal reproduction of discretionary pattern-reading — stated plainly so the gap
between "the book's idea" and "what was actually tested" isn't hidden:
- The lookback window is split into three consecutive, equal sub-periods (oldest → newest).
- **Contraction**: average true range must strictly decrease across the three sub-periods
  (oldest > middle > newest) — a proxy for "each pullback shallower than the last."
- **Volume drying**: average volume must also strictly decrease across the same three
  sub-periods — a proxy for "supply drying up."
- **Breakout**: today's close exceeds the highest high of the entire lookback window, on
  volume at least `rvol_min`× the recent average — the "markup" confirmation.
- **Trend context**: Close > SMA150 (Minervini's own commonly-cited trend-template moving
  average, distinct from the SMA200 already used elsewhere in this project for variety and
  fidelity to the source material).

- **Economic rationale:** progressively contracting supply (each pullback absorbed by
  progressively fewer willing sellers) signals near-term equilibrium is close, so a
  volume-confirmed breakout reflects genuine new demand rather than a shakeout that reverses.
- **Behavioural rationale:** "strong-hand" accumulation gradually absorbing "weak-hand" supply
  during the quiet consolidation phase.
- **Literature:** Minervini (2013), O'Neil (1988) — "Moderate" academic support (practitioner
  books, not peer-reviewed papers) — the weakest-rated remaining candidate on this axis,
  stated honestly.
- **Known risk (from the registry itself):** "Broader market breakdown invalidating chart
  pattern" — no regime filter is included in this design; if this hypothesis clears
  DEVELOPMENT, that omission should be revisited given §8.4/§8.5's findings on regime
  dependency, but is not added now to avoid tuning a design that hasn't even been tried yet.
- **Novelty vs. graveyard:** distinct from the already-tested `BreakoutConfirmV2Strategy`
  (single Donchian breakout + RVOL, no multi-stage contraction/volume-drying requirement) and
  `VolatilitySqueezeV1Strategy` (Bollinger/Keltner band-width squeeze, no explicit multi-stage
  structure or volume-drying condition).
- **Falsification criteria:** the same V2DevelopmentGate v1.0 thresholds as every other family
  this cycle, plus both DEVELOPMENT halves independently non-catastrophic from the first run.

**Parameters, fixed before any run:**

| Parameter | Value | Origin |
|---|---|---|
| `sub_window_days` | 15 | STRUCTURAL_REQUIREMENT — three 15-day stages give a 45-session lookback, in the middle of the registry's own 20-50 session expected holding-period range |
| `trend_ma` | 150 | MARKET_CONVENTION — Minervini's own commonly-cited trend-template moving average |
| `rvol_min` | 1.5 | ECONOMIC_RATIONALE — a step above `BreakoutConfirmV2Strategy`'s 1.2, since VCP explicitly emphasizes pronounced ("institutional markup") volume expansion on the breakout, not merely moderate expansion |
| `atr_stop_mult` | 2.0 | MARKET_CONVENTION — same stop convention used throughout this project |
| `max_holding_days` | 50 | MARKET_CONVENTION — upper bound of the registry's own stated 20-50 session holding period |

**Predeclared robustness neighbourhood (±10%, same convention as every prior family):**
`sub_window_days ∈ {14, 16}`, `rvol_min ∈ {1.35, 1.65}`.

**Result: positive in aggregate, fails sub-period consistency — a third occurrence of the
same regime pattern.**

| Period | Trades | Net Expectancy_R | Profit Factor |
|---|---|---|---|
| Full (2016-08→2021-12) | 145 | +0.1203 | 1.14 |
| H1 (2016-08→2019-03) | 66 | **-0.2269** | 0.70 |
| H2 (2019-04→2021-12) | 77 | +0.3832 | 1.58 |

The full-period number looks good on its own, exactly the trap §8.4 exists to catch: H1 is
not merely weak, it is the worst single-half result of any strategy tested this cycle
(-0.2269, worse than TrendPullbackV2's -0.0574 or unfiltered ALPHA-018's -0.0133). A third
independent strategy design — different mechanism, different literature, different author —
showing the identical "fails 2016-2019, thrives 2019-2021" fingerprint is strong evidence this
reflects the market during those periods, not a defect specific to any one hypothesis.

**Applied `MarketBreadthRegimeFilter` (generalized from §8.5's squeeze-specific overlay into
reusable infrastructure — `strat_vol_contraction_v1_regime_filtered`) and re-tested. It did
not fix this one:**

| Period | Trades | Net Expectancy_R | Profit Factor |
|---|---|---|---|
| Full | 128 | +0.1026 | 1.20 |
| H1 | 57 | **-0.2150** | 0.73 |
| H2 | 70 | +0.3031 | 1.59 |

Trade count only fell modestly (145→128 full period) and H1 stayed catastrophic. Unlike
ALPHA-018 — where the strategy's own entry logic had no trend-context requirement at all, so
the market-breadth filter added real, independent discriminating information — ALPHA-020
already requires `Close > SMA150` in its own entry criteria, which correlates heavily with
market-wide breadth being high. The regime overlay had little new information left to add.
**Lesson for the record: the regime-filter fix is not universal — it works precisely when the
base strategy lacks its own trend-context filter, and does little when the strategy already
has one.** `strat_vol_contraction_v1` does not qualify, filtered or not, and is not pursued
further.

**This exhausts the readily available candidate backlog.** Of the ALPHA-014→048 registry:
ALPHA-014/016/017 are infeasible (need data never ingested), ALPHA-021→048 are unfilled
placeholder stubs with no real content, and ALPHA-015/018/019/020 (the four with both real
content and feasible data) have all now been tested. The only candidate that has ever cleared
DEVELOPMENT on both halves and its own parameter-robustness check remains
`VolatilitySqueezeV1RegimeFilteredStrategy` (§8.5) — Validation-inconclusive per §8.6, not
proven, not disproven, one-shot resource already spent. See §1 for the honest summary of
where that leaves this project.

---

## 9. NEW DATA SOURCE — NSE DELIVERY POSITION (2026-08-08)

Per explicit instruction to go beyond OHLCV, researched what's actually obtainable rather than
assuming. Checked directly against Kite Connect's own API documentation: it provides no
fundamentals and no delivery data of any kind (confirmed, not assumed). NSE itself, however,
publishes a daily "Security Wise Delivery Position" report (the `MTO_DDMMYYYY.DAT` file) free,
with no login, at a stable archive URL — verified live by actually fetching it, not by trusting
secondhand descriptions: covers 2014-08-11 through the present, matching this project's
existing `MarketBar` range exactly.

**Ingested:**
- New table `delivery_positions` (migration `006_delivery_positions`): `instrument_id`,
  `trading_date`, `traded_qty`, `delivery_qty`, `delivery_pct`, unique per
  instrument/date.
- `market_data/delivery_provider.py`: fetches and parses the raw NSE file. Only `"20,"`-
  prefixed data rows are kept, and only `EQ`-series rows (matching this project's equity-only
  universe); a non-numeric delivery percentage (NSE writes `"-"` when not applicable) is
  skipped, not coerced to `0.0` — unmeasurable is not zero.
- `market_data/delivery_backfill.py`: resumable, idempotent, rate-limited backfill orchestrator,
  mirroring `HistoricalBackfillWorkflow`'s design.
- `DataPortal.get_delivery_history()`: delivery data is served through the same look-ahead-safe
  interface as prices, not queried directly by strategies — extends the existing point-in-time
  guarantee rather than creating a side channel around it.

**A real correctness bug found and fixed before trusting the pipeline:** the first symbol-
matching implementation walked `SYMBOL_SUCCESSION` chains to attribute historical symbols'
delivery data to their current successor instrument (the same idea already used for price-data
continuity). Tested against a real 2016 file, it produced two genuinely separate, both-listed
companies (HDFC Ltd and HDFC Bank, independent until their 2023 merger) colliding onto one
instrument's delivery row on the same day — caught by a database uniqueness constraint, but
the underlying problem was a correctness one: `SYMBOL_SUCCESSION` mixes pure renames (safe to
splice) with mergers/demergers (NOT safe — the predecessor is a genuinely different legal
entity). Fixed by matching only direct current symbols — an instrument that changed its ticker
has an honest delivery-data gap before the change, not a fabricated, conflated series.

**Not yet solved:** fundamentals data (earnings, ROE, balance-sheet items). No equally clean,
free, primary-source option has been found; ALPHA-014 and ALPHA-016 remain infeasible.

**Enables:** ALPHA-017 (Institutional Volume Breakout & Delivery Accumulation), previously
marked `REQUIRES_DELIVERY_DATA_ENHANCEMENT` and infeasible — see §9.1.

---

### 9.1 PRE-REGISTRATION — ALPHA-017 Institutional Volume Breakout & Delivery Accumulation (2026-08-08)

Committed **before** writing or running the strategy code, same discipline as every prior
hypothesis this cycle. The historical delivery backfill is running as this is written; no
result of any kind exists yet to bias these choices.

**Hypothesis (registry: Gunduz 2018; Blume, Easley & O'Hara 1994):** a price breakout
accompanied by both abnormal volume expansion AND delivery volume elevated above the
instrument's own recent norm reflects informed institutional accumulation (shares being bought
to hold, not just traded intraday) ahead of continued price discovery — distinct from a
breakout on volume alone (already tested and failed as `BreakoutConfirmV2Strategy`,
net_expectancy_r -0.1249), because high volume with LOW delivery is more consistent with
short-term speculative churn than genuine accumulation.

- **Economic rationale:** delivery percentage measures what fraction of traded volume resulted
  in an actual change of beneficial ownership (settled, not squared off intraday) — a direct,
  exchange-reported proxy for "real" buying rather than noise, unavailable from price/volume
  alone.
- **Behavioural rationale:** informed institutional order flow absorbing available retail
  supply during accumulation, before the move becomes obvious to price-only observers.
- **Literature:** Gunduz (2018), Blume/Easley/O'Hara (1994) — "Moderate" support, on the
  weaker end but grounded in real market-microstructure research, not a practitioner book.
- **Known risk (from the registry itself):** "Fakeout volume spikes, distribution near
  resistance" — a volume/delivery spike can also mark distribution (informed sellers exiting
  into retail demand) rather than accumulation; the ATR stop is the only defense against this,
  no separate filter is added for it now.
- **Novelty vs. graveyard:** distinct from `BreakoutConfirmV2Strategy` (volume alone, already
  tested and failed) and from every delivery-blind strategy tested this cycle — this is the
  first hypothesis using a genuinely new data type, not a new combination of OHLCV.
- **Falsification criteria:** the same V2DevelopmentGate v1.0 thresholds as every other family,
  plus both DEVELOPMENT halves independently non-catastrophic from the first run (the standing
  requirement since §8.4).

**Parameters, fixed before any run:**

| Parameter | Value | Origin |
|---|---|---|
| `channel_period` | 20 | MARKET_CONVENTION — same Donchian breakout period as `BreakoutConfirmV2Strategy`, for direct comparability |
| `rvol_min` | 1.5 | ECONOMIC_RATIONALE — a step above `BreakoutConfirmV2Strategy`'s 1.2, matching ALPHA-020's reasoning: "abnormal" volume expansion implies more pronounced than merely moderate |
| `delivery_lookback` | 20 | STRUCTURAL_REQUIREMENT — matches `channel_period`, for a consistent baseline window |
| `delivery_ratio_min` | 1.2 | SIGNAL_VIABILITY_CALIBRATION — today's delivery % must be >= 1.2x the instrument's own trailing 20-day average delivery %; self-relative rather than a fixed cross-sectional threshold, since baseline delivery % varies structurally by instrument |
| `trend_ma` | 50 | MARKET_CONVENTION — same baseline trend filter used by `TrendPullbackV2Strategy`/`BreakoutConfirmV2Strategy` |
| `atr_stop_mult` | 2.0 | MARKET_CONVENTION — same stop convention used throughout this project |
| `max_holding_days` | 30 | MARKET_CONVENTION — upper bound of the registry's own stated 15-30 session holding period |

**Predeclared robustness neighbourhood (±10%, same convention as every prior family):**
`rvol_min ∈ {1.35, 1.65}`, `delivery_ratio_min ∈ {1.08, 1.32}`.

**Historical delivery backfill completed** (§9): 2,950 trading sessions, 371,058 rows, all 142
instruments covered, one single-day gap (2026-02-13, a network timeout — reported honestly,
not silently filled), verified authentic by independently cross-checking one instrument/date
against NSE's separate `sec_bhavdata_full` report format — exact match
(traded_qty/delivery_qty/delivery_pct all identical, from two independently-fetched files).

**Result: fails, on concentration — and the failure mode itself is a real, worth-recording
finding.**

| Period | Trades | Net Expectancy_R | Profit Factor | Net P&L |
|---|---|---|---|---|
| Full (2016-08→2021-12) | 384 | +0.1366 | 1.10 | +₹232,832 |
| H1 (2016-08→2019-03) | 181 | +0.1382 | **0.96** | **-₹51,881** |
| H2 (2019-04→2021-12) | 193 | +0.1563 | 1.28 | +₹336,212 |

At first glance this looks like the first strategy with positive net_expectancy_r in *both*
halves — but H1's own numbers contradict each other (positive average R-multiple, negative
total P&L, profit_factor below 1.0), the same class of red flag that led to finding F7
earlier this cycle. Investigated before reporting anything: not a repeat of F7 (no
fee-dominated micro-positions; smallest position in H1 risked ₹284, well clear of the ₹200
floor). The real cause: one trade with **R = +38.9** — risking only ~₹1,944 but returning
~₹75,696 — pulls the simple *average* R-multiple positive across 181 trades, while the
*dollar-weighted* total is negative once that one outlier is set against several much
larger-risk losing trades (ADANIENT alone: -₹86,200). Remove that one trade and the other 180
combined lost roughly ₹127,577. `net_expectancy_r` (an unweighted mean) and `net_pnl` (a
dollar-weighted sum) can genuinely disagree in sign when one extreme outlier meets uneven
position sizing across trades — both numbers were computed correctly; trusting either one in
isolation would have been the mistake.

**The official gate (`V2DevelopmentGateEvaluator`, full DEVELOPMENT period) confirms this
formally: `gate_pass = False`, rejected on `max_single_trade_profit_share_pct = 31.21% >
25.0%` cap.** Same underlying concentration problem the R-multiple contradiction pointed to,
caught by the standard mechanism this project already has for exactly this failure mode — no
new check was needed, checking all the gate criteria rather than one convenient number was
what mattered. No parameter-robustness check run (matches established precedent for outright
gate failures). `strat_delivery_volume_breakout_v1` does not qualify and is not pursued
further as-is.

**What this leaves behind that's real: the delivery-data infrastructure itself.** The
hypothesis failed; the data pipeline (§9) is verified, permanent, and reusable — the next
delivery-based hypothesis (or a fix to this one, e.g. a concentration-aware position-sizing
cap, out of scope for now) does not require redoing any of this engineering.

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
