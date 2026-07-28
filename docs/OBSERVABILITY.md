# TradeCraft — Observability

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Logging

### Structured Logging
- Use structured (JSON) log format for machine parseability
- Human-readable format for console during development
- Log level configurable via `LOG_LEVEL` environment variable

### Log Levels
| Level | Use |
|-------|-----|
| DEBUG | Detailed diagnostic information |
| INFO | Normal operational events |
| WARNING | Unexpected but handled situations |
| ERROR | Failures requiring attention |
| CRITICAL | System-threatening failures |

### Log Categories
| Category | Examples |
|----------|----------|
| `trading` | Signals, proposals, approvals, orders, fills |
| `risk` | Risk checks, limit breaches, RISK LOCK events |
| `compliance` | Compliance checks, regulatory flags |
| `data` | Data ingestion, quality checks, gaps |
| `ai` | AI calls, responses, costs, errors |
| `broker` | Broker communication, session management |
| `system` | Startup, shutdown, health checks |

### Log Storage
- Logs written to `LOG_DIR` (configurable, default `./logs`)
- Rotation policy: daily rotation, configurable retention
- Sensitive values always redacted (see SECURITY.md)

## 2. Health Checks

The system should expose health status for:

| Component | Health Check |
|-----------|-------------|
| Database | Connection alive, migrations current |
| Market data | Last update timestamp, freshness |
| Trading calendar | Calendar loaded, next trading day known |
| Broker connection | Session status (paper: always healthy) |
| AI providers | Availability, budget remaining |
| Risk engine | Active, limits loaded |
| Compliance engine | Active, rules loaded |

## 3. AI Cost Tracking

### Per-Call Tracking
| Field | Description |
|-------|-------------|
| `provider` | Claude, OpenAI, Gemini |
| `model` | Specific model version |
| `task` | What the AI call was for |
| `input_tokens` | Tokens sent |
| `output_tokens` | Tokens received |
| `estimated_cost_inr` | Estimated cost in ₹ |
| `timestamp` | When the call was made |
| `latency_ms` | Response time |
| `success` | Whether call succeeded |

### Budget Enforcement
- Monthly ceiling: ₹2,500 (configurable via `AI_MONTHLY_BUDGET_INR`)
- Warning at 80% of budget
- AI research pauses or requires approval at 100%
- Deterministic trading/risk never depends on AI availability
- Monthly expenditure visible in dashboard

## 4. Data Freshness Monitoring

| Metric | Alert Threshold |
|--------|----------------|
| Market data last update | > 1 trading day stale |
| Corporate actions last check | > 7 days |
| Trading calendar last verified | > 30 days |
| Regulatory sources last checked | > 30 days |

## 5. Dashboard Metrics

The web dashboard must display:
- System health status (overall + per component)
- Data freshness indicators
- AI cost for current month
- Recent audit log entries
- Risk state (NORMAL / ELEVATED / RISK_LOCK)
- Compliance status
- Paper/Live mode indicator
