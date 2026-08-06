# DOCUMENTATION INDEX

---

## 🚨 START HERE

| Document | What it is |
|---|---|
| **[docs/PROJECT_STATUS.md](./PROJECT_STATUS.md)** | **Authoritative status, corrected history, and the roadmap to live trading. Read this first.** |
| [docs/research/REPO_AUDIT_2026-08-06.md](./research/REPO_AUDIT_2026-08-06.md) | The audit that voided Research Cycles 1 and 2 |
| [docs/research/NEXT_STEPS.md](./research/NEXT_STEPS.md) | Remediation detail and the commands to run now |
| [docs/research/known_mistakes.md](./research/known_mistakes.md) | Failures we do not repeat — MISTAKE #0 is the important one |

> **Context:** an independent audit on 2026-08-06 established that Research Cycles 1 and 2 ran
> entirely against a **synthetic price database**. Their conclusions were artifacts, not
> findings. All void milestone certificates, cycle summaries, graveyard entries and scratch
> artifacts were **deleted on 2026-08-06** — they remain in git history (commit `55e1360`) if
> ever needed. Real market data was ingested on 2026-08-06. **No hypothesis has yet been
> validly tested.**

---

## 🏛️ System & Architecture

| Document | What it is |
|---|---|
| [README.md](../README.md) | Repository landing page |
| [docs/OVERVIEW.md](./OVERVIEW.md) | System overview, vision, philosophy |
| [docs/GETTING_STARTED.md](./GETTING_STARTED.md) | Setup, virtualenv, CLI commands |
| [docs/ARCHITECTURE.md](./ARCHITECTURE.md) | Subsystem deep-dive |
| [docs/DOMAIN_MODEL.md](./DOMAIN_MODEL.md) | Core domain entities |
| [docs/RUNBOOK.md](./RUNBOOK.md) | Day-to-day operations & troubleshooting |
| [docs/REPOSITORY_MANIFEST.md](./REPOSITORY_MANIFEST.md) | Directory structure and ownership |
| [docs/adr/](./adr/) | 10 architectural decision records |

---

## 🧪 Research & Governance

| Document | What it is |
|---|---|
| [docs/GOVERNANCE_MANUAL.md](./GOVERNANCE_MANUAL.md) | Data firewalls and hypothesis gates |
| [docs/RESEARCH_PLAYBOOK.md](./RESEARCH_PLAYBOOK.md) | Step-by-step research workflow |
| [docs/DECISION_LOG.md](./DECISION_LOG.md) | Architectural decisions & rejected alternatives |
| [docs/ROADMAP.md](./ROADMAP.md) | Milestone roadmap (see PROJECT_STATUS.md §4 for current direction) |
| [docs/research/research_principles.md](./research/research_principles.md) | Core research discipline |
| [docs/research/research_methodology.md](./research/research_methodology.md) | Methodology |
| [docs/research/anti_overfitting_rules.md](./research/anti_overfitting_rules.md) | Pre-registration and experiment budgets |
| [docs/research/backtesting_invariants.md](./research/backtesting_invariants.md) | Invariants the engine must hold |
| [docs/research/dataset_firewall.md](./research/dataset_firewall.md) | Development / validation / final test separation |
| [docs/research/adr/](./research/adr/) | 21 research methodology ADRs |

---

## 🔬 Active Research — Cycle 3

| Document | What it is |
|---|---|
| [docs/research/alpha_library/alpha_registry.json](./research/alpha_library/alpha_registry.json) | **35-hypothesis backlog (ALPHA-014→048)** |
| [docs/research/C3R_0_ALPHA_BACKLOG.md](./research/C3R_0_ALPHA_BACKLOG.md) | Alpha backlog narrative |
| [docs/research/C3R_1_ALPHA_015_MEMORANDUM.md](./research/C3R_1_ALPHA_015_MEMORANDUM.md) | ALPHA-015 investment memo |
| [docs/research/C3R_1_LITERATURE_REVIEW.md](./research/C3R_1_LITERATURE_REVIEW.md) | Academic support |
| [docs/research/C3R_1_5_STRATEGY_DESIGN_REVIEW.md](./research/C3R_1_5_STRATEGY_DESIGN_REVIEW.md) | Design review & assumption register |

> ⚠️ The Cycle 3 documents above assessed data feasibility against the **synthetic** database,
> where cross-sectional correlation was 1.0 and relative strength was mathematically vacuous.
> Those feasibility judgements are void and must be redone against the real data. The economic
> reasoning and literature review remain useful.

---

## 📋 Policy

[BACKTESTING_POLICY](./BACKTESTING_POLICY.md) ·
[BROKER_EXECUTION_POLICY](./BROKER_EXECUTION_POLICY.md) ·
[COMPLIANCE_POLICY](./COMPLIANCE_POLICY.md) ·
[DATA_POLICY](./DATA_POLICY.md) ·
[NEWS_POLICY](./NEWS_POLICY.md) ·
[RISK_POLICY](./RISK_POLICY.md) ·
[STRATEGY_GOVERNANCE](./STRATEGY_GOVERNANCE.md) ·
[TESTING_POLICY](./TESTING_POLICY.md) ·
[TRADING_PHILOSOPHY](./TRADING_PHILOSOPHY.md) ·
[SECURITY](./SECURITY.md) ·
[REGULATORY_SOURCES](./REGULATORY_SOURCES.md)

---

## 🛠️ Operations

[PAPER_TRADING](./PAPER_TRADING.md) ·
[LOCAL_OPERATION](./LOCAL_OPERATION.md) ·
[DEPLOYMENT](./DEPLOYMENT.md) ·
[CLOUD_MIGRATION](./CLOUD_MIGRATION.md) ·
[OBSERVABILITY](./OBSERVABILITY.md) ·
[UI_UX](./UI_UX.md) ·
[CONTRIBUTING](./CONTRIBUTING.md) ·
[GLOSSARY](./GLOSSARY.md) ·
[FAQ](./FAQ.md) ·
[KNOWN_LIMITATIONS](./KNOWN_LIMITATIONS.md)
