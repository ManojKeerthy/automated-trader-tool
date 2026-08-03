# GETTING STARTED & OPERATIONAL GUIDE

## 1. Environment Setup

### Prerequisites
- Python `3.11+`
- Windows PowerShell or Bash terminal

### Virtual Environment & Installation
```bash
# Activate virtual environment
.venv\Scripts\activate

# Install dependencies in editable mode
pip install -e .
```

---

## 2. Common Engineering Commands

| Operation | Command Line | Purpose |
| :--- | :--- | :--- |
| **Strict Type Check** | `.venv\Scripts\python.exe -m mypy src/tradecraft` | Ensures 100% mypy strict type safety |
| **Linter Check** | `.venv\Scripts\python.exe -m ruff check src` | Enforces ruff code quality standards |
| **Unit Test Suite** | `.venv\Scripts\python.exe -m pytest tests/ -v --ignore=tests/integration` | Runs 167+ unit regression tests |
| **Alpha Audit** | `.venv\Scripts\python.exe scratch/run_m3c_4_alpha_audit.py` | Audits 20 institutional alpha sources |
| **Firewall Verification** | `.venv\Scripts\python.exe scratch/run_m3d_0_ranking_audit.py` | Verifies dataset firewall boundary checks |
