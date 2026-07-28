# TradeCraft — Broker Execution Policy

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Target Broker

**Zerodha Kite Connect** is the target live broker.

The user has a Kite developer account and will activate the API subscription before integration testing.

## 2. Authentication

### Credentials
```
KITE_API_KEY=      # In .env, NEVER in source
KITE_API_SECRET=   # In .env, NEVER in source
```

### Session Management
- Follow Zerodha's documented authentication/session flow
- Do NOT invent permanent access-token behaviour
- Handle session expiry gracefully
- Re-authentication must be supported

### Security Rules
- Never hard-code credentials
- Never commit credentials to Git
- Never ask user to paste secrets into source files, docs, Git commits, or AI prompts
- Never log credentials (even partially)

## 3. Broker Interface Architecture

```python
class BrokerInterface(Protocol):
    """All order execution goes through this abstraction."""
    async def place_order(self, order: Order) -> OrderResult: ...
    async def modify_order(self, order_id: OrderId, ...) -> OrderResult: ...
    async def cancel_order(self, order_id: OrderId) -> OrderResult: ...
    async def get_order_status(self, order_id: OrderId) -> OrderStatus: ...
    async def get_positions(self) -> list[Position]: ...
    async def get_holdings(self) -> list[Holding]: ...
```

### Adapters
- **PaperBroker** — Simulated execution, default mode, M7
- **ZerodhaBroker** — Kite Connect integration, M11

See [PAPER_TRADING.md](PAPER_TRADING.md) for paper/live separation.

## 4. Error Handling

Design for all of:

| Scenario | Handling |
|----------|----------|
| API errors | Retry with backoff, log, alert |
| Partial fills | Track filled/remaining quantity |
| Rejected orders | Log reason, notify, do not retry without review |
| Duplicate requests | Idempotency keys prevent double orders |
| Rate limits | Respect Kite Connect rate limits, queue if needed |
| Session expiry | Detect, re-authenticate, retry |
| Network failures | Timeout handling, retry policy, circuit breaker |
| Market closed | Reject orders outside market hours |

## 5. Order Lifecycle

```
Order Created
  ▼
Risk Validation ──── FAIL → Blocked
  ▼ PASS
Compliance Validation ── FAIL → Blocked
  ▼ PASS
Human Approval ──── REJECTED → Logged
  ▼ APPROVED
Submit to Broker
  ▼
Monitor Status
  ├── FILLED → Position created
  ├── PARTIALLY_FILLED → Track remainder
  ├── REJECTED → Log, notify
  └── FAILED → Log, notify, error handling
```

## 6. Idempotency

Every order submission must include an idempotency key. If a submission is retried (e.g., after network timeout), the same key prevents duplicate orders at the broker.

## 7. Reconciliation

After each trading session:
- Compare internal position state with broker-reported positions
- Flag and investigate discrepancies
- Never silently override internal state with broker state without logging

## 8. Zerodha API Usage by Milestone

| Milestone | Zerodha Usage | Purpose |
|-----------|---------------|---------|
| M0 | None | Architecture only |
| M1 | Historical data API (read-only) | Market data ingestion |
| M2–M10 | Historical data API (read-only) | Data for research/backtesting |
| M11 | Full trading API | Live order execution |

Live execution is M11. Earlier milestones use Zerodha ONLY for approved read-only/data functionality.

## 9. Never Invent Kite API Behaviour

- Use only documented Kite Connect API endpoints
- Do not assume capabilities not in official documentation
- When documentation is ambiguous, fail safely
- Verify API behaviour against current official docs, not AI memory
