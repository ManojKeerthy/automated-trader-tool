# ADR-010: AI Provider Abstraction

**Status**: ACCEPTED
**Date**: 2026-07-28
**Decision Makers**: User (constitution + resolved decisions)

## Context

The system uses external AI providers for research and analysis. Multiple providers (Claude, OpenAI, Gemini) should be supported, with a pooled monthly budget.

## Decision

Implement an `AIProvider` abstraction layer:

```python
class AIProvider(Protocol):
    async def complete(self, prompt: str, **kwargs) -> AIResponse: ...
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Decimal: ...
    @property
    def provider_name(self) -> str: ...
    @property
    def model_name(self) -> str: ...
```

### Provider Priority
1. Claude (preferred)
2. OpenAI
3. Gemini

### Budget
- Monthly ceiling: ₹2,500 (pooled, not per-provider)
- Configurable via `AI_MONTHLY_BUDGET_INR`
- Warning at 80%
- AI research pauses at 100% (requires approval to continue)

### Cost Tracking
Per-call tracking of: provider, model, task, tokens, estimated cost, timestamp, latency, success/failure.

### Validation
All LLM output treated as untrusted structured input. Parse, validate schema, check for hallucinated data.

## Rationale

1. **Provider flexibility**: Not locked into one vendor
2. **Cost control**: Pooled budget with tracking prevents runaway costs
3. **Safety**: AI unavailability never breaks trading operations
4. **Observability**: Full cost and usage visibility

## Consequences

- AI module provides the abstraction; consumers don't know which provider is active
- Monthly expenditure visible in dashboard
- Deterministic operations never depend on AI
- LLM output validation is mandatory (not optional)
- System safe when all AI keys are missing
