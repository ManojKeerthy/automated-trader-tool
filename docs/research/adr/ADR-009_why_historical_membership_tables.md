# ADR-009: WHY HISTORICAL MEMBERSHIP TABLES ARE MANDATORY

## Status
Accepted

## Context
Index constituent changes occur regularly (additions, deletions, re-weightings). Static constituent flags in database tables cannot capture multiple membership periods.

## Decision
TradeCraft uses effective-dated membership records (`effective_from` $\rightarrow$ `effective_to`) in `HistoricalMembershipEngine` to track universe membership over time.

## Consequences
- **Positive**: Enables accurate reconstruction of index additions and deletions across historical dates.
