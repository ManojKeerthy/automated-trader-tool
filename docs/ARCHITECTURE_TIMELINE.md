# ARCHITECTURAL TIMELINE & SYSTEM EVOLUTION

This document traces the complete architectural evolution of the TradeCraft platform across all completed milestones from M1 through M3D.4.5:

| Milestone | Architectural State Introduced | Motivation | Key System Changes | Associated ADRs |
| :--- | :--- | :--- | :--- | :--- |
| **M1** | Historical NSE Data Pipeline | Market Data Ingestion | SQLite storage, OHLCV schema, data quality rules | ADR-001 |
| **M2** | Deterministic Backtester | Event-Driven Simulation | `BacktestEngine`, Double-entry cash accounting, `DataPortal` | ADR-002 to ADR-005 |
| **M3A** | Real Data Integration | Real NSE Data Acceptance | Real data portal, regime classifiers, benchmark data | ADR-006, ADR-007 |
| **M3B** | Strategy Research Lab | V2/V3 Strategy Evaluation | Signal viability, failure diagnostics, frozen decision triage | ADR-008 to ADR-010 |
| **M3C.0** | Research Governance Baseline | Cycle 1 Closure | Research Graveyard, decision records, 100% sealed Validation | ADR-011 |
| **M3C.1** | Point-in-Time Universe | Eliminating Survivorship Bias | `DataProvider`, `SecurityMaster`, `UniverseAPI`, `CorporateActionRegistry` | ADR-012 |
| **M3C.2** | Quant Research Platform | Platform Standardization | `FeatureRegistry`, `FeatureStore`, `HypothesisRegistry`, Public `ResearchClient` SDK | ADR-013 |
| **M3C.3** | Framework & Diagnostics | Cross-Experiment Analytics | `StatisticalDiagnostics`, `ExperimentComparator`, Explorer, Playbooks | ADR-014 |
| **M3C.4** | Alpha Research Library | Scientific Discovery | `AlphaLibrary` (20 sources), `HypothesisAdmissionGate`, `NoveltyScoringEngine` | ADR-015, ADR-016 |
| **M3D.0** | Cycle 2 Candidate Ranking | Alpha Candidate Selection | Weighted Objective Scoring (0-100), Ranked Candidate Shortlist | N/A |
| **M3D.0.1**| Alpha Portfolio & Roadmap | Multi-Cycle Strategy | Alpha Taxonomy, Dependency Matrix, Orthogonality Diagrams, Roadmap | N/A |
| **M3D.0.2**| Target Quant Architecture | 5-10 Year Blueprint | Quant Firm Capability Map, Portfolio Blueprint, Architecture Diagrams | N/A |
| **M3D.1** | Hypothesis Pre-Registration | Governance Lock | Pre-registered `hypo-cycle2-alpha013-v1` into `HypothesisRegistry` | N/A |
| **M3D.2** | Pure Code Implementation | Strategy Implementation | `EarningsDriftV1Strategy` in `src/tradecraft/strategy/earnings_drift_v1.py` | N/A |
| **M3D.3** | Blind Signal Viability Audit | Structural Verification | 1,500 signals generated, 100% financial blinding, Signal Sanity Audit | N/A |
| **M3D.4** | Single DEVELOPMENT Backtest | DEVELOPMENT Gate | Executed single backtest under `FORCE_CLOSE` $\rightarrow$ `DEVELOPMENT_SURVIVOR` | N/A |
| **M3D.4.5**| Forensic Audit & Freeze | Independent Verification | 5/5 criteria passed $\rightarrow$ `GO_FOR_VALIDATION` $\rightarrow$ **DEVELOPMENT Phase Frozen** | ADR-017 |
