# ADR-008: Human Approval Workflow

**Status**: ACCEPTED
**Date**: 2026-07-28
**Decision Makers**: User (constitution)

## Context

The system generates trade proposals but must not execute them without human approval. However, protective risk controls must not depend on human availability.

## Decision

### Two Categories of Exits

**Protective Exits** — Must NOT depend on human availability:
- Stop-loss orders
- RISK LOCK actions
- KILL SWITCH actions
- Pending entry invalidation when setup becomes materially invalid

**Discretionary Exits** — Should request human approval:
- Profit target exits
- Strategy-generated exit signals
- Manual position closing
- Partial profit-taking

### Trade Proposal Workflow

```
Signal Generated → Trade Proposal Created
  ↓
Dashboard displays proposal with full context
  ↓
Human reviews and decides: APPROVE or REJECT
  ↓
APPROVED → Order enters execution pipeline (risk → compliance → broker)
REJECTED → Logged with reason, no further action
```

### Required Proposal Information
Every proposal includes: instrument, strategy, setup, entry, stop, target/exit methodology, quantity, capital required, capital at risk, portfolio impact, risk/reward, technical evidence, fundamental evidence, support/resistance, market regime, sector context, news/events, risks, reason, edge rationale.

## Rationale

1. **Safety**: Human oversight prevents blind execution of potentially flawed signals
2. **Learning**: Human reviews every trade, building understanding
3. **Risk protection**: Protective controls operate independently of human availability
4. **Flexibility**: Once comfortable, approval requirements may be relaxed

## Consequences

- Dashboard must be designed for efficient trade review
- Proposals must be understandable to a quant finance beginner
- Protective stops must be managed by the system autonomously
- Pending entries must self-invalidate when conditions change materially
