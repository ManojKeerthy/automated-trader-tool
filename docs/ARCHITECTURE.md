# TradeCraft — System Architecture

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Architecture Style

**Modular Monolith** (see [ADR-001](adr/ADR-001-modular-monolith.md)).

A single deployable Python application with strong module boundaries. Components communicate through well-defined Python interfaces, not network calls. Modules may later be extracted into services if complexity justifies it.

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WEB DASHBOARD                               │
│                    (React + TypeScript)                              │
│          Trade Approval · Portfolio View · Risk Monitor             │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST API
┌────────────────────────────┴────────────────────────────────────────┐
│                        API LAYER (FastAPI)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  PORTFOLIO    │  │  ORDER       │  │  HUMAN APPROVAL          │  │
│  │  ENGINE       │  │  MANAGEMENT  │  │  WORKFLOW                │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘  │
│         │                 │                      │                  │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────────┴───────────────┐  │
│  │  RISK        │  │  BROKER      │  │  COMPLIANCE              │  │
│  │  ENGINE      │  │  ABSTRACTION │  │  ENGINE                  │  │
│  │  ┌────────┐  │  │  ┌────────┐  │  │                          │  │
│  │  │RISK    │  │  │  │Paper   │  │  │  SEBI/NSE rules          │  │
│  │  │LOCK    │  │  │  │Broker  │  │  │  Fail-closed             │  │
│  │  │KILL SW │  │  │  ├────────┤  │  │                          │  │
│  │  └────────┘  │  │  │Zerodha │  │  │                          │  │
│  └──────────────┘  │  │Adapter │  │  └──────────────────────────┘  │
│                    │  └────────┘  │                                 │
│                    └──────────────┘                                 │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  STRATEGY    │  │  SCREENING   │  │  MARKET REGIME           │  │
│  │  ENGINE      │  │  ENGINE      │  │  DETECTOR                │  │
│  │  ┌────────┐  │  │              │  │                          │  │
│  │  │Registry│  │  │              │  │                          │  │
│  │  │Version │  │  │              │  │                          │  │
│  │  └────────┘  │  │              │  │                          │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────────┘  │
│         │                 │                                        │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────────────────────────┐  │
│  │  FEATURE     │  │  RESEARCH &  │  │  AI ORCHESTRATION        │  │
│  │  ENGINE      │  │  BACKTESTING │  │  ┌────────┐              │  │
│  │              │  │              │  │  │Claude  │              │  │
│  │              │  │              │  │  │OpenAI  │              │  │
│  │              │  │              │  │  │Gemini  │              │  │
│  │              │  │              │  │  └────────┘              │  │
│  └──────┬───────┘  └──────────────┘  └──────────────────────────┘  │
│         │                                                          │
│  ┌──────┴─────────────────────────────────────────────────────┐    │
│  │                    DATA LAYER                               │    │
│  │  Instrument Master · Market Data · Corporate Actions        │    │
│  │  Fundamentals · News/Events · Trading Calendar              │    │
│  └─────────────────────────┬───────────────────────────────────┘    │
│                            │                                       │
│  ┌─────────────────────────┴───────────────────────────────────┐   │
│  │              CROSS-CUTTING CONCERNS                          │   │
│  │  Audit · Observability · Configuration · Security            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                        PostgreSQL                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## 3. Module Dependency Rules

### Layer Hierarchy (top depends on bottom, never reverse)

1. **Dashboard** → API Layer
2. **API Layer** → Domain Modules
3. **Domain Modules** → Core / Data Layer
4. **Core** → Standard library / external packages only

### Critical Dependency Constraints

| Rule | Rationale |
|------|-----------|
| Risk Engine MUST NOT depend on AI | Deterministic risk control |
| Compliance Engine MUST NOT depend on AI | Deterministic compliance |
| Order Management MUST NOT depend on AI | Deterministic execution |
| Broker adapters MUST implement BrokerInterface | Paper/live separation |
| Strategy Engine MUST NOT directly call broker | Orders go through Order Management |
| AI module MAY be called by Research, Screening, Strategy formulation | Advisory role only |
| No module may import from `broker.paper` or `broker.zerodha` directly | Always through abstraction |

### Module Boundary Enforcement

Each module in `src/tradecraft/` exposes its public API through its `__init__.py`. Internal implementation details are private. Cross-module access should use defined interfaces.

## 4. Module Catalogue

### Core (`core/`)
Shared domain primitives used across all modules.
- Enums: `TradeSide`, `OrderType`, `OrderStatus`, `TradeStatus`, `RiskLevel`, `MarketRegime`
- Value objects: `Money`, `Quantity`, `Price`, `Percentage`
- Types: `InstrumentId`, `StrategyId`, `OrderId`, `TradeId`
- Exceptions: Domain-specific exception hierarchy
- Time utilities: Timezone-aware helpers for `Asia/Kolkata`

### Instrument Master (`instruments/`)
- Nifty 50 constituent management (point-in-time)
- Instrument metadata: symbol, ISIN, exchange, sector, industry
- Universe filtering interface
- Historical constituent tracking for survivorship-bias-free backtesting

### Market Data (`market_data/`)
- `MarketDataProvider` interface
  - `ZerodhaMarketDataProvider` — Kite Connect historical candle API
  - `TestMarketDataProvider` — Fixture-based testing
  - Future: `PaidDataProvider`
- Daily OHLCV storage in PostgreSQL
- Data quality validation (missing sessions, duplicates, impossible values, gaps)
- Corporate-action-adjusted series derivation
- Data freshness tracking

### Corporate Actions (`corporate_actions/`)
- `CorporateActionsProvider` interface
  - `NSECorporateActionsProvider`
  - `TestCorporateActionsProvider`
- Modelled events: splits, bonuses, dividends, rights, mergers, symbol changes, delistings
- Raw vs adjusted price series management
- Reproducible adjustment audit trail

### Fundamentals (`fundamentals/`)
- Financial statements, ratios, valuation metrics
- Quality, profitability, growth, leverage signals
- Data sourced from official/reliable providers

### News/Events (`news/`)
- News ingestion with source provenance
- Event calendar (earnings, corporate actions, macro events)
- News signals require research validation like any other signal
- No automatic trade triggering from LLM sentiment

### Feature Engineering (`features/`)
- Technical indicators (MA, RSI, MACD, ATR, ADX, Bollinger, Donchian, etc.)
- Relative strength, sector strength, market breadth
- Fundamental-derived features
- All features are CANDIDATES — must justify themselves empirically

### Screening (`screening/`)
- Universe filtering based on strategy requirements
- Liquidity filters, volatility filters
- Sector/industry grouping
- Candidate selection pipeline

### Strategy Engine (`strategy/`)
- Strategy definition interface
- Strategy registry with immutable versioning
- Lifecycle management: IDEA → RESEARCH → ... → PRODUCTION
- Signal generation
- Entry/exit rule specification
- Both systematic strategies and AI-discovered strategies

### Research (`research/`)
- Hypothesis formulation and testing
- AI-assisted strategy discovery
- Statistical analysis tools

### Backtesting (`backtesting/`)
- Backtest engine with bias defenses
- Walk-forward validation
- Out-of-sample testing
- Cost/slippage modelling
- Comprehensive metrics calculation
- Reproducible results (persisted calendar, data snapshot, strategy version)

### Market Regime (`regime/`)
- Regime detection (bullish, bearish, sideways, high/low volatility)
- Regime-dependent strategy/risk adjustment (when validated)
- Categories are not assumed optimal — subject to research

### Portfolio Engine (`portfolio/`)
- Portfolio state tracking
- Position management
- Cash management
- Allocation tracking
- P&L calculation (realised/unrealised)

### Risk Engine (`risk/`)
- **DETERMINISTIC** — no AI dependency
- Per-trade risk calculation
- Portfolio risk aggregation
- Position sizing (volatility-adjusted)
- Limit enforcement:
  - Risk per trade: target 0.5%, hard max 0.75%
  - Max total open portfolio risk: 2.0%
  - Max single-stock allocation: 20%
  - Max sector exposure: 40%
  - Max simultaneous positions: 5
  - Daily loss guard: 1.5%
  - Weekly loss guard: 3%
- Drawdown controls: 5% warning, 8% reduction, 10% HARD RISK LOCK
- RISK LOCK implementation
- KILL SWITCH implementation
- Prohibited behaviours: martingale, revenge trading, uncapped leverage

### Compliance Engine (`compliance/`)
- **DETERMINISTIC** — no AI dependency
- SEBI regulatory rules
- NSE exchange rules
- Instrument trading restrictions
- Fail-closed on uncertainty
- Versioned regulatory knowledge base
- Compliance status reporting

### Order Management (`orders/`)
- Order lifecycle: created → validated → submitted → filled/rejected
- Risk validation gate
- Compliance validation gate
- Human approval gate
- Order idempotency
- Pending entry invalidation

### Broker Abstraction (`broker/`)
```python
class BrokerInterface(Protocol):
    """Abstract broker operations. All execution goes through this."""
    async def place_order(self, order: Order) -> OrderResult: ...
    async def modify_order(self, order_id: OrderId, ...) -> OrderResult: ...
    async def cancel_order(self, order_id: OrderId) -> OrderResult: ...
    async def get_order_status(self, order_id: OrderId) -> OrderStatus: ...
    async def get_positions(self) -> list[Position]: ...
    async def get_holdings(self) -> list[Holding]: ...
```

- **Paper Broker** (`broker/paper/`): Simulated execution, default mode
- **Zerodha Adapter** (`broker/zerodha/`): Kite Connect integration, M11+

### Positions (`positions/`)
- Position tracking
- Reconciliation with broker state
- Position history

### P&L (`pnl/`)
- Realised P&L calculation
- Unrealised P&L (mark-to-market)
- Transaction cost tracking
- Tax-relevant reporting (future)

### AI Orchestration (`ai/`)
- `AIProvider` interface (Claude, OpenAI, Gemini)
- Cost tracking per call
- Budget enforcement
- Response validation
- Graceful degradation when unavailable
- Never in deterministic execution path

### Audit (`audit/`)
- Durable decision records
- Trade rationale logging
- Strategy version tracking
- Data snapshot references
- Approval records

### Observability (`observability/`)
- Structured logging
- Health checks
- Metrics collection
- AI cost reporting
- Data freshness monitoring

### Configuration (`config/`)
- Environment-based configuration
- Mode management (PAPER/LIVE)
- Feature flags
- Per-environment settings

### Security (`security/`)
- Secret management (environment variables)
- API credential handling
- Redaction in logs
- Least privilege enforcement

## 5. Data Flow: Trade Lifecycle

```
Market Data → Feature Engine → Strategy Engine → Screening
                                      │
                                      ▼
                              Signal Generated
                                      │
                                      ▼
                            Risk Engine Validates
                          (position size, limits, drawdown)
                                      │
                              ┌───────┴────────┐
                              │ RISK REJECTED   │──→ Logged, no trade
                              └────────────────┘
                                      │ PASSED
                                      ▼
                           Compliance Engine Validates
                          (regulatory, instrument checks)
                                      │
                              ┌───────┴────────┐
                              │ COMPLIANCE FAIL │──→ Logged, no trade
                              └────────────────┘
                                      │ PASSED
                                      ▼
                            Trade Proposal Created
                          (full context for human review)
                                      │
                                      ▼
                              Dashboard → Human
                                      │
                              ┌───────┴────────┐
                              │ REJECTED        │──→ Logged
                              └────────────────┘
                                      │ APPROVED
                                      ▼
                            Order Management
                                      │
                                      ▼
                          Broker Interface (Paper/Live)
                                      │
                                      ▼
                            Position Tracking
                                      │
                                      ▼
                         P&L + Reconciliation + Audit
```

## 6. Cross-Platform Architecture

See [ADR-006](adr/ADR-006-cross-platform-portability.md).

### Principles
- **Build once, configure per environment, run anywhere**
- All paths via `pathlib` (Python) / `path` module (Node.js)
- UTC storage, explicit `Asia/Kolkata` for market logic
- No OS-specific code in core modules
- Docker for infrastructure services
- Environment-based configuration

### Environment Matrix

| Environment | OS | Database | Broker | Mode |
|-------------|-----|----------|--------|------|
| Local Dev (Windows) | Windows 10/11 | Docker PostgreSQL | Paper | PAPER |
| Local Dev (macOS) | macOS | Docker PostgreSQL | Paper | PAPER |
| Local Dev (Linux) | Linux | Docker PostgreSQL | Paper | PAPER |
| Cloud Dev | Linux | Docker PostgreSQL | Paper | PAPER |
| Cloud Paper | Linux | Managed PostgreSQL | Paper | PAPER |
| Cloud Production | Linux | Managed PostgreSQL | Zerodha | LIVE |

## 7. Security Boundaries

See [SECURITY.md](SECURITY.md).

- Secrets: Environment variables only, never in source
- Broker credentials: Isolated in Zerodha adapter, never logged
- AI API keys: Per-provider, budget-tracked
- Audit logs: Append-only, tamper-evident where practical
- Mode switching: Explicit configuration, no silent fallback

## 8. Deterministic vs AI Boundaries

See [ADR-004](adr/ADR-004-deterministic-vs-ai-boundaries.md).

### DETERMINISTIC (No AI dependency)
- Risk calculations and limits
- Compliance rules
- Order execution
- Position sizing
- RISK LOCK / KILL SWITCH
- P&L calculations
- Data quality checks

### AI-ASSISTED (Advisory, validated, human-approved)
- Strategy research and discovery
- Feature hypothesis generation
- News analysis
- Market commentary
- Backtest analysis
- Failure diagnosis

## 9. Database Design Principles

- PostgreSQL as single source of truth
- All schema changes via version-controlled migrations
- UTC timestamps with timezone awareness
- Separate raw and derived data tables
- Audit trail tables for all trading decisions
- No manual database state — reproducible from migrations

## 10. API Design

- RESTful API (FastAPI) between backend and dashboard
- Async where appropriate for I/O operations
- Typed request/response models (Pydantic)
- Authentication for dashboard access
- Rate limiting on external API calls (Zerodha, AI providers)
