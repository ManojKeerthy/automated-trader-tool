# ADR-012: WHY HYPOTHESIS PRE-REGISTRATION IS MANDATORY

## Status
Accepted

## Context
Running backtests before formalizing economic rationale leads to post-hoc storytelling and data mining.

## Decision
All research hypotheses MUST be pre-registered in `HypothesisRegistry` with explicit falsification criteria before backtest execution. Hypotheses become cryptographically immutable once registered.

## Consequences
- **Positive**: Complete defense against post-hoc curve-fitting.
