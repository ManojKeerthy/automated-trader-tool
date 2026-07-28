# TradeCraft — Current State

> **IMPORTANT**: This document must accurately describe what ACTUALLY EXISTS, not what is planned.
>
> Last Updated: 2026-07-28
> Current Milestone: M0 ✅ COMPLETE

## What Exists

### Repository Structure ✅
- Python package structure: `src/tradecraft/` with 26 module directories
- Each module contains `__init__.py` stub — **no implementation code**
- Dashboard placeholder: `dashboard/README.md`
- Test structure: `tests/unit/`, `tests/integration/`, `tests/property/`, `tests/fixtures/`

### Configuration ✅
- `.gitignore` — comprehensive exclusions
- `.env.example` — all environment variables documented
- `docker-compose.yml` — PostgreSQL 16 service
- `Makefile` — common development tasks
- `pyproject.toml` — Python project definition with dev dependencies

### Documentation ✅
- 23 policy/design documents in `docs/`
- 7 AI memory documents in `ai/`
- 10 Architecture Decision Records in `docs/adr/`
- 1 Strategy Decision Record in `docs/strategy-decisions/`
- Comprehensive glossary for trading terminology

## What Does NOT Exist

> ⚠️ None of the following have been implemented. They are documented and designed, but no code exists.

- ❌ **No database schema or migrations** — PostgreSQL structure not yet created
- ❌ **No trading logic** — no strategies, signals, or backtesting code
- ❌ **No market data ingestion** — no Zerodha API integration
- ❌ **No data quality checks** — designed but not implemented
- ❌ **No trading calendar** — designed but not implemented
- ❌ **No instrument master** — Nifty 50 constituents not loaded
- ❌ **No corporate actions** — designed but not implemented
- ❌ **No feature engineering** — no indicators calculated
- ❌ **No risk engine** — risk policy documented but not coded
- ❌ **No compliance engine** — compliance policy documented but not coded
- ❌ **No order management** — designed but not implemented
- ❌ **No broker connection** — neither paper nor Zerodha
- ❌ **No portfolio tracking** — no positions, no P&L
- ❌ **No AI integration** — no LLM connections
- ❌ **No dashboard UI** — React app not yet created
- ❌ **No API endpoints** — FastAPI not yet set up
- ❌ **No tests with real assertions** — test directories exist but are empty
- ❌ **No CI/CD pipeline** — GitHub Actions not configured
- ❌ **No database migrations** — Alembic not set up

## External Dependencies Status

| Dependency | Status |
|------------|--------|
| Zerodha Kite Connect API | User has dev account; subscription not yet activated |
| AI providers (Claude/OpenAI/Gemini) | Not connected |
| PostgreSQL | Docker Compose ready, not started |
| NSE data access | Not yet attempted |

## Next Milestone

**M1: Market Data Foundation** — pending user approval to begin.
