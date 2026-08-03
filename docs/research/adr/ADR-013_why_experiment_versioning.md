# ADR-013: WHY EXPERIMENT ENVIRONMENT VERSIONING IS MANDATORY

## Status
Accepted

## Context
Code changes, dependency updates, OS differences, and non-deterministic random seeds can alter historical backtest output without altering strategy parameters.

## Decision
`ExperimentRegistry` records full environment reproducibility metadata (Python version, OS, `pip freeze`, execution hash, CPU, RAM, Git commit, random seed) for every run.

## Consequences
- **Positive**: 100% deterministic experiment reproducibility across environments.
