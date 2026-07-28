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

### Open Questions Resolved (2026-07-28)

1. **Trading calendar**: Layered approach — NSE official data validated against `exchange_calendars` library
2. **Market data**: Zerodha Kite Connect historical API (daily OHLCV), stored locally in PostgreSQL
3. **Zerodha integration**: API subscription before M1; live trading not until M11
4. **AI budget**: ₹2,500/month pooled across providers, Claude preferred
5. **Risk parameters**: 0.5% risk/trade (0.75% hard max), 2% portfolio risk, 5 max positions, 10% hard RISK LOCK
6. **CI/CD**: GitHub Actions, multi-OS (Windows + Linux required, macOS best effort)
7. **Corporate actions**: NSE as primary source, provider interface for future alternatives

## What Exists

See CURRENT_STATE.md for the accurate current state.

## What Does NOT Exist

- No trading logic
- No market data ingestion
- No database schema
- No API endpoints
- No dashboard UI
- No broker connections
- No AI integration
- No strategies
- No backtesting engine
