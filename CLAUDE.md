# TradeCraft — Project Context

**Goal:** an automated swing-trading tool that places real orders on Zerodha Kite under
human approval and makes money net of costs. The research platform is machinery for finding
something worth trading — it is not the product.

**Authoritative status: [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md). Read it first.**

---

## ⚠️ Do not trust the historical record

An independent audit on 2026-08-06 found that **Research Cycles 1 and 2 ran entirely against
a synthetic price database** generated inside this repo (`scratch/seed_real_market_bars.py`)
and stamped `source='ZERODHA_KITE_EOD'`. Ten instruments sharing one 21-day sawtooth,
`open == close` on every bar, constant ATR. Expected gross edge was exactly zero.

Their conclusions — *"no strategy survived development"*, *"PEAD V1 does not work"* — are
artifacts, not findings. Around 250 governance documents, SHA-256 certificates and forensic
audits attested to results that were meaningless. Most were deleted on 2026-08-06; they
remain in git history at commit `55e1360`.

- **Never cite an M3A–M3G result, gate verdict or graveyard entry as evidence.**
- The four graveyard bans (trend pullback, momentum RS, breakout, mean reversion) are
  **lifted** — those families were never validly tested.
- **Prefer artifacts to prose.** Narrative docs here were found to contain figures
  contradicting the JSON they claimed to summarise, and to attribute P&L to instruments that
  never existed in the database. When prose and data disagree, the data wins — and say so.
- **Verify before asserting status.** Query the database and read
  `config/research_governance_state.json` rather than repeating a document's claim.

---

## Current state (2026-08-06)

- **Real data ingested**: 142 instruments, 387,874 bars, 2014-08-11 → 2026-08-06, in
  **PostgreSQL**, passing the authenticity gate.
- **Blocking issue**: corporate action adjustment. Largest daily move is +190.67% and
  `is_adjusted=False` on every bar. Unadjusted bonuses create overnight gaps that never
  happened, stopping out every long in that name — this would reproduce the Cycle 1 symptom
  on real data. Pipeline is built (`src/tradecraft/corporate_actions/`); verification
  against NSE circulars is outstanding and needs a human.
- **No validated strategy exists. No order-placement code exists.** There is currently no
  evidence for or against any hypothesis.
- Next: Phase A in PROJECT_STATUS.md §4.

---

## Standing rules (adopted from real failures here)

1. **Provenance is a property of the numbers, never of a label.** A `source` column is worth
   nothing. `python -m tradecraft data verify` is blocking before any research run.
2. **No metric may gate a decision unless a unit test proves it correct on a hand-computed
   fixture** with known winners, losers and a force-closed position. `expectancy_r` had no
   such test and was structurally incapable of returning a positive number — it terminated
   every strategy ever run here.
3. **Fix defects as classes, not instances.** Cycle 2 found a missing-exit bug and fixed one
   site; the identical defect sat in all four Cycle 1 strategies and cost a whole cycle. A
   fix is not complete until every site with the same pattern is found and cleared.
4. **Every result names its source database** (`BacktestResult.data_provenance`). Ingestion
   wrote to PostgreSQL while 12 runners hardcoded SQLite, and nothing recorded which was used.
5. **Prefer assertions in code to certificates in prose.** ~250 governance documents did not
   catch what one 20-line test would have.
6. **Never pin a content hash of the market data.** It cannot distinguish tampering from
   correction, and here it actively blocked ingesting real data.
7. **A strategy must declare how it exits.** Enforced in `SignalIntent.__post_init__`.
8. **Unmeasurable is not zero.** Exclude and report coverage; never substitute `0.0`.

---

## Architecture

Modular monolith. Python 3.11+, PostgreSQL 16, SQLAlchemy 2.0, Alembic, FastAPI.

```
src/tradecraft/
  backtesting/        engine, execution, costs, metrics, portfolio, trade_ledger
  corporate_actions/  detector, adjuster, importer      <- newest, Phase A
  core/               db, db_models, db_provenance, preflight, time_utils
  market_data/        provider (Kite), backfill, authenticity, quality_report, calendar
  research/           sizing, feature/hypothesis registries, lab, diagnostics
  strategy/           base (SignalIntent/ExitSignal), registry, strategy families
  screening/          eligibility, regime, engine
  universe/           security master, historical membership, survivorship guard
```

**Single store.** Research code must obtain sessions via
`tradecraft.core.db_provenance.resolve_research_session()`. Hardcoded SQLite paths are
rejected by `guard_no_hardcoded_store()`.

**Raw vs adjusted bars.** Raw bars (`is_adjusted=false`) are immutable — what actually
printed, used for execution reasoning. Adjusted bars (`is_adjusted=true`) are derived and
regenerated on demand, used for research. The `uq_instrument_date_adj` constraint permits both.

---

## Commands

```bash
# Data
python -m tradecraft auth login                 # then: auth token <request_token>
python -m tradecraft data verify                # authenticity gate — blocking, exits 1 on fail
python -m tradecraft data quality-report        # stale names, extreme moves, duplicates
python -m tradecraft data corporate-actions detect --write-template docs/research/ca.csv
python -m tradecraft data corporate-actions import docs/research/ca.csv
python -m tradecraft data corporate-actions apply [--apply]
python -m tradecraft data backfill --universe NIFTY100 --start 2015-01-01

# Dev
pytest tests/ -q
ruff check src tests && mypy src
alembic upgrade head
```

Key test files: `tests/unit/test_r_multiple_and_sizing.py` (29 hand-computed fixtures),
`tests/unit/test_corporate_actions.py` (32), `tests/integration/test_data_authenticity.py`,
`tests/unit/test_db_provenance.py`.

---

## Conventions

- Long-only cash equity. No shorting, no leverage, integer share quantities.
- Signal at date T close → execution at T+1 open (`signal_date < entry_date <= exit_date`).
- Costs are real: STT, exchange charges, SEBI, GST, stamp duty, per-ISIN-per-day DP charges,
  plus 5bps slippage. Round-trip friction ≈ 0.24% before slippage.
- Timezone: UTC storage, explicit `Asia/Kolkata` for market logic.
- Never invent regulatory rules, broker capabilities, API endpoints, fees or market data.
  Distinguish KNOWN / ASSUMED / PROPOSED / VERIFIED / IMPLEMENTED / TESTED.
- Run `git` natively on Windows, not through a mounted filesystem — `git status` over the
  mount is slow enough to time out and strand `.git/index.lock`. Use `--no-optional-locks`
  for read-only queries.

---

## Further reading

| Document | What it is |
|---|---|
| [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | Authoritative status + 7-phase roadmap to live trading |
| [docs/research/REPO_AUDIT_2026-08-06.md](docs/research/REPO_AUDIT_2026-08-06.md) | The audit, with line references |
| [docs/research/NEXT_STEPS.md](docs/research/NEXT_STEPS.md) | Remediation state and commands |
| [docs/research/known_mistakes.md](docs/research/known_mistakes.md) | MISTAKE #0 is the important one |
| [docs/research/START_HERE.md](docs/research/START_HERE.md) | Research onboarding, dataset firewall |
| [ai/AGENT_INSTRUCTIONS.md](ai/AGENT_INSTRUCTIONS.md) | Priority hierarchy, permitted/forbidden actions |
| [docs/research/alpha_library/alpha_registry.json](docs/research/alpha_library/alpha_registry.json) | 35-hypothesis backlog (ALPHA-014→048) |
