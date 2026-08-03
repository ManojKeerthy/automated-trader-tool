# ADR-011: WHY THE FEATURE REGISTRY & FEATURE STORE ARE MANDATORY

## Status
Accepted

## Context
Allowing strategies to calculate raw technical indicators internally leads to code duplication, subtle lookahead bugs, non-standardized definitions, and un-cached redundant computation.

## Decision
Strategies MUST consume pre-registered features from `FeatureRegistry` via `FeatureStore`. Strategies are prohibited from calculating technical indicators internally.

## Consequences
- **Positive**: Standardized, audited feature definitions with cryptographic checksums.
- **Positive**: Significant performance speedup via feature caching.
