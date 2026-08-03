# MANDATORY RESEARCH READINESS CHECKLIST (M3D ONWARD)

Before executing any future research milestone or backtest experiment, the researcher or AI agent MUST verify and document compliance with this 9-point checklist:

- [ ] **1. Hypothesis Pre-Registered**: Immutable `hypothesis_uuid` registered in `HypothesisRegistry` with economic & behavioral rationale.
- [ ] **2. Dataset Firewall Verified**: `VALIDATION_ACCESS_COUNT = 0` and `FINAL_TEST_ACCESS_COUNT = 0`.
- [ ] **3. Point-in-Time Features Verified**: All features queried via `UniverseAPI` and `FeatureStore` with $T+\text{lag}$ clock gating.
- [ ] **4. Accounting Invariants Pass**: Double-entry identity $\text{Final Equity} - \text{Initial Capital} \equiv \sum \text{Net PnL}$ ($\le ₹0.0001$) under `FORCE_CLOSE`.
- [ ] **5. No Optimization Code Invoked**: 0 grid sweeps, 0 Bayesian searches, 0 parameter retries.
- [ ] **6. Experiment ID Generated**: Cryptographic `experiment_id` generated with full environment metadata.
- [ ] **7. Feature Versions Frozen**: All features consumed derive from `FeatureRegistry` with SHA256 checksums.
- [ ] **8. Reports Enabled**: Automated Markdown and JSON report generators configured.
- [ ] **9. Artifact Paths Verified**: Output directory paths set under `scratch/` or artifacts directory.
