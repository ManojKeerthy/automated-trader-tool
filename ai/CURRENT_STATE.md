# TradeCraft — Current State

> **IMPORTANT**: This document must accurately describe what ACTUALLY EXISTS, not what is planned.
>
> Last Updated: 2026-07-29
> Current Milestone: M3A ✅ COMPLETE (Research Data & Screening Foundation Built & Verified)

## What Exists

### Repository & CI/CD Structure ✅
- Python package structure: `src/tradecraft/` with all M1/M2/M3A core components fully implemented.
- GitHub Actions CI workflow in `.github/workflows/ci.yml` verifying linting (Ruff), type safety (Mypy strict), and running pytest on Ubuntu and Windows with PostgreSQL service container.

### M3A Research Data & Screening Foundation ✅
- **Point-in-Time Feature Framework** (`src/tradecraft/features/base.py`): Immutable `FeatureDefinition`, `FeatureValue`, `FeatureSet`, and a versioned registry of 19 technical indicators across 6 families (Trend, Momentum, Volatility, Volume, Breakout, Support/Resistance). Derived features calculated on demand.
- **6 Indicator Families** (`src/tradecraft/features/indicators.py`): Pure, stateless indicator functions with explicit lookback requirements and point-in-time safety semantics. Includes SMA, EMA, MA Slope, Price-to-MA ratio, Trend Structure, RSI, ROC, Multi-period returns, ATR, ATR%, Rolling Volatility, Volatility Expansion, Average Volume, Average Traded Value, RVOL, Volume Expansion, Donchian Channels, Breakout Distance, Consolidation Range, 52W High Distance, and Pivot High/Low with confirmation delay.
- **Support & Resistance Look-Ahead Safety**: Pivot highs/lows require `right_bars` future bars to confirm. Pivots are available ONLY at confirmation date ($T + \text{right\_bars}$), preventing look-ahead bias at peak/trough date $T$.
- **Fundamental & News Interfaces** (`src/tradecraft/research/fundamental_interface.py`, `news_interface.py`): Abstract interfaces enforcing point-in-time availability (`available_from <= query_date`). `NullFundamentalDataProvider` and `NullNewsDataProvider` return unavailable/empty results when no trusted source is configured.
- **Eligibility & Liquidity Screening** (`src/tradecraft/screening/eligibility.py`): Deterministic eligibility pipeline separating operational exclusions (data quality, minimum history, stale data, low liquidity, unresolved corporate actions, unverified identity) from research quality flags (`UNVERIFIED_UNIVERSE`). Configurable `LiquidityScreenConfig` (default provisional ₹5 Crore 20-session average traded value).
- **Market Regime Engine** (`src/tradecraft/screening/regime.py`): Versioned `RegimeDefinition` classifying Trend (BULLISH/BEARISH/SIDEWAYS via MA crossover), Volatility (LOW/NORMAL/HIGH/EXTREME via ATR% percentile ranking), and Market Breadth (STRONG/NEUTRAL/WEAK via % above MA). Breadth quality tracks constituent universe verification (`UNVERIFIED_UNIVERSE`).
- **Strategy-Neutral Screening Engine** (`src/tradecraft/screening/engine.py`): Strategy-neutral orchestrator producing `ScreeningResult` with candidates, regime snapshot, exclusion summary, and full metadata for auditability. Supports zero-candidate output.
- **Alembic Migration 004** (`alembic/versions/004_m3a_screening_schema.py`): Schema migration creating `feature_definitions`, `market_regime_snapshots`, and `screening_runs` tables.
- **CLI & REST API Integration**: CLI subcommands and REST endpoints `/api/regime/current` and `/api/screening/run`.
- **Comprehensive Verification Suite**: 65 passing M3A unit tests (`tests/unit/test_m3a_features.py`, `test_m3a_screening.py`) + 29 M1/M2 tests (94 unit tests total) + PostgreSQL migration upgrade path checks. Clean Ruff and Mypy strict compliance across all 67 source files.

### Configuration & Credentials Management ✅
- `.gitignore` — comprehensive exclusions including local cached sessions.
- `.env` — local development configuration containing postgres details and credentials.
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
- Database versioned migrations using Alembic in `alembic/`:
  - `001_initial_schema`: Initial table definitions.
  - `002_add_transformation_version`: Migration correcting schema drift on the `market_bars` table.
- NSE custom calendar mapping in `src/tradecraft/market_data/nse_calendar.py` and wrapped by `src/tradecraft/market_data/calendar.py` supporting:
  - Special sessions, Muhurat Trading, and 2026 exchange holiday validations.
  - Custom file overrides (`data/nse_holidays_override.json` and `data/nse_special_sessions_override.json`).
  - Authoritative manifest verification (`verify_against_manifest`).

### Data Ingestion & Quality ✅
- Provider abstractions in `src/tradecraft/market_data/provider.py` (Kite Connect adapter + mock data structures).
- Session credentials cacher in `src/tradecraft/market_data/session.py` (saving active access tokens in gitignored local `.kite_session.json` file, with auto-redaction helper `redact_secrets` in logs/exception messages).
- Preflight validator in `src/tradecraft/core/preflight.py` checking database schema version and missing tables/columns before running update loops (failing once with an actionable message).
- Data quality verification in `src/tradecraft/market_data/quality_engine.py` (flagging duplicates, missing sessions, negative values, stale data, and extreme returns > 20% as WARNING suspicion instead of invalidating data).
- Orchestrated workflow in `src/tradecraft/market_data/ingestion.py` executing Nifty 50 constituent mapping and incremental database updates with transactional rollback and post-commit stats.
  - Cutoff Policy: 18:00 IST (6:00 PM local time) checks. Run before 18:00 IST expects the previous trading day's EOD candle.
  - Instrument sync: Automatically deactivates old/demerged symbols (`LTIM` and `TATAMOTORS`) and maps active ones (`LTM` and `TMPV`).
  - Reporting metrics: Separates Processed Successfully, Already Current, Updated With New Data, and Failed.

### M2 Research & Backtesting Foundation ✅
- **Deterministic EOD Backtest Engine** (`src/tradecraft/backtesting/engine.py`): Top-level orchestrator enforcing chronological session iteration, point-in-time data portal access, T+1 execution, and research quality gating (`TRUSTWORTHY`, `RESEARCH_ONLY`, `UNVERIFIED`, `BLOCKED`).
- **Point-in-Time DataPortal** (`src/tradecraft/backtesting/data_portal.py`): Multi-level look-ahead bias protection enforcing date boundary checks on bars, features, universe membership, and benchmark queries. Raises `LookAheadError` on any future data access attempt.
- **Realistic Execution Simulator** (`src/tradecraft/backtesting/execution.py`): T+1 execution model supporting market/limit/stop orders, gap-through-stop fills at Open, whole-share integer enforcement, and conservative OHLC ambiguity resolution (assumes stop-loss hit first when both stop and target fall in same daily bar).
- **Verified July 2026 Cost Model & DP Charges** (`src/tradecraft/backtesting/costs.py`): Effective-dated cost schedules implementing verified July 2026 Zerodha/NSE/SEBI rates (STT 0.1%, NSE charges 0.00345%, SEBI 0.0001%, stamp duty 0.015% buy, GST 18% on brokerage+SEBI+exchange charges, DP charges ₹13+GST per ISIN per day on sell). Flags `COST_MODEL_HISTORICAL_ASSUMPTION` for historical periods.
- **Slippage Models** (`src/tradecraft/backtesting/slippage.py`): `ZeroSlippage` (debug only) and `FixedBasisPointSlippage` (default 5 bps).
- **Performance Metrics Engine** (`src/tradecraft/backtesting/metrics.py`): Calculates CAGR, annualised volatility, Sharpe (√252 annualisation, versioned GoI 91-day T-Bill risk-free rate ~5.35%), Sortino, Calmar, max drawdown & duration, win/loss rates, profit factor, payoff ratio, expectancy, and transaction costs. Handles zero trades, zero volatility, and prevents NaN/Inf output.
- **Versioned Risk-Free Rate Model** (`src/tradecraft/research/risk_free_rate.py`): `RiskFreeRateConfig` recording annual rate, RBI/CCIL provenance, observation date, and `CURRENT_RATE_ASSUMPTION` vs `HISTORICAL_POINT_IN_TIME`.
- **Instrument Identity & Point-in-Time Universe** (`src/tradecraft/instruments/universe.py`): `InstrumentHistory` model tracking symbol changes/mergers and `UniverseMembership` model with `verified_as_of` semantics (no invented effective dates). Queries before verified coverage return `UNVERIFIED`.
- **Strategy Interface & Registry** (`src/tradecraft/strategy/base.py`, `registry.py`): `Strategy` protocol with immutable versioning (ADR-007). `SignalIntent` specifies order intent without dictating fill price.
- **Reference Strategies** (`src/tradecraft/strategy/reference_strategies.py`): `BuyAndHoldStrategy` and `SMACrossoverStrategy` created solely for engine validation, with mandatory disclaimer labels.
- **Auditable Trade Ledger** (`src/tradecraft/backtesting/trade_ledger.py`): `TradeLedger` recording complete trade entry/exit details, fees breakdown, slippage cost, and exit reasons.
- **Explicit Historical Data Backfill** (`src/tradecraft/market_data/backfill.py`): `data backfill` CLI command supporting chunked, rate-limit aware, resumable, and idempotent population of historical daily bars.
- **Alembic Research Migration** (`alembic/versions/003_m2_research_schema.py`): Alembic migration `003_m2_research_schema` creating `instrument_history`, `universe_membership`, `strategy_definitions`, `experiments`, `cost_schedules`, `backtest_runs`, `backtest_trades`, `backtest_metrics`. Applied to local PostgreSQL.
- **CLI & API Research Integration**: CLI commands `data backfill`, `backtest run`, `strategy list` and FastAPI REST endpoints `/api/strategies` and `/api/backtest/run`.
- **Verification Suite**: 30 passing unit and integration tests (`tests/unit/test_m2_backtest_engine.py`) covering verified July 2026 costs, DataPortal look-ahead prevention, 7 execution timing scenarios, OHLC ambiguity resolution, known-answer accounting, and metrics edge cases.

---

## What Does NOT Exist

> ⚠️ None of the following have been implemented. They are documented and designed, but no code exists.

- ❌ **No M3 Strategy Framework** — no strategy promotion pipeline or live strategies (M3 scope)
- ❌ **No M4 Risk Engine** — risk policy documented, basic capital guard in place, full engine in M4
- ❌ **No M4 Compliance Engine** — compliance policy documented, engine in M4
- ❌ **No order execution** — paper or Zerodha live order placement (M4 scope)
- ❌ **No AI integration** — no LLM connections
- ❌ **No derivatives / no short selling / no leverage** — out of current scope

---

## External Dependencies Status

| Dependency | Status |
|------------|--------|
| Zerodha Kite Connect API | User has credentials; session caching & daily authentication workflow verified |
| Zerodha Sandbox | Officially confirmed NOT to exist (we use internal PaperBroker simulator for paper mode) |
| AI providers (Claude/OpenAI/Gemini) | Not connected |
| PostgreSQL | Docker Compose ready, local Docker Desktop active |
| BSE/NSE data access | Mock provider ready; live Zerodha client fully integrated and tested via mocks |

---

## Next Milestone

**M2: Backtesting & Strategy Foundation** — building the core backtesting engine, point-in-time universe filters, strategy executor, and basic performance stats.
