# ADR-008: WHY IMMUTABLE SECURITY UUIDs ARE USED INSTEAD OF TICKER SYMBOLS

## Status
Accepted

## Context
Ticker symbols change due to corporate renames, exchange reassignments, and mergers (e.g. `M&M` $\rightarrow$ `MAHMRA`). Using symbols as primary keys breaks history when symbols change.

## Decision
TradeCraft internal models, trade ledgers, and feature stores use an immutable `security_uuid` (UUID4 string) as the primary key. Ticker symbols and ISIN codes are attributes mapped to `security_uuid` via effective-dated history records.

## Consequences
- **Positive**: 100% corporate identity continuity across renames, mergers, and demergers.
