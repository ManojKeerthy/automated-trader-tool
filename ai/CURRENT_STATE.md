# TradeCraft — Current State

> **IMPORTANT**: This document must accurately describe what ACTUALLY EXISTS, not what is planned.
>
> Last Updated: 2026-07-28
> Current Milestone: M1 ✅ COMPLETE (Post-Completion Audit Done)

## What Exists

### Repository & CI/CD Structure ✅
- Python package structure: `src/tradecraft/` with all M1 core components fully implemented.
- GitHub Actions CI workflow in `.github/workflows/ci.yml` verifying linting (Ruff), type safety (Mypy strict), and running pytest on Ubuntu and Windows.

### Configuration & Credentials Management ✅
- `.gitignore` — comprehensive exclusions including local cached sessions.
- `.env` — local development configuration containing postgres details and placeholders.
- `docker-compose.yml` — PostgreSQL 16 service.
- `Makefile` — common development tasks.
- `pyproject.toml` — Python project definition with production dependencies (`fastapi`, `kiteconnect`, `exchange_calendars`, `sqlalchemy`, `alembic`, `pydantic-settings`).

### Core & Reference Data ✅
- Timezone utility helpers in `src/tradecraft/core/time_utils.py` handling `Asia/Kolkata` and UTC conversions.
- SQLAlchemy 2.0 database engine, session management, and Base models in `src/tradecraft/core/db.py`.
- Declarative models in `src/tradecraft/core/db_models.py` mapping:
  - `Instrument`: Lot/tick sizes, nifty50 member tracking, and Zerodha tokens.
  - `MarketBar`: Daily OHLCV data with uniqueness constraints, provenance tracking (`source`, `retrieved_at`, `is_adjusted`, `adjustment_factor`), and `transformation_version`.
  - `CorporateAction`: Splits, dividends, record dates.
- Database versioned migrations using Alembic in `alembic/` (version `001_initial_schema` ready).
- NSE custom calendar mapping in `src/tradecraft/market_data/nse_calendar.py` and wrapped by `src/tradecraft/market_data/calendar.py` supporting:
  - Special sessions, Muhurat Trading, and 2026 exchange holiday validations.
  - Custom file overrides (`data/nse_holidays_override.json` and `data/nse_special_sessions_override.json`).
  - Authoritative manifest verification (`verify_against_manifest`).

### Data Ingestion & Quality ✅
- Provider abstractions in `src/tradecraft/market_data/provider.py` (Kite Connect adapter + mock data structures).
- Session credentials cacher in `src/tradecraft/market_data/session.py` (saving active access tokens in gitignored local `.kite_session.json` file, with auto-redaction helper `redact_secrets` in logs/exception messages).
- Data quality verification in `src/tradecraft/market_data/quality_engine.py` (flagging duplicates, missing sessions, negative values, stale data, and extreme returns > 20% as WARNING suspicion instead of invalidating data).
- Orchestrated workflow in `src/tradecraft/market_data/ingestion.py` executing Nifty 50 constituent mapping and incremental database updates with transactional rollback and post-commit stats.

### CLI & API Interfaces ✅
- Command Line Interface in `src/tradecraft/cli.py` exposing:
  - `python -m tradecraft auth login`: Generates redirect URL.
  - `python -m tradecraft auth token YOUR_TOKEN`: Exchanges callback code.
  - `python -m tradecraft data update`: Runs daily updates (supports `--dry-run`).
- FastAPI server in `src/tradecraft/api.py` exposing read REST endpoints: `/api/instruments`, `/api/universe/nifty50`, `/api/bars`, `/api/data-quality`, `/api/corporate-actions`.
- Glassmorphic monitoring dashboard in `src/tradecraft/dashboard/index.html` loading data status, freshness, and quality alerts.

### Verification Suite ✅
- pytest suite containing unit tests for calendar schedules, timezone math, data quality rules, and integration database ingestion checks (`19 passed, 4 skipped`).
- PostgreSQL integration tests in `tests/integration/test_db_postgres.py` checking unique constraints, database rollbacks, decimal scaling, and timezone retention (configured to skip if live database is unreachable).
- Deterministic M1 E2E acceptance test in `tests/integration/test_e2e_m1.py` verifying full ingestion logic, quality engine error tracking, and idempotency.

### Documentation ✅
- 24 policy/design documents in `docs/` (including newly created `docs/KNOWN_LIMITATIONS.md`).
- 7 AI memory documents in `ai/`.

---

## What Does NOT Exist

> ⚠️ None of the following have been implemented. They are documented and designed, but no code exists.

- ❌ **No trading logic** — no strategies, signals, or backtesting code (M2 scope)
- ❌ **No feature engineering** — no indicators calculated (M2 scope)
- ❌ **No point-in-time Nifty 50 constituents** — `POINT-IN-TIME NIFTY 50 MEMBERSHIP NOT YET VERIFIED` (M2 scope)
- ❌ **No risk engine** — risk policy documented but not coded (M3 scope)
- ❌ **No compliance engine** — compliance policy documented but not coded (M3 scope)
- ❌ **No order execution** — paper or Zerodha order placement (M4 scope)
- ❌ **No portfolio tracking** — no positions, no P&L
- ❌ **No AI integration** — no LLM connections
- ❌ **No dashboard UI** — React app not yet created (uses static html for status monitoring currently)

---

## External Dependencies Status

| Dependency | Status |
|------------|--------|
| Zerodha Kite Connect API | User has credentials; session caching & daily authentication workflow verified |
| Zerodha Sandbox | Officially confirmed NOT to exist (we use internal PaperBroker simulator for paper mode) |
| AI providers (Claude/OpenAI/Gemini) | Not connected |
| PostgreSQL | Docker Compose ready, local Docker Desktop not active |
| BSE/NSE data access | Mock provider ready; live Zerodha client fully integrated and tested via mocks |

---

## Next Milestone

**M2: Backtesting & Strategy Foundation** — building the core backtesting engine, point-in-time universe filters, strategy executor, and basic performance stats.
