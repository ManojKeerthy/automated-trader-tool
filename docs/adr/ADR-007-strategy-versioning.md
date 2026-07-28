# ADR-007: Strategy Versioning

**Status**: ACCEPTED
**Date**: 2026-07-28
**Decision Makers**: User (constitution)

## Context

Strategies evolve through research. Production strategies must be reproducible and auditable. Changes to a live strategy must be controlled.

## Decision

All production strategy versions are **immutable**. Once deployed:
- Parameters cannot be changed
- Logic cannot be modified
- A new version must be created and pass through the full lifecycle

### Version Format
`{strategy_name}-v{major}.{minor}.{patch}`

Example: `momentum-breakout-v1.2.0`

### Versioning Rules
- **Major**: Fundamental logic change (new entry/exit rules)
- **Minor**: Parameter adjustment or feature addition
- **Patch**: Bug fix that doesn't change strategy behaviour

### Registry
The strategy registry stores all versions with:
- Strategy code reference (commit hash or module path)
- Parameters (frozen)
- Lifecycle stage
- Promotion/demotion history
- Performance metrics

## Rationale

1. **Auditability**: "Which strategy version generated this signal?" is always answerable
2. **Reproducibility**: Any past signal can be reproduced with the stored version + data
3. **Safety**: Prevents silent strategy drift
4. **Research**: Compare performance across versions

## Consequences

- Strategy code must be structured to support multiple versions simultaneously
- Registry must persist version history in PostgreSQL
- AI modifications to strategies create new versions, never modify existing ones
- Backtest results are linked to specific strategy versions
