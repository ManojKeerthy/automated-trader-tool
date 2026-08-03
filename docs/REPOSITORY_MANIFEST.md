# REPOSITORY MANIFEST & DIRECTORY STRUCTURE

This document details the complete repository directory structure, ownership, immutability status, and architecture fit:

| Path / Directory | Description | Source-Controlled vs Generated | Immutability Status | Ownership |
| :--- | :--- | :---: | :---: | :--- |
| `src/tradecraft/` | Core Platform Python Package | Source-Controlled | Mutable via PR | Quant Engineering |
| `src/tradecraft/sdk/` | Public Research SDK (`ResearchClient`) | Source-Controlled | Mutable via PR | Quant Engineering |
| `src/tradecraft/research/` | Alpha Library, Registries & Framework | Source-Controlled | Immutable Definitions | Research Team |
| `src/tradecraft/universe/` | Point-in-Time Universe Architecture | Source-Controlled | Core Subsystem | Data Engineering |
| `src/tradecraft/strategy/` | Pure Strategy Implementations | Source-Controlled | Frozen per Hypothesis | Quantitative Research |
| `src/tradecraft/backtesting/` | Event-Driven Engine & DataPortal | Source-Controlled | Core Subsystem | Core Platform |
| `config/` | Machine-Readable Platform Governance State | Source-Controlled | State Locked | Governance Officer |
| `docs/` | Institutional Knowledge Base & ADRs | Source-Controlled | Documentation | All Contributors |
| `scratch/` | Audit Scripts & Intermediate Artifacts | Source-Controlled | Audit Evidence | Research Audit |
| `tests/` | Pytest Unit & Integration Test Suites | Source-Controlled | Regression Suite | Engineering QA |
| `data/` | SQLite Database Storage (`tradecraft.db`)| Generated / Local | Local Data | System Administrator |
