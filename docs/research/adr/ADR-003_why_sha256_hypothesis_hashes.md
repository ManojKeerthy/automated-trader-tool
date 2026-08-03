# ADR-003: WHY SHA256 HYPOTHESIS CONFIGURATION HASHES ARE MANDATORY

## Status
Accepted

## Context
Researchers often make undocumented code modifications to strategy rules or parameter values, leading to silent configuration drift and non-reproducible research results.

## Decision
Every strategy definition MUST compute a deterministic SHA256 configuration hash from its sorted JSON parameters and strategy ID (`hashlib.sha256(f"{strategy_id}:{version}:{param_json}".encode("utf-8")).hexdigest()`). This hash is pre-registered and audited before backtest execution.

## Consequences
- **Positive**: Complete cryptographic immutability. Ensures that any parameter or rule modification alters the SHA256 hash, detecting unauthorized code mutations.
- **Positive**: Enables unambiguous lineage tracking across research cycles.
