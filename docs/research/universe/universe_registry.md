# UNIVERSE REGISTRY & DATASET VERSIONING SPECIFICATION

The `UniverseRegistry` maintains immutable metadata definitions for supported universes (`NIFTY50`, `NIFTY100`, `NIFTY200`, `NIFTY250`, `NIFTY500`, `CUSTOM`).

## Dataset Versioning Parameters
Every comparative backtest run MUST permanently record the following cryptographic versioning metadata:
- `dataset_version`: Dataset snapshot version (e.g. `v1`)
- `membership_version`: Membership version (e.g. `1.0.0`)
- `corporate_action_version`: Corporate action version (e.g. `1.0.0`)
- `security_master_version`: Security Master catalog version (e.g. `1.0.0`)
- `checksum`: SHA256 cryptographic hash of universe metadata.
