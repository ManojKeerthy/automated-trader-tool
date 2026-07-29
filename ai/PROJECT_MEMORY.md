# TradeCraft — Project Memory

> Last Updated: 2026-07-28

## Project Summary

TradeCraft is a personal algorithmic swing trading platform for the Indian market (NSE, Nifty 50). Built for capital preservation first, risk-adjusted returns second.

## Key Decisions Made

### M0 (2026-07-28)

1. **Architecture**: Modular monolith (ADR-001)
2. **Tech stack**: Python + React + PostgreSQL + Docker (ADR-002)
3. **Paper/live separation**: BrokerInterface with PaperBroker/ZerodhaBroker adapters (ADR-003)
4. **AI boundaries**: AI advisory only; risk/compliance/execution are deterministic (ADR-004)
5. **Timezone**: UTC storage, explicit Asia/Kolkata for market logic (ADR-005)
6. **Cross-platform**: Build once, configure per environment, run anywhere (ADR-006)
7. **Strategy versioning**: Immutable versions, full lifecycle (ADR-007)
8. **Human approval**: All trades require approval; protective stops are autonomous (ADR-008)
9. **Emergency controls**: RISK LOCK at 10% drawdown, KILL SWITCH for emergencies (ADR-009)
10. **AI providers**: Abstraction layer, pooled ₹2,500/month budget (ADR-010)

### M1 (2026-07-28)

1. **Exchange Calendar Selection**: Used the BSE (`XBOM`) calendar in `exchange_calendars` since `XNSE` was not registered in the installed package. They share identical national holidays and trading sessions.
2. **Zerodha Session Caching**: Implemented a local daily cache file `.kite_session.json` in the user's data directory. Avoids repetitive redirects, and automatically expires daily at 6:00 AM.
3. **Type-Safety Configurations**: Integrated type stubs overrides in `pyproject.toml` to satisfy mypy strict requirements for external untyped packages (pandas, exchange_calendars, and kiteconnect).

### M1 Post-Completion Audit (2026-07-28)

1. **NSE Calendar Overrides**: Decoupled the BSE (`XBOM`) calendar from regulatory truth by implementing a custom `NSETradingCalendar` (`nse_calendar.py`) that overlay data directory overrides (`nse_holidays_override.json` and `nse_special_sessions_override.json`) and run-time validation assertions.
2. **PostgreSQL Integration Tests**: Implemented specific PostgreSQL integration checks (`test_db_postgres.py`) testing transactions, constraint rollbacks, and numeric precision scaling (with auto-skipping if database is offline).
3. **Audit Log Secret Redaction**: Added auto-redaction of `KITE_API_SECRET` strings in exception handling and logging blocks within `session.py` to prevent credentials leakage.
4. **Ingestion Counter Accuracy**: Fixed the incremental reporting counters in `ingestion.py` to only record inserted bars and corporate actions after a successful database `commit()`.
5. **Point-in-Time Nifty 50 Warning**: Added a prominent warning regarding Nifty 50 survivorship bias, flagging that point-in-time constituent membership is not yet verified.

### M1 Schema Parity Audit (2026-07-28)

1. **Transformation Version Drift Fix**: Resolved the schema drift by adding the forward Alembic migration `002_add_transformation_version.py` which creates the missing column `transformation_version` on the `market_bars` table.
2. **Alembic Testing in Integration Suite**: Refactored `db_schema` test fixture in `test_db_postgres.py` to run migrations dynamically using Alembic Config and Command APIs. Added a command dropping the `alembic_version` table on test setup/teardown to ensure database tests run migrations cleanly.
3. **Preflight Validation**: Added a preflight schema verification check in `preflight.py` checking required tables and columns before starting data loops, aborting cleanly with `DATABASE MIGRATION REQUIRED` warning instead of generating 50 duplicate stack traces.
4. **CLI Wording Rename**: Renamed the CLI market data modes from `LIVE` to `REAL_DATA` to prevent confusion with money-order execution.

### M2 — Backtesting & Strategy Research Foundation (2026-07-28)

1. **Deterministic EOD Backtest Engine**: Built engine using `HistoricalClock`, `DataPortal`, `ExecutionSimulator`, `Portfolio`, and `MetricsEngine`.
2. **Multi-Level Look-Ahead Protection**: `DataPortal` enforces date boundary checks on bars, features, universe membership, and benchmark queries, raising `LookAheadError` on any attempt to query T+1.
3. **Execution Semantics & OHLC Ambiguity**: Fills at T+1 Open. Gap-through-stop fills at Open. When both stop-loss and profit-target fall inside the same daily bar's H-L range, the simulator deterministically assumes the adverse outcome (stop-loss hit first).
4. **Verified July 2026 Costs & DP Charges**: Implemented effective-dated `CostSchedule` with verified rates: STT 0.1%, NSE charges 0.00345%, SEBI 0.0001%, stamp duty 0.015% buy, GST 18% on (brokerage + SEBI + exchange charges), and DP charges ₹13 + 18% GST = ₹15.34 per ISIN per day on sell.
5. **Versioned Risk-Free Rate**: Sourced from Reserve Bank of India / CCIL 91-day Treasury Bill yield (~5.35% per annum), recorded in `RiskFreeRateConfig` with provenance.
6. **Point-in-Time Universe & Research Quality Gating**: Added `UniverseMembership` with `verified_as_of` semantics. Backtests classify research quality into `TRUSTWORTHY`, `RESEARCH_ONLY`, `UNVERIFIED`, and `BLOCKED`. Unverified universe membership gates backtest promotion.
7. **SignalIntent Boundary**: Strategies declare order intents without dictating fill prices. `ExecutionSimulator` determines theoretical and actual fill prices.
8. **Explicit Data Backfill**: Separated incremental EOD `data update` from historical population `data backfill` (resumable, chunked, rate-limit aware, idempotent).
9. **Schema Parity Migration**: Applied Alembic migration `003_m2_research_schema` creating `instrument_history`, `universe_membership`, `strategy_definitions`, `experiments`, `cost_schedules`, `backtest_runs`, `backtest_trades`, `backtest_metrics`. Verified dialect portability across PostgreSQL and SQLite.

### M3A — Research Data & Screening Foundation (2026-07-29)

1. **PIT Feature Framework**: Built versioned `FeatureDefinition` registry with 19 indicators across 6 families. Calculation on demand ensures no stale state.
2. **Pivot Look-Ahead Defenses**: Support/resistance pivot highs/lows require `right_bars` future bars to confirm, placing availability strictly at confirmation date ($T + \text{right\_bars}$) rather than peak date $T$.
3. **Provisional Configurable Liquidity Screening**: Default ₹5 Crore 20-session average daily traded value threshold configured in `LiquidityScreenConfig` with recorded version and parameters.
4. **Operational Eligibility vs Research Quality Separation**: Securities excluded by data quality/liquidity cannot be screened; securities passing operational checks but with unverified PIT universe membership carry research quality flags without blocking research-only runs.
5. **Versioned Market Regime Engine**: `RegimeDefinition` specifies deterministic MA crossover trend, ATR% percentile volatility ranking, and % above MA breadth logic. Breadth tracks universe verification (`UNVERIFIED_UNIVERSE`).
6. **Strategy-Neutral Screening**: `ScreeningEngine` orchestrates eligibility, features, and regime classification without strategy-specific rules. Zero candidates output is valid and non-error.
7. **Fundamental & News Abstract Interfaces**: Abstract classes (`AbstractFundamentalDataProvider`, `AbstractNewsDataProvider`) with point-in-time constraints (`available_from <= query_date`). Default null providers return empty/unavailable.
8. **Alembic Migration 004**: Applied migration `004_m3a_screening_schema.py` creating `feature_definitions`, `market_regime_snapshots`, and `screening_runs`.

## What Exists

See [CURRENT_STATE.md](file:///c:/infiligence/automated-trader-tool/ai/CURRENT_STATE.md) for the accurate current state.
