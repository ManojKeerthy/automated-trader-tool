# ADR-004: Deterministic vs AI Boundaries

**Status**: ACCEPTED
**Date**: 2026-07-28
**Decision Makers**: User (constitution)

## Context

The system uses AI (LLMs) for research and analysis but must ensure that critical trading operations remain deterministic, reliable, and safe even when AI is unavailable.

## Decision

Establish a hard boundary between deterministic and AI-assisted operations:

### DETERMINISTIC (No AI dependency, no LLM in path)
- Risk calculations and limit enforcement
- Compliance validation
- Order execution pipeline
- Position sizing
- RISK LOCK / KILL SWITCH
- P&L calculations
- Data quality checks
- Protective stop execution
- Portfolio state management

### AI-ASSISTED (Advisory, validated, human-approved)
- Strategy research and hypothesis generation
- Feature discovery
- News analysis and summarisation
- Market commentary
- Backtest result analysis
- Failure diagnosis
- Strategy degradation detection

## Rationale

1. **Safety**: LLMs can hallucinate, produce inconsistent output, or be unavailable. Critical financial operations must not depend on them.
2. **Reliability**: The system must be safe during AI outages.
3. **Auditability**: Deterministic code produces reproducible results. LLM output varies.
4. **Regulatory**: Automated trading decisions should be based on transparent, auditable logic.

## Consequences

- AI module may be imported by research, screening, and strategy discovery modules
- AI module MUST NOT be imported by risk, compliance, orders, broker, positions, or P&L modules
- LLM output is treated as untrusted structured input requiring validation
- All AI calls are logged with cost tracking
- System must function safely with `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `GOOGLE_AI_API_KEY` all empty/missing
