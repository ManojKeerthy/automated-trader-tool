# ADR-009: RISK LOCK and KILL SWITCH Design

**Status**: ACCEPTED
**Date**: 2026-07-28
**Decision Makers**: User (constitution)

## Context

The system needs emergency risk controls that operate deterministically and cannot be bypassed by AI, strategies, or system errors.

## Decision

### RISK LOCK

Activates when portfolio drawdown reaches 10% from peak.

**Actions**:
1. Block all new position entries — no exceptions
2. Prioritise capital preservation for existing positions
3. Protective stops remain active
4. Log event with full portfolio state
5. Notify user via dashboard
6. Require human review to clear

**Cannot be cleared by**: AI, automatic timer, strategy signal, or portfolio recovery alone.

**Clear procedure**: Portfolio must have recovered AND human must explicitly review and approve resumption.

### KILL SWITCH

Global emergency control — the "big red button."

**Actions**:
1. Immediately block all new orders
2. Cancel all pending/open orders
3. Optionally close all positions (if configured and market open)
4. Log event with full system state
5. Require explicit human intervention to reset

**Triggers**:
- Manual user activation (dashboard button)
- System health critical failure
- Data integrity failure affecting trading decisions
- Complete broker communication failure during market hours with open positions

### Drawdown Levels (Progressive)

| Level | Threshold | State |
|-------|-----------|-------|
| Normal | < 5% | Normal trading |
| Warning | ≥ 5% | Reduced risk appetite, logged |
| Reduction | ≥ 8% | Active exposure reduction |
| Lock | ≥ 10% | RISK LOCK — no new positions |

## Rationale

1. **Capital preservation**: Prevents catastrophic loss from system errors or adverse markets
2. **Determinism**: These controls are pure code, no AI in path
3. **Irrevocability**: Cannot be silently bypassed
4. **Human authority**: Final decision to resume trading is always human

## Consequences

- Risk engine must continuously monitor drawdown
- RISK LOCK state persisted in database (survives restart)
- KILL SWITCH must be accessible from dashboard at all times
- Tests must verify these controls cannot be bypassed
