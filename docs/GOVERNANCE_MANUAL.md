# QUANTITATIVE RESEARCH GOVERNANCE MANUAL

## 1. DATASET FIREWALL RULES

- **Data Boundary Violation**: Any query targeting dates $> 2021-12-31$ (DEVELOPMENT split end date) raises `DataBoundaryViolationError` at the `DataPortal` / SQLAlchemy boundary.
- **Sealed Access Counters**: `VALIDATION_ACCESS_COUNT` and `FINAL_TEST_ACCESS_COUNT` are tracked in `config/research_platform_state.json`. Any unauthorized access raises a critical alert.

---

## 2. RESEARCH GRAVEYARD & NOVELTY ENGINE

- **Abandoned Lineages**: `strat_trend_pullback`, `strat_momentum_rs`, `strat_breakout_confirm`, `strat_mean_reversion`.
- **Graveyard Collision Rule**: `NoveltyScoringEngine` compares proposed hypothesis keywords and feature definitions against all abandoned lineages. If token similarity $> 0.35$ (Novelty Score $< 0.65$), pre-registration is automatically blocked.

---

## 3. SINGLE DEVELOPMENT BACKTEST POLICY

- **Non-Override Policy**: Exactly ONE backtest execution is permitted on DEVELOPMENT data per hypothesis under `FORCE_CLOSE` policy. Grid searches, parameter sweeps, and post-hoc indicator modifications are strictly prohibited.
