# TradeCraft

**Autonomous Indian Swing Trading Platform**

> Capital preservation first. Risk-adjusted returns second. Raw profit last.

## Status

| Milestone | Status |
|-----------|--------|
| M0: Requirements & Architecture | ✅ Complete |
| M1: Market Data Foundation | 🔲 Not Started |

**Mode: PAPER ONLY** — No live trading capability exists.

## What Is This?

TradeCraft is a personal algorithmic swing trading platform for the Indian equity market (NSE, Nifty 50). It is designed to:

- Research and validate trading strategies systematically
- Manage risk with deterministic, non-bypassable controls
- Require human approval for every trade
- Paper trade first, live trade only after extensive validation
- Explain financial concepts to a non-expert user

See [Trading Philosophy](docs/TRADING_PHILOSOPHY.md) for the full priority hierarchy.

## Architecture

**Modular monolith** — Python backend with React + TypeScript dashboard, PostgreSQL database, Docker infrastructure.

See [Architecture](docs/ARCHITECTURE.md) for the full system design.

## Quick Start

```bash
# Prerequisites: Python 3.11+, Docker, Node.js 18+, Git

# 1. Clone and configure
git clone <repository-url>
cd automated-trader-tool
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD at minimum

# 2. Start database
docker compose up -d

# 3. Set up Python environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

> **Note**: The application is not yet runnable. M0 establishes the foundation.

## Project Structure

```
src/tradecraft/              Python application (26 modules)
dashboard/                   React + TypeScript dashboard (planned)
tests/                       Automated tests
docs/                        Policy & design documents
docs/adr/                    Architecture Decision Records
docs/strategy-decisions/     Strategy Decision Records
ai/                          Agent memory & instructions
```

## Key Documents

| Document | Description |
|----------|-------------|
| [Product Requirements](docs/PRODUCT_REQUIREMENTS.md) | Full PRD |
| [Architecture](docs/ARCHITECTURE.md) | System design, module boundaries |
| [Domain Model](docs/DOMAIN_MODEL.md) | Entities, relationships |
| [Risk Policy](docs/RISK_POLICY.md) | Risk limits, RISK LOCK, KILL SWITCH |
| [Trading Philosophy](docs/TRADING_PHILOSOPHY.md) | Priority hierarchy, core beliefs |
| [Roadmap](docs/ROADMAP.md) | All milestones M0–M13 |
| [Glossary](docs/GLOSSARY.md) | Trading terminology explained |
| [Current State](ai/CURRENT_STATE.md) | What actually exists right now |

## Contributing

This is a personal project. See [Agent Instructions](ai/AGENT_INSTRUCTIONS.md) for AI agent guidelines.

## License

Proprietary. Not open source.