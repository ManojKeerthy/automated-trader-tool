# TradeCraft — Roadmap

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## Milestone Overview

| Milestone | Name | Dependencies | Status |
|-----------|------|-------------|--------|
| **M0** | Requirements & Architecture | — | ✅ COMPLETE |
| **M1** | Market Data Foundation | M0 | 🔲 NOT STARTED |
| **M2** | Research & Backtesting | M1 | 🔲 NOT STARTED |
| **M3** | Strategy Framework | M2 | 🔲 NOT STARTED |
| **M4** | Risk Engine | M3 | 🔲 NOT STARTED |
| **M5** | Portfolio Engine | M4 | 🔲 NOT STARTED |
| **M6** | Compliance System | M5 | 🔲 NOT STARTED |
| **M7** | Paper Broker | M6 | 🔲 NOT STARTED |
| **M8** | Dashboard | M7 | 🔲 NOT STARTED |
| **M9** | AI Research System | M8 | 🔲 NOT STARTED |
| **M10** | Shadow Trading | M9 | 🔲 NOT STARTED |
| **M11** | Zerodha Live Integration | M10 | 🔲 NOT STARTED |
| **M12** | Production Hardening | M11 | 🔲 NOT STARTED |
| **M13** | Cloud Migration | M12 | 🔲 NOT STARTED |

---

## M0 — Requirements & Architecture ✅

### Scope
- Constitution analysis and decision resolution
- Repository structure establishment
- Authoritative documentation system (25+ policy documents)
- Domain architecture and module boundaries
- Data model design
- Security boundaries definition
- Paper/live separation design
- Deterministic vs AI boundary definition
- Architecture Decision Records (10 ADRs)
- Milestone roadmap with acceptance criteria

### Acceptance Criteria
- [x] Repository structure created with all module directories
- [x] All policy documents written with substantive content
- [x] Domain model defined with entities, relationships, enumerations
- [x] Architecture diagram with module dependency rules
- [x] All 7 open questions resolved and documented
- [x] Risk parameters defined and documented
- [x] ADRs created for all major architectural decisions
- [x] CURRENT_STATE.md accurately reflects M0 reality
- [x] No trading logic implemented
- [x] No live connections to any external service

---

## M1 — Market Data Foundation

### Scope
- Trading calendar implementation (`TradingCalendar` abstraction)
- Calendar validation against NSE official data
- Instrument master for Nifty 50 (current constituents)
- `MarketDataProvider` interface
- `ZerodhaMarketDataProvider` for daily OHLCV
- PostgreSQL schema and migrations for market data
- Data quality validation pipeline
- `CorporateActionsProvider` interface
- `NSECorporateActionsProvider` (initial)
- Raw vs adjusted price series management
- `TestMarketDataProvider` with fixtures

### Acceptance Criteria
- [ ] Trading calendar correctly identifies NSE trading days, holidays, and special sessions
- [ ] Calendar validated against at least 2 years of official NSE holiday lists
- [ ] Nifty 50 current constituents loaded with metadata (symbol, ISIN, sector)
- [ ] Daily OHLCV downloaded from Zerodha and stored in PostgreSQL
- [ ] Data quality checks detect missing sessions, impossible values, gaps
- [ ] Corporate actions (splits, bonuses) fetched from NSE
- [ ] Raw and adjusted price series stored separately
- [ ] All data has documented provenance
- [ ] TestMarketDataProvider works with fixture data
- [ ] Database migrations are version-controlled and reproducible
- [ ] Tests: unit + integration for all components
- [ ] Documentation updated: DATA_POLICY.md, CURRENT_STATE.md

### Prerequisites
- User activates Zerodha Kite Connect API subscription
- Zerodha API credentials configured in `.env`

---

## M2 — Research & Backtesting

### Scope
- Feature engineering framework
- Core technical indicators (MA, RSI, MACD, ATR, ADX, Bollinger, etc.)
- Backtest engine with bias defenses
- Transaction cost model (Indian equities)
- Validation metrics calculation (Sharpe, Sortino, drawdown, etc.)
- Walk-forward validation framework
- Out-of-sample testing support
- Parameter sensitivity analysis
- Backtest reproducibility (data snapshot, calendar, strategy version)

### Acceptance Criteria
- [ ] Feature engine computes indicators correctly (verified against known values)
- [ ] Backtest engine simulates trades with realistic fills and costs
- [ ] Look-ahead bias protection verified
- [ ] Survivorship bias protection via point-in-time universe
- [ ] Transaction costs modelled per BACKTESTING_POLICY.md
- [ ] All validation metrics from BACKTESTING_POLICY.md calculable
- [ ] Walk-forward validation produces stable results
- [ ] Backtests are reproducible from persisted state
- [ ] Tests: unit tests for indicators, integration tests for backtest engine
- [ ] Documentation updated

---

## M3 — Strategy Framework

### Scope
- Strategy definition interface
- Strategy registry with immutable versioning
- Strategy lifecycle management
- Signal generation framework
- Entry/exit rule specification
- At least one initial systematic strategy (researched and validated)
- Screening engine (universe filtering)
- Strategy documentation template

### Acceptance Criteria
- [ ] Strategy interface defined and implementable
- [ ] Registry tracks strategy versions immutably
- [ ] Lifecycle transitions enforced (cannot skip stages)
- [ ] At least one strategy backtested with positive expectancy after costs
- [ ] Screening engine filters universe based on strategy requirements
- [ ] Strategy versioning produces unique, reproducible identifiers
- [ ] Tests: strategy lifecycle, registry, screening
- [ ] Strategy decision record created for initial strategy

---

## M4 — Risk Engine

### Scope
- Per-trade risk calculation
- Portfolio risk aggregation
- Position sizing (volatility-adjusted)
- All risk limits from RISK_POLICY.md implemented
- Daily/weekly loss guards
- Drawdown monitoring and state management
- RISK LOCK implementation
- KILL SWITCH implementation
- Prohibited behaviour prevention (martingale, revenge trading, etc.)
- Risk validation gate in order pipeline

### Acceptance Criteria
- [ ] Risk per trade correctly calculated and enforced
- [ ] Position sizing respects all limits simultaneously
- [ ] Daily and weekly loss guards activate correctly
- [ ] Drawdown levels trigger correct state transitions
- [ ] RISK LOCK blocks all new positions
- [ ] KILL SWITCH cancels pending orders
- [ ] Prohibited behaviours are prevented in code
- [ ] Risk engine is fully deterministic (no AI dependency)
- [ ] Tests: invariant tests for all risk rules
- [ ] Documentation updated

---

## M5 — Portfolio Engine

### Scope
- Portfolio state management
- Position tracking (open, partially closed, closed)
- Cash management
- Realised and unrealised P&L calculation
- Portfolio value tracking and peak tracking
- Sector exposure tracking
- Correlation analysis (basic)
- Portfolio snapshots for audit

### Acceptance Criteria
- [ ] Portfolio accurately tracks cash, invested capital, total value
- [ ] P&L calculations correct for buys, sells, partial exits
- [ ] Drawdown calculated from peak value
- [ ] Sector exposure tracked and queryable
- [ ] Portfolio snapshots persisted for audit
- [ ] Tests: P&L calculation edge cases, portfolio state transitions

---

## M6 — Compliance System

### Scope
- Compliance engine (deterministic)
- Instrument trading restriction checks
- Market hours validation
- Regulatory knowledge base (initial population)
- Fail-closed implementation
- Compliance validation gate in order pipeline
- Compliance status reporting

### Acceptance Criteria
- [ ] Compliance engine validates every trade proposal
- [ ] Uncertain compliance status blocks trade (fail-closed)
- [ ] Market hours respected
- [ ] Instrument restrictions checked
- [ ] Regulatory knowledge base has initial entries from REGULATORY_SOURCES.md
- [ ] Compliance engine is fully deterministic
- [ ] Tests: compliance rules, fail-closed behaviour
- [ ] SEBI algo trading classification researched and documented

---

## M7 — Paper Broker

### Scope
- `BrokerInterface` implementation
- `PaperBroker` adapter
- Order lifecycle (create → validate → submit → fill)
- Simulated fills with slippage
- Human approval workflow (command-line initially)
- Protective stop simulation
- Position reconciliation
- Pending entry invalidation

### Acceptance Criteria
- [ ] PaperBroker implements full BrokerInterface
- [ ] Orders go through risk → compliance → approval pipeline
- [ ] Fills simulated with configurable slippage
- [ ] Stops execute in simulation
- [ ] Paper mode cannot submit live orders (invariant test)
- [ ] Approval workflow functional (even if CLI-based before dashboard)
- [ ] Pending entries invalidated when setup becomes invalid
- [ ] Tests: broker contract tests, order lifecycle, safety invariants

---

## M8 — Dashboard

### Scope
- React + TypeScript project setup (Vite)
- FastAPI backend API layer
- Portfolio overview page
- Trade proposal review page (APPROVE/REJECT)
- Open positions page
- System status page
- Risk state visualisation
- Paper/Live mode indicator
- KILL SWITCH button
- Terminology tooltips (ⓘ icons)

### Acceptance Criteria
- [ ] Dashboard shows portfolio value, cash, P&L, drawdown
- [ ] Trade proposals displayed with full context
- [ ] APPROVE/REJECT workflow functional
- [ ] Risk state (NORMAL/ELEVATED/RISK_LOCK) visible
- [ ] KILL SWITCH accessible
- [ ] Paper/Live mode prominently displayed
- [ ] Terminology tooltips for all financial terms
- [ ] Works on Chrome, Edge, Safari, Firefox
- [ ] OS-independent (no Windows-specific behaviour)

---

## M9 — AI Research System

### Scope
- AI provider abstraction (Claude, OpenAI, Gemini)
- Cost tracking per call
- Budget enforcement (₹2,500/month)
- AI-assisted strategy research
- AI-assisted failure analysis
- AI-assisted feature hypothesis
- Response validation
- Graceful degradation when AI unavailable

### Acceptance Criteria
- [ ] AI provider interface supports Claude, OpenAI, Gemini
- [ ] Cost tracked per call with monthly aggregation
- [ ] Budget enforcement pauses AI research at limit
- [ ] AI can propose strategies (go through full lifecycle)
- [ ] Platform safe when AI unavailable
- [ ] AI cannot bypass risk/compliance controls
- [ ] Tests: budget enforcement, graceful degradation

---

## M10 — Shadow Trading

### Scope
- Run paper trades in parallel with real market
- Compare paper results with actual market outcomes
- Strategy performance monitoring
- Degradation detection
- Shadow trading dashboard view
- Evidence collection for live trading decision

### Acceptance Criteria
- [ ] Paper trades executed daily based on strategy signals
- [ ] Results compared to actual market prices
- [ ] Performance metrics tracked over time
- [ ] Strategy degradation detected and flagged
- [ ] Sufficient shadow trading evidence before M11

---

## M11 — Zerodha Live Integration

### Scope
- `ZerodhaBroker` adapter implementing `BrokerInterface`
- Kite Connect authentication flow
- Live order placement, modification, cancellation
- Real-time order status tracking
- Session management and re-authentication
- Rate limiting
- Error handling (partial fills, rejections, network failures)
- Idempotency
- Position reconciliation with broker
- Limited live capital deployment

### Acceptance Criteria
- [ ] ZerodhaBroker implements full BrokerInterface
- [ ] Authentication follows Kite Connect documented flow
- [ ] Orders placed, modified, cancelled correctly
- [ ] Partial fills handled
- [ ] Rejections handled gracefully
- [ ] Rate limits respected
- [ ] Idempotency prevents duplicate orders
- [ ] Reconciliation detects discrepancies
- [ ] Live mode requires explicit configuration + human confirmation
- [ ] Tests: contract tests (paper and live satisfy same interface)

### Prerequisites
- Active Kite Connect API subscription
- Sufficient shadow trading evidence
- Explicit human approval for live trading

---

## M12 — Production Hardening

### Scope
- Comprehensive error handling review
- Recovery procedures
- Backup strategy
- Performance optimisation
- Security audit
- Full CI/CD pipeline
- Multi-OS CI validation
- Documentation review and update
- Edge case handling
- Operational runbook

### Acceptance Criteria
- [ ] All error paths handled gracefully
- [ ] Recovery procedures documented and tested
- [ ] Database backup strategy implemented
- [ ] CI passes on Windows + Linux + macOS
- [ ] Security review completed
- [ ] All documentation current
- [ ] Operational runbook available

---

## M13 — Cloud Migration

### Scope
- Cloud VM provisioning
- Managed PostgreSQL setup
- Container deployment pipeline
- Monitoring and alerting
- 24×7 operation support
- Backup automation
- Network security

### Acceptance Criteria
- [ ] System runs on cloud Linux VM
- [ ] Same Docker images as local development
- [ ] Database migrated to managed PostgreSQL
- [ ] Monitoring and alerting operational
- [ ] Automated backups
- [ ] Secure network configuration
- [ ] 24×7 operation validated

### Prerequisites
- M12 completed
- Cloud provider selected
- Budget approved
