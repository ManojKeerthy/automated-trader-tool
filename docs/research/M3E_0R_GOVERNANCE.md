# M3E.0R — VALIDATION GOVERNANCE SPECIFICATION & RULES

> **GOVERNANCE STATUS**: **`LOCK_ENACTED`**

---

## 1. MANDATORY PREFLIGHT CHECKLIST FOR M3ER

Before opening a single market bar from the sealed VALIDATION split (`2022-01-01` $\rightarrow$ `2024-06-30`), the M3ER runner must execute and log:
1. `validate_db_hash()`: Assert SHA-256(`data/tradecraft.db`) == `6d336dcdf1e1a0454ca53a56861ada387f24e70c9aa476b74081c8014c81f28f`
2. `validate_strategy_hash()`: Assert SHA-256(`earnings_drift_v1.py`) == `c3f19080926cf203ea7e82ab254215a30190d9b86efee2b0db41b4cd277d3521`
3. `validate_engine_hash()`: Assert SHA-256(`engine.py`) == `d098affd9b5fb98a5274659688fdd62ef42e96404282606db43c7de06dcd551c`
4. `validate_firewall_count()`: Assert `VALIDATION_ACCESS_COUNT == 0`
5. `validate_authenticity_verifier()`: Assert `AuthenticityVerifier` passes 100% clean AST inspection.

---

## 2. SINGLE-SHOT RULE & RETIREMENT POLICY

- Zero parameter tuning permitted.
- Zero feature engineering permitted.
- Zero backtest retries permitted.
- If any pre-registered gate fails, the strategy is marked **`RETIRED_FAIL_VALIDATION`** and cannot be revalidated under the current hypothesis UUID.
