# TRADECRAFT RESEARCH SYSTEM — START HERE

> **MANDATORY ONBOARDING INSTRUCTION FOR ALL DEVELOPERS AND AI AGENTS**:  
> Before proposing, modifying, or testing any strategy, you MUST read the [Research Graveyard](file:///c:/infiligence/automated-trader-tool/docs/research/research_graveyard.md) and [Strategy Lineage Registry](file:///c:/infiligence/automated-trader-tool/docs/research/strategy_lineage_registry.md) and verify that the proposed hypothesis is not a disguised retry of an abandoned lineage.
>
> **NON-NEGOTIABLE RULE**:  
> *A rejected strategy family may not be revived simply by changing parameter values, indicator periods, thresholds, or naming. Any future proposal must first demonstrate that it is based on a materially different economic hypothesis rather than a variation of an abandoned lineage.*

---

## 1. CURRENT PROJECT STATUS

- **Active Research Cycle**: `Research Cycle 1 (CLOSED)`
- **Cycle 1 Master Outcome**: **`CLOSED_NO_SURVIVOR`**
- **Strategy Families Status**:
  - `Trend Pullback`: **`RESEARCH_GRAVEYARD`** (V1 $\rightarrow$ V2 $\rightarrow$ ABANDONED)
  - `Momentum Relative Strength`: **`RESEARCH_GRAVEYARD`** (V1 $\rightarrow$ V2 $\rightarrow$ ABANDONED)
  - `Breakout Confirmation`: **`RESEARCH_GRAVEYARD`** (V1 $\rightarrow$ V2 $\rightarrow$ V3 $\rightarrow$ ABANDONED)
  - `Mean Reversion`: **`RESEARCH_GRAVEYARD`** (V1 $\rightarrow$ V2 $\rightarrow$ V3 $\rightarrow$ ABANDONED)
- **Next Permitted Milestone**: `M3C.1 — POINT-IN-TIME UNIVERSE EXPANSION ARCHITECTURE` (Pending User Approval)

---

## 2. SEALED DATASETS & DATA FIREWALL

Access rules are enforced at runtime via `DevelopmentDataFirewall`:
- **`DEVELOPMENT`** (`2016-08-01` $\rightarrow$ `2021-12-31`): The ONLY historical dataset consumed during Cycle 1.
- **`VALIDATION`** (`2022-01-01` $\rightarrow$ `2024-06-30`): **STRICTLY SEALED** (`VALIDATION_ACCESS_COUNT = 0`).
- **`FINAL TEST`** (`2024-07-01` $\rightarrow$ `2026-07-28`): **STRICTLY SEALED** (`FINAL_TEST_ACCESS_COUNT = 0`).

> [!CAUTION]
> Any attempted query or feature calculation beyond `2021-12-31` will raise `DataBoundaryViolationError` and terminate execution immediately.

---

## 3. MANDATORY BACKTESTING INVARIANTS

All strategy research code must strictly satisfy:
1. **Point-in-Time Data**: Clock gating via `DataPortal` prevents lookahead bias.
2. **Signal/Execution Timing**: Signal evaluated at Date $T$ close $\rightarrow$ Execution strictly at Date $T+1$ open or later (`signal_date < entry_date <= exit_date`).
3. **No Leverage or Short Selling**: Long-only cash equity delivery, integer share quantities (`quantity >= 1`).
4. **Accounting Integrity**: Realised Net PnL must reconcile to equity change: $\text{Final Equity} - \text{Initial Capital} \equiv \sum \text{TradeRecord.net\_pnl}$ under `EndOfBacktestPolicy.FORCE_CLOSE` ($\le ₹0.0001$).
5. **Execution Friction**: Transaction costs (STT, exchange fees, SEBI, GST, stamp duty, DP charges) and fixed basis point slippage embedded in execution prices.

---

## 4. PROHIBITED RESEARCH PRACTICES

The following are strictly forbidden across TradeCraft:
- Grid search, random parameter sweeps, or Bayesian optimization.
- Post-hoc strategy modifications or threshold adjustments after observing P&L results.
- Peeking into Validation or Final Test datasets.
- Re-interpreting failed Development Gate criteria as passed.
- Rescuing abandoned strategy lineages.

---

## 5. REQUIRED READING ROADMAP

Before writing any research code or proposing new hypotheses, consult the following permanent documentation artifacts:

| Document | Purpose |
| :--- | :--- |
| [research_principles.md](file:///c:/infiligence/automated-trader-tool/docs/research/research_principles.md) | Immutable project research philosophy (15 principles). |
| [research_cycle_1_summary.md](file:///c:/infiligence/automated-trader-tool/docs/research/research_cycle_1_summary.md) | Chronological master history from M3A to M3B.4. |
| [strategy_lineage_registry.md](file:///c:/infiligence/automated-trader-tool/docs/research/strategy_lineage_registry.md) | Complete lineage records and SHA256 hashes for all strategies. |
| [research_graveyard.md](file:///c:/infiligence/automated-trader-tool/docs/research/research_graveyard.md) | Detailed failure mechanisms for all abandoned hypotheses. |
| [research_decision_log.md](file:///c:/infiligence/automated-trader-tool/docs/research/research_decision_log.md) | Log of formal governance decisions (DEC-2026-001 to DEC-2026-014). |
| [known_mistakes.md](file:///c:/infiligence/automated-trader-tool/docs/research/known_mistakes.md) | Registry of "research scars" and mistakes never to repeat. |
| [engineering_lessons.md](file:///c:/infiligence/automated-trader-tool/docs/research/engineering_lessons.md) | Analysis of the 6 major engineering defects discovered & fixed. |
| [backtesting_invariants.md](file:///c:/infiligence/automated-trader-tool/docs/research/backtesting_invariants.md) | Technical invariants required for all backtesting code. |
| [research_roadmap.md](file:///c:/infiligence/automated-trader-tool/docs/research/research_roadmap.md) | Long-term multi-cycle project roadmap (Cycles 1 to 7). |
| [glossary.md](file:///c:/infiligence/automated-trader-tool/docs/research/glossary.md) | Canonical definitions of all research and trading terminology. |
