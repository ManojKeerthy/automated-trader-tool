# ADR-003: Paper/Live Broker Separation

**Status**: ACCEPTED
**Date**: 2026-07-28
**Decision Makers**: User (constitution)

## Context

The system must guarantee that paper trading cannot accidentally trigger live orders, while sharing as much code as possible between paper and live modes.

## Decision

Implement a `BrokerInterface` protocol with separate adapter implementations:

```
BrokerInterface (Protocol)
├── PaperBroker     ← Simulated execution, DEFAULT mode
└── ZerodhaBroker   ← Kite Connect, requires explicit config + safeguards
```

## Rationale

1. **Safety**: Architectural separation makes accidental live trading structurally impossible
2. **Testability**: PaperBroker provides predictable, testable execution
3. **Shared logic**: Order management, risk validation, and compliance checking work identically regardless of broker mode
4. **Extensibility**: Future brokers can be added as new adapters

## Safety Guarantees

- `TRADECRAFT_MODE=PAPER` is the default; absent configuration = PAPER
- System NEVER silently falls back from paper to live
- Mode is set at startup and immutable at runtime
- LIVE mode requires explicit configuration, credential validation, and human confirmation
- Every order carries its `BrokerMode` for audit
- PaperBroker never imports or calls Zerodha code

## Consequences

- All order execution goes through BrokerInterface
- No module outside `broker/` may know which adapter is active
- Testing must verify paper/live isolation invariants
- Dashboard must prominently display current mode
