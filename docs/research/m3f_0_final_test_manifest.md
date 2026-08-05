# M3F.0 — AUTHORITATIVE FINAL TEST EXECUTION MANIFEST & CONTRACT

> **FINAL TEST GOVERNANCE STATUS**: **`FINAL_TEST_GOVERNANCE_LOCKED`**  
> **STRATEGY FAMILY**: `EarningsDriftV1Strategy` (`strat_earnings_drift_v1`, `v1.0.0`)  
> **HYPOTHESIS UUID**: `hypo-cycle2-alpha013-v1`  
> **FINAL TEST DATASET**: `2024-07-01` $\rightarrow$ `2026-07-28` (Sealed)  
> **BACKTEST POLICY**: **`FORCE_CLOSE`** (One-Shot Execution)  
> **IMMUTABLE CONTRACT STATUS**: **`COMPLETE_AND_FROZEN`** ([ADR-019](file:///c:/infiligence/automated-trader-tool/docs/research/adr/ADR-019_FINAL_TEST_GOVERNANCE_LOCK.md))

---

## 1. FROZEN 13-COMPONENT DEPENDENCY INVENTORY & SHA-256 CHECKSUMS

| Subsystem Component | Version | Source File Path | Immutable SHA-256 Checksum |
| :--- | :---: | :--- | :--- |
| **Strategy Implementation** | `v1.0.0` | [earnings_drift_v1.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/strategy/earnings_drift_v1.py) | `a32d5a97cbf4dbefbb920ff782622021f6dc0a121b2bd1ab27a1945e618ca813` |
| **Backtesting Engine** | `v2.0.0` | [engine.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/backtesting/engine.py) | `d098affd9b5fb98a5274659688fdd62ef42e96404282606db43c7de06dcd551c` |
| **Public Research SDK** | `v1.0.0` | [research_client.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/sdk/research_client.py) | `adafb41c4923d8bac01fbc2ba7c4b7defab81aae8f3a9845636230a6426095df` |
| **Feature Store & Registry** | `v1.0.0` | [feature_store.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/research/feature_store.py) | `b5fcb96a8e1df5cccce25fdbf986322ae17894e5058859b6e255953bb777c375` |
| **Security Master** | `v1.0.0` | [security_master.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/universe/security_master.py) | `b43262a836cee3a0992a2e1a6316521c68d1c12242061f668753ebee4e3a230e` |
| **Corporate Action Registry** | `v1.0.0` | `src/tradecraft/universe/corporate_actions.py` | `66c80fefe9ef6907fc0d7eaffa8e7b434d0cbb9d08a903efb2b4b07fd95a31d4` |
| **Universe Registry** | `NIFTY250_v1` | `src/tradecraft/universe/universe_registry.py` | `c5e2d78f094b4672f1d873f2ccc3a24987fe82b1699d9aaf2252d92cff25ac91` |
| **Statutory Cost Model** | `v2.0.0` | `src/tradecraft/backtesting/costs.py` | `bc133d17c1571545850caa3a4c5ab5c210d8493e92bc1fca570f5c3fa2c41002` |
| **Slippage Model** | `5bps` | `src/tradecraft/backtesting/slippage.py` | `f282ad43e6274409459d4176ed2b37545a026cfd213d5deb4971bfa9c2928a9b` |
| **Validation Report** | `M3E` | [m3e_validation_report.md](file:///C:/Users/ManojKumarKeerthy/.gemini/antigravity-ide/brain/50823c0a-b0cc-4fe3-a1ba-0c813e7b1fe8/m3e_validation_report.md) | `60419466b24a767eed2a7605106533be09beb7797c922837d90b07d957da5105` |
| **Validation Certificate** | `M3E` | [m3e_validation_certificate.md](file:///C:/Users/ManojKumarKeerthy/.gemini/antigravity-ide/brain/50823c0a-b0cc-4fe3-a1ba-0c813e7b1fe8/m3e_validation_certificate.md) | `7b06005599e59e965a3f2f4be92a8c03cb362683be3b481d52fdd33976509820` |
| **Validation Results Data** | `M3E` | `scratch/m3e_validation_results.json` | `47783873b5e63b522063c6e4bf0e60eff7dae7066c6337d0a4f8770650b762a2` |
| **Validation Manifest** | `M3E.0` | `scratch/m3e_0_validation_manifest.json` | `ebb18cc8486f52a87ca5ff8e8f5ae0e06f4c95ae6d21815e906ed5002861c608` |

---

## 2. IMMUTABLE STRATEGY & CONFIGURATION FREEZE

```json
{
  "strategy_class": "EarningsDriftV1Strategy",
  "hypothesis_uuid": "hypo-cycle2-alpha013-v1",
  "strategy_version": "1.0.0",
  "parameters": {
    "holding_period_bars": 30,
    "min_surge_pct": 0.015,
    "volume_expansion_ratio": 1.50,
    "stop_loss_atr_mult": 2.00
  },
  "universe_definition": "NIFTY250",
  "execution_policy": "FORCE_CLOSE",
  "cost_model": "IndianEquityDeliveryCostModel",
  "slippage_model": "FixedBasisPointSlippage(bps=5)"
}
```

---

## 3. IMMUTABLE PRE-REGISTERED FINAL TEST DECISION GATES

| Decision Metric | Pre-Registered Gate Threshold | Failure Rationale |
| :--- | :---: | :--- |
| **Expectancy ($R$)** | $\ge +0.15\text{R}$ | Risk-adjusted trade edge falls below institutional standard |
| **Profit Factor** | $\ge 1.20$ | Gross gains fail to exceed gross losses by 20% |
| **Sharpe Ratio** | $\ge 1.10$ | Risk-normalized return insufficient for deployment |
| **Maximum Drawdown** | $\le 20.0\%$ | Unacceptable peak-to-trough capital loss |
| **Double-Entry Residual Error** | **`₹0.0000`** | Absolute zero-tolerance accounting failure |
| **Minimum Executed Trades** | $\ge 25$ | Sample size statistically invalid |

---

## 4. ONE-SHOT EXECUTION PROTOCOL & FAILURE CONSTRAINTS

1. **One-Shot Execution Rule**: Final Test is executed **EXACTLY ONCE** on the sealed `FINAL TEST` dataset (`2024-07-01` $\rightarrow$ `2026-07-28`).
2. **Prohibition of Retries & Tuning**: Parameter tuning, code modification, feature changes, or retries are **STRICTLY PROHIBITED**.
3. **Failure Handling**: If the strategy fails any single gate threshold, `strat_earnings_drift_v1` is automatically locked into the **Research Graveyard**, and Research Cycle 2 is declared abandoned.

---

## 5. SEALED DATASET FIREWALL ENFORCEMENT

- `DEVELOPMENT` (`2016-08-01` $\rightarrow$ `2021-12-31`): **PERMANENTLY FROZEN & CLOSED**
- `VALIDATION` (`2022-01-01` $\rightarrow$ `2024-06-30`): **COMPLETED & CLOSED** (`VALIDATION_ACCESS_COUNT = 1`)
- `FINAL TEST` (`2024-07-01` $\rightarrow$ `2026-07-28`): **100% SEALED** (`FINAL_TEST_ACCESS_COUNT = 0`)

---

## 6. HARD STOP CONFIRMATION

Milestone **M3F.0** is complete.

- **`FINAL_TEST_ACCESS_COUNT`** = `0`
- **Backtests Executed**: `0`
- **P&L Calculated**: `0`
- Awaiting explicit user authorization before executing **Milestone M3F — Single Authoritative FINAL TEST Backtest**.
