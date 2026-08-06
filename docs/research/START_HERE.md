# TRADECRAFT RESEARCH — START HERE

> **MANDATORY ONBOARDING FOR ALL DEVELOPERS AND AI AGENTS.**
>
> Read **[docs/PROJECT_STATUS.md](../PROJECT_STATUS.md)** before doing anything else. It is
> the authoritative status document and supersedes every narrative in this repository.

---

## 1. CURRENT STATUS

- **Research Cycles 1 and 2: VOID.** Both ran entirely against a synthetic price database
  generated inside this repo and stamped `source='ZERODHA_KITE_EOD'`. Their conclusions —
  "no strategy survived development", "PEAD V1 does not work" — are artifacts, not findings.
- **The research graveyard has been deleted and all four family bans lifted.** Trend
  Pullback, Momentum RS, Breakout Confirmation and Mean Reversion were never validly tested
  and are eligible again.
- **Real data ingested 2026-08-06**: 142 instruments, 387,874 bars, 2014-08-11 → 2026-08-06,
  in PostgreSQL, passing the authenticity gate.
- **Blocking now**: corporate action adjustment. Largest daily move is +190.67% and
  `is_adjusted=False` on every bar.
- **No validated strategy exists. No order-placement code exists.**

Void milestone certificates, cycle summaries, the graveyard, the lineage registry and all
scratch artifacts were deleted on 2026-08-06. They remain in git history (commit `55e1360`).

---

## 2. THE NON-NEGOTIABLE RULE — RESTATED

The original rule was *"a rejected strategy family may not be revived by changing parameter
values."* That rule is sound, but it was applied to families rejected on fabricated
evidence, which turned a safeguard into a permanent ban on legitimate research.

**The corrected rule:**

> A strategy family may not be revived by changing parameter values, indicator periods,
> thresholds or naming — **when the original rejection was based on valid evidence.**
> A rejection derived from data that has since been shown to be invalid confers no
> protection and must be discarded, not honoured.

Before any future rejection is treated as binding, confirm it was produced against data that
passed the authenticity gate.

---

## 3. DATASET FIREWALL

Re-declared 2026-08-06 against real data. Both access counters reset to 0 — prior counts
referred to the synthetic store.

| Split | Range | Status |
|---|---|---|
| DEVELOPMENT | `2014-08-11` → `2021-12-31` | Open for research |
| VALIDATION | `2022-01-01` → `2024-06-30` | **SEALED** (access count 0) |
| FINAL TEST | `2024-07-01` → `2026-08-06` | **SEALED** (access count 0) |

> The FINAL TEST split now holds real out-of-sample data for the first time. It can be spent
> exactly once. Its right edge moves as daily ingestion continues — freeze an explicit end
> date in the run config before it is ever used.

---

## 4. MANDATORY INVARIANTS

1. **Data authenticity is blocking.** `python -m tradecraft data verify` must pass before any
   research run. Provenance is a property of the numbers, never of a `source` label.
2. **Point-in-time data.** `DataPortal` clock gating prevents lookahead.
3. **Signal/execution timing.** Signal at date T close → execution at T+1 open or later
   (`signal_date < entry_date <= exit_date`).
4. **No leverage or short selling.** Long-only cash equity, integer share quantities.
5. **Accounting integrity.** `Final Equity − Initial Capital ≡ Σ net_pnl` under `FORCE_CLOSE`.
6. **Execution friction.** STT, exchange fees, SEBI, GST, stamp duty, DP charges and slippage
   embedded in execution prices.
7. **Every strategy declares its exits.** `SignalIntent` rejects signals with no stop, target
   or time stop. `END_OF_BACKTEST` exits above 5% of trades means exits are not firing.
8. **Every result names its source database** via `BacktestResult.data_provenance`.

---

## 5. PROHIBITED

- Grid search, parameter sweeps, Bayesian optimisation.
- Post-hoc threshold changes after observing P&L.
- Peeking into Validation or Final Test.
- Re-interpreting a failed gate as passed.
- **Citing any M3A–M3G result as evidence.**
- Gating a decision on a metric that has no hand-computed fixture test.

---

## 6. REQUIRED READING

| Document | Purpose |
|---|---|
| [../PROJECT_STATUS.md](../PROJECT_STATUS.md) | **Authoritative status and roadmap** |
| [REPO_AUDIT_2026-08-06.md](./REPO_AUDIT_2026-08-06.md) | What went wrong and why it was invisible |
| [known_mistakes.md](./known_mistakes.md) | Research scars — MISTAKE #0 is the important one |
| [NEXT_STEPS.md](./NEXT_STEPS.md) | Current remediation state and commands |
| [research_principles.md](./research_principles.md) | Research philosophy |
| [research_methodology.md](./research_methodology.md) | Methodology |
| [anti_overfitting_rules.md](./anti_overfitting_rules.md) | Pre-registration and experiment budgets |
| [backtesting_invariants.md](./backtesting_invariants.md) | Technical invariants |
| [dataset_firewall.md](./dataset_firewall.md) | Split separation rules |
| [engineering_lessons.md](./engineering_lessons.md) | Defects found and fixed |
| [research_decision_log.md](./research_decision_log.md) | Formal governance decisions |
| [research_roadmap.md](./research_roadmap.md) | Multi-cycle roadmap |
| [glossary.md](./glossary.md) | Terminology |
| [alpha_library/alpha_registry.json](./alpha_library/alpha_registry.json) | 35-hypothesis backlog (ALPHA-014→048) |
