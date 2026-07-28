# TradeCraft — Paper Trading

> Version: 1.0.0 | Status: APPROVED | Last Updated: 2026-07-28

## 1. Paper Trading Mandate

**V1 MUST be paper trading.** There must be no accidental path from paper mode to live orders.

## 2. Architecture

Paper and live execution share the same `BrokerInterface` but use separate adapters:

```
BrokerInterface (Protocol)
├── PaperBroker     ← Default, always safe
└── ZerodhaBroker   ← Requires explicit configuration + safeguards
```

## 3. Safety Guarantees

| Guarantee | Implementation |
|-----------|---------------|
| Paper is default | `TRADECRAFT_MODE=PAPER` is the default; absent config = PAPER |
| No silent fallback | System NEVER silently falls back from paper to live |
| Mode is explicit | `BrokerMode` enum (PAPER/LIVE) is set at startup from configuration |
| Live requires safeguards | LIVE mode requires: explicit config, credential validation, human confirmation, compliance check |
| Mode is visible | Dashboard shows current mode prominently |
| Mode is immutable at runtime | Cannot switch from PAPER to LIVE while the system is running |
| Orders are tagged | Every order carries its `BrokerMode` — audit trail always records paper vs live |

## 4. Paper Broker Behaviour

The PaperBroker simulates order execution:

| Aspect | Behaviour |
|--------|-----------|
| Order placement | Accepted immediately (simulated) |
| Fill simulation | Filled at signal price + configurable slippage |
| Partial fills | Can be simulated for realism |
| Rejections | Can simulate random rejections for testing |
| Position tracking | Maintained in memory and database |
| Cash tracking | Deducted/credited with simulated costs |
| Market hours | Respects trading calendar |
| Data source | Uses stored market data for price reference |

## 5. Transition to Live

The path from paper to live is deliberately long:

```
Paper Trading (M7)
  ▼
Shadow Trading (M10) — paper trades compared to real market
  ▼
Human Review of shadow results
  ▼
Zerodha Integration (M11) — live API connected
  ▼
Limited Live (small capital)
  ▼
Full Live (gradual increase)
```

Each transition requires:
- Sufficient evidence from the previous stage
- Explicit human approval
- Updated risk parameters
- Compliance review

## 6. Paper Portfolio

- Initial capital: ₹50,000
- All risk parameters from RISK_POLICY.md apply
- Transaction costs are simulated (see BACKTESTING_POLICY.md § 3)
- P&L is tracked as if real
- All audit logging occurs as if real

## 7. Testing Invariants

These invariants MUST be tested and must NEVER be violated:

```
assert paper_mode_cannot_submit_live_order()
assert live_mode_requires_explicit_configuration()
assert absent_config_defaults_to_paper()
assert mode_cannot_change_at_runtime()
assert every_order_carries_broker_mode_tag()
assert paper_broker_never_calls_zerodha_api()
```
