# INSTITUTIONAL QUANTITATIVE RESEARCH FAQ

### Q1: Why is the DEVELOPMENT dataset permanently frozen in ADR-017?
**Answer**: Once a hypothesis is implemented, blind-audited, backtested under `FORCE_CLOSE`, and forensically audited, continuing to run backtests or tune parameters on the DEVELOPMENT dataset causes severe data mining and overfitting. Freezing DEVELOPMENT permanently preserves statistical rigor before entering Validation.

### Q2: Why is only ONE backtest permitted per hypothesis?
**Answer**: Multiple backtests with parameter tweaks are equivalent to covert data mining. Enforcing a pre-registration lock and single backtest policy ensures that strategy performance reflects genuine economic alpha rather than post-hoc curve fitting.

### Q3: Why do failed strategies enter a Research Graveyard?
**Answer**: Failed strategy lineages preserve institutional memory. The `NoveltyScoringEngine` blocks future researchers from unknowingly re-testing abandoned parameter or indicator combinations.

### Q4: How do I add a new strategy for Research Cycle 2?
**Answer**: Follow the [Research Playbook](file:///c:/infiligence/automated-trader-tool/docs/RESEARCH_PLAYBOOK.md): Select an alpha source from `AlphaLibrary`, pre-register a hypothesis into `HypothesisRegistry` via `ResearchClient`, implement the strategy class inheriting from `BaseStrategy`, execute the blind signal audit, and request user approval for DEVELOPMENT backtesting.
