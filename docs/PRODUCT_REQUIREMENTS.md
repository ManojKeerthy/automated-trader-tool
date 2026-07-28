# TradeCraft — Product Requirements Document

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Product Vision

TradeCraft is a production-quality personal algorithmic swing trading platform for an Indian retail investor. It is designed for **positive long-term risk-adjusted expectancy** with **capital preservation and avoidance of catastrophic loss** as the highest priorities.

The system initially paper trades. It may only trade real capital through Zerodha Kite Connect after sufficient validation and explicit human approval.

## 2. User Profile

- Experienced software developer, beginner in quantitative finance
- Does NOT want to manually perform fundamental/technical analysis
- The software must perform research, screening, analysis, risk calculations, and strategy evaluation
- UI must explain financial/trading terminology contextually
- AI must NEVER be treated as an unquestionable source of financial, regulatory, mathematical, market, or execution truth

## 3. Priority Hierarchy

The following priority order must NEVER be reversed to increase expected profit:

1. Legal and regulatory compliance
2. Capital preservation
3. Prevention of catastrophic loss
4. Data correctness
5. Risk management
6. Strategy robustness
7. Execution correctness
8. Long-term risk-adjusted returns
9. Raw return

## 4. Market Scope

### Initial Universe
- Nifty 50 constituents (point-in-time correct for backtesting)

### Supported Instruments
- Indian cash equities
- Potentially broad-market Indian ETFs (after suitability/regulatory validation)

### Excluded Instruments
- Derivatives, options, futures, leveraged products
- Short positions (may be researched for future release)
- Penny stocks, illiquid securities
- Instruments under problematic regulatory restrictions

### Primary Exchange
- NSE (BSE support architecturally present but not blocking)

## 5. Trading Style

- **Primary**: Swing trading
- No arbitrary fixed holding duration
- Positions may be held days, weeks, or months when justified
- Weekend/earnings/event holding decisions via validated strategy/risk policies

## 6. Human Authority

### Initial Mode: Human-Approved
- Every new trade requires explicit human approval
- Discretionary/profit exits should request approval
- Protective stops and emergency risk controls must NOT depend on human availability

### Trade Proposal Requirements
Each proposed trade must provide: instrument, strategy, setup, proposed entry, stop, target/exit methodology, quantity, capital required, capital at risk, portfolio impact, risk/reward, technical evidence, fundamental evidence (where applicable), support/resistance context, market regime, sector context, relevant news/events, major risks, reason for trade, reason the strategy believes an edge exists.

### User Actions
- APPROVE or REJECT

## 7. Portfolio Parameters

- Starting paper capital: ₹50,000
- Risk profile: Moderate, capital preservation priority
- Profit initially fully reinvested
- No required monthly income target
- NO TRADE is a valid and desirable decision
- The system must be comfortable holding cash

## 8. Platform Requirements

- Windows, macOS, and Linux as first-class local environments
- Cross-platform deterministic behaviour
- Docker-based infrastructure
- Eventual cloud production on Linux containers

## 9. Technology Stack

- **Backend**: Python 3.11+
- **Dashboard**: React + TypeScript
- **Database**: PostgreSQL 16 (via Docker)
- **Infrastructure**: Docker / Docker Compose
- **Version Control**: Git + GitHub
- **CI/CD**: GitHub Actions

## 10. Operational Model

- Local-first operation on Windows laptop (16 GB RAM, 512 GB SSD)
- Manual start each trading day
- Target daily window: ~4:30 PM–6:00 PM IST (post-market close)
- End-of-day swing trading workflows
- Future: 24×7 cloud VM

## 11. Key Subsystems

See [ARCHITECTURE.md](ARCHITECTURE.md) for module boundaries and interfaces.

| Subsystem | Purpose |
|-----------|---------|
| Instrument Master | Universe management, Nifty 50 constituents |
| Market Data | OHLCV ingestion via Zerodha, quality checks, local storage |
| Corporate Actions | Splits, bonuses, dividends from NSE |
| Fundamentals | Financial statements, ratios |
| News/Events | News ingestion with provenance |
| Feature Engineering | Indicators, derived features |
| Screening | Universe filtering, candidate selection |
| Strategy | Definitions, registry, versioning, lifecycle |
| Research | Hypothesis testing, AI-assisted discovery |
| Backtesting | Engine, validation, bias defense |
| Market Regime | Regime detection and classification |
| Portfolio | Construction, tracking, allocation |
| Risk Engine | Limits, RISK LOCK, KILL SWITCH |
| Compliance | SEBI/NSE rules, fail-closed |
| Order Management | Order lifecycle |
| Broker Abstraction | Paper + Zerodha adapters |
| Positions | Tracking, reconciliation |
| P&L | Realised/unrealised calculation |
| AI Orchestration | Provider abstraction, cost tracking |
| Audit | Durable decision records |
| Dashboard | Web UI for monitoring and approval |

## 12. AI Integration

- Preferred providers: Claude > OpenAI > Gemini
- Monthly budget ceiling: ₹2,500 (pooled)
- AI is advisory only — never controls execution or bypasses risk
- AI calls must be observable and cost-tracked
- Platform must remain safe if LLM is unavailable
- LLM output is untrusted structured input requiring validation

## 13. Delivery Milestones

See [ROADMAP.md](ROADMAP.md) for detailed milestone definitions.

M0 through M13, from Requirements & Architecture through Cloud Migration.
