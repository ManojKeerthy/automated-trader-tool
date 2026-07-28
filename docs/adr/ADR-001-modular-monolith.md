# ADR-001: Modular Monolith Architecture

**Status**: ACCEPTED
**Date**: 2026-07-28
**Decision Makers**: User (constitution), System Architect

## Context

The system needs an architecture that supports 17+ domain modules with clear boundaries, while being practical for a single-developer project with ₹50,000 starting capital.

## Decision

Adopt a **modular monolith** architecture. A single deployable Python application with strong module boundaries enforced by convention and testing.

## Rationale

1. **Complexity vs. value**: Microservices, Kafka, and Kubernetes add operational complexity that is not justified for a single-user system
2. **Development speed**: A single deployment unit is faster to develop, test, and debug
3. **Latency**: In-process function calls are simpler than network calls between services
4. **Data consistency**: Simpler transaction management with a single database
5. **Future extraction**: Strong module boundaries make it possible to extract modules into services later if justified

## Consequences

- All modules live in `src/tradecraft/` with separate directories
- Each module exposes its public API through `__init__.py`
- Cross-module imports must go through public interfaces
- No shared mutable state between modules
- Modules communicate through defined interfaces, not direct internal access
- If a module grows too complex, it can be extracted with minimal refactoring

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|-----------------|
| Microservices | Unjustified complexity for single user, single developer |
| Event-driven / Kafka | Operational overhead without demonstrated need |
| Serverless | Not suitable for stateful trading system |
| Monolith without module boundaries | Would make future extraction difficult |
