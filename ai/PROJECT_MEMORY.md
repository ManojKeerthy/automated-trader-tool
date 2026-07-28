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

## What Exists

See [CURRENT_STATE.md](file:///c:/infiligence/automated-trader-tool/ai/CURRENT_STATE.md) for the accurate current state.
