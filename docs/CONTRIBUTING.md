# CONTRIBUTOR & DEVELOPER GUIDELINES

## 1. Engineering Standards

- **Python Version**: Python `3.11+`
- **Type Annotations**: 100% type coverage required. Must pass `.venv\Scripts\python.exe -m mypy src/tradecraft` with 0 issues.
- **Code Style**: Must pass `.venv\Scripts\python.exe -m ruff check src` with 0 issues.
- **Unit Testing**: Every new feature or strategy must include corresponding unit tests in `tests/unit/`. All tests must pass: `.venv\Scripts\python.exe -m pytest tests/ -v`.

---

## 2. Quantitative Governance Compliance

- **Public SDK Interface**: All notebook and external script interactions MUST consume `ResearchClient` from `tradecraft.sdk`. Do NOT import internal modules directly.
- **Dataset Sealing**: NEVER write queries targeting Validation (`2022-01-01` $\rightarrow$ `2024-06-30`) or Final Test (`2024-07-01` $\rightarrow$ `2026-07-28`) datasets without explicit user authorization.
