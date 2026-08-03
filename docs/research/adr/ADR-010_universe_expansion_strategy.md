# ADR-010: UNIVERSE EXPANSION STRATEGY VIA DECOUPLED DEFINITIONS

## Status
Accepted

## Context
Expanding research from NIFTY 50 to NIFTY 250 or NIFTY 500 should not require refactoring strategy code or database schemas.

## Decision
Universes are defined configurationally in `UniverseRegistry`. Strategies consume universe identifiers via `UniverseAPI.get_constituents(universe_id, query_date)`. Expanding to larger universes requires adding metadata definitions and membership rows without modifying core code.

## Consequences
- **Positive**: Zero architectural friction when scaling from NIFTY 50 to full NSE equity universe.
