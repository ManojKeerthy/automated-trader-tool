# TRADECRAFT ANTI-OVERFITTING & RESEARCH INTEGRITY RULES

> **RESEARCH DISCIPLINE SPECIFICATION**: Anti-data-mining standards enforcing pre-registration, parameter auditability, and single-run experimentation.

---

## 1. PRE-REGISTRATION IMMUTABILITY
- Before any backtest execution, the researcher or agent MUST freeze the strategy parameters, plain-language hypothesis, and parameter selection origins.
- The hypothesis registry computes a SHA256 configuration hash. Once registered, the configuration hash cannot be altered.

## 2. PARAMETER SELECTION PROVENANCE AUDIT
- Every parameter differing from parent configurations MUST undergo a Parameter Selection Provenance Audit.
- Required Invariant: `Alternatives Tested? = NO` and `P&L Used to Select? = NO`.
- Provenance category must be one of:
  - `INHERITED_FROM_V2`
  - `STANDARD_TECHNICAL_CONVENTION`
  - `ECONOMICALLY_DERIVED`
  - `RISK_MODEL_DERIVED`
  - `POST_HOC_DIAGNOSTIC_MOTIVATED`
- If `OPTIMISED_ON_DEVELOPMENT` is detected, the experiment is terminated BEFORE backtesting.

## 3. EXPERIMENT BUDGET LIMITS
- Maximum V2 configurations tested per family: **EXACTLY 1**.
- Maximum V3 configurations tested per family: **EXACTLY 1**.
- Retries, parameter sweeps, grid searches, Bayesian optimizations, and V3.1/V3.2 variants are strictly prohibited.

## 4. FIXED-TRADE COUNTERFACTUAL TESTING
- Robustness testing across friction scenarios (0 bps, 5 bps, 10 bps, 20 bps) MUST operate as fixed-trade counterfactuals on the exact executed trade paths.
- Regenerating signals or altering portfolio execution under alternative friction assumptions is prohibited.

## 5. POST-HOC DIAGNOSTIC LABELLING
- Diagnostic observations discovered after observing Development backtest results MUST be explicitly labelled:  
  $$\text{POST\_HOC\_DEVELOPMENT\_DIAGNOSTIC} \neq \text{AUTHORISED\_STRATEGY\_RULE}$$
- Post-hoc diagnostics may inform future hypothesis formulation for subsequent research cycles, but cannot be converted into retroactive strategy rules during backtesting.
