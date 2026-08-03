# ADR-016: WHY GRAVEYARD LINEAGE COLLISION PROTECTION IS MANDATORY

## Status
Accepted

## Context
Researchers often attempt to revive abandoned strategies by slightly tweaking parameters or indicators, wasting research cycles on fundamentally flawed concepts.

## Decision
The `NoveltyScoringEngine` automatically evaluates text and feature similarity against abandoned Graveyard strategy lineages (`strat_trend_pullback`, `strat_momentum_rs`, `strat_breakout_confirm`, `strat_mean_reversion`). Any proposal with similarity $> 0.35$ (novelty $< 0.65$) is AUTOMATICALLY REJECTED.

## Consequences
- **Positive**: Complete defense against recycled failed ideas; forces exploration of genuinely novel alpha sources.
