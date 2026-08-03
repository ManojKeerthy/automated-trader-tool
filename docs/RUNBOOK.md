# DAY-TO-DAY OPERATIONAL RUNBOOK

## 1. Routine Operational Procedures

### Research Execution Procedures
1. **Pre-Registration Audit**: Run `.venv\Scripts\python.exe scratch/run_m3d_1_preregistration_audit.py` to verify admission gate & novelty engine.
2. **Blind Signal Audit**: Run `.venv\Scripts\python.exe scratch/run_m3d_3_blind_signal_audit.py` to verify signal density & sanity checks without calculating P&L.
3. **Forensic Audit Execution**: Run `.venv\Scripts\python.exe scratch/run_m3d_4_5_forensic_audit.py` to verify independent metric recomputation and pre-registered forensic criteria.

### System Health & Quality Assurance
```bash
# Run mypy strict type checker
.venv\Scripts\python.exe -m mypy src/tradecraft

# Run ruff code linter
.venv\Scripts\python.exe -m ruff check src

# Run unit regression test suite
.venv\Scripts\python.exe -m pytest tests/ -v --ignore=tests/integration
```

---

## 2. Troubleshooting & Recovery Procedures

### Data Portal Firewall Violations
- **Symptom**: `DataBoundaryViolationError` raised during execution.
- **Root Cause**: Script or function attempted to query date $> 2021-12-31$ (DEVELOPMENT boundary).
- **Resolution**: Verify query start/end dates. Ensure clock is correctly gated to DEVELOPMENT split.

### Trade Ledger SHA-256 Mismatch
- **Symptom**: Checksum verification fails for `scratch/m3d_4_5_trade_ledger.json`.
- **Root Cause**: Accidental file modification or non-deterministic trade generation.
- **Resolution**: Restore `scratch/m3d_4_5_trade_ledger.json` from git history. Re-verify SHA-256 fingerprint: `72414b3adb3cc21f29a275a7ccc8819328b56e584ea80f0cc1801fc8cd1d4bd8`.
