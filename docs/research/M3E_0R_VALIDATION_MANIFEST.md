# M3E.0R — AUTHORITATIVE VALIDATION MANIFEST & FREEZE CERTIFICATE

> **VALIDATION GOVERNANCE STATUS**: **`VALIDATION_GOVERNANCE_LOCK_ENACTED`**  
> **VALIDATION DATASET SPLIT**: `2022-01-01` $\rightarrow$ `2024-06-30` (Sealed)  
> **VALIDATION ACCESS COUNT**: **`0`** (`VALIDATION_ACCESS_COUNT = 0` verified)  
> **EXECUTION POLICY**: `EndOfBacktestPolicy.FORCE_CLOSE`  
> **PREFLIGHT EXECUTION GATE**: **`ENACTED & MANDATORY`**

---

## 1. STRATEGY & EXPERIMENT CONFIGURATION

- **Strategy Class**: `EarningsDriftV1Strategy` in [earnings_drift_v1.py](file:///c:/infiligence/automated-trader-tool/src/tradecraft/strategy/earnings_drift_v1.py)
- **Strategy ID & Version**: `strat_earnings_drift_v1` v1.0.0
- **Hypothesis UUID**: `hypo-cycle2-alpha013-v1` (ALPHA-013 Post-Earnings Announcement Drift)
- **Pre-Registered Parameters**:
  - `holding_period_max_sessions`: `30`
  - `atr_stop_multiplier`: `2.0`
  - `min_volume_expansion_ratio`: `1.5`
  - `position_size_pct`: `0.10`
- **Initial Capital**: `₹1,000,000.00`
- **Cost Model**: `IndianEquityDeliveryCostModel`
- **Slippage Model**: `FixedBasisPointSlippage(5)` (5 bps)
- **Universe**: `NIFTY_50`

---

## 2. PRE-REGISTERED VALIDATION DECISION GATES

The strategy will be evaluated on the sealed VALIDATION dataset against the following immutable pre-registered decision thresholds:

| Decision Metric | Pre-Registered Threshold | Mandatory / Optional | Lock Status |
| :--- | :---: | :---: | :---: |
| **Profit Factor** | $\ge 1.30$ | **MANDATORY** | **FROZEN** |
| **Expectancy ($R$)** | $\ge +0.25R$ | **MANDATORY** | **FROZEN** |
| **Sharpe Ratio** | $\ge 0.50$ | **MANDATORY** | **FROZEN** |
| **Maximum Drawdown** | $\le 25.0\%$ | **MANDATORY** | **FROZEN** |
| **Residual Accounting Error** | $= 0.0000$ INR | **MANDATORY** | **FROZEN** |
| **Minimum Trades Count** | $\ge 15$ | **MANDATORY** | **FROZEN** |

---

## 3. IMMUTABLE ARTIFACT SHA-256 FINGERPRINTS

| Component / Artifact | Path | SHA-256 Checksum |
| :--- | :--- | :--- |
| **Historical Market Database** | `data/tradecraft.db` | `6d336dcdf1e1a0454ca53a56861ada387f24e70c9aa476b74081c8014c81f28f` |
| **Strategy Implementation** | `src/tradecraft/strategy/earnings_drift_v1.py` | `c3f19080926cf203ea7e82ab254215a30190d9b86efee2b0db41b4cd277d3521` |
| **Backtest Engine** | `src/tradecraft/backtesting/engine.py` | `d098affd9b5fb98a5274659688fdd62ef42e96404282606db43c7de06dcd551c` |
| **Cost Model** | `src/tradecraft/backtesting/costs.py` | `bc133d17c1571545850caa3a4c5ab5c210d8493e92bc1fca570f5c3fa2c41002` |
| **Slippage Model** | `src/tradecraft/backtesting/slippage.py` | `f282ad43e6274409459d4176ed2b37545a026cfd213d5deb4971bfa9c2928a9b` |
| **DataPortal** | `src/tradecraft/backtesting/data_portal.py` | `a2ff18679287fffd434d4b675cc5f03450dc49999ddb910fb68845e52e4da882` |
| **Feature Store** | `src/tradecraft/research/feature_store.py` | `b5fcb96a8e1df5cccce25fdbf986322ae17894e5058859b6e255953bb777c375` |
| **Security Master** | `src/tradecraft/core/db_models.py` | `4064b33f07646166c40745ad21e34678fef9323cc23d61167aab24bd15542f00` |
| **Universe Registry** | `src/tradecraft/universe/universe_registry.py` | `c5e2d78f094b4672f1d873f2ccc3a24987fe82b1699d9aaf2252d92cff25ac91` |
| **M3D.4R Backtest Report** | `docs/research/M3D_4R_DEVELOPMENT_BACKTEST.md` | `02163dbfa122bc0541e87626952c68e977b09996d160daa47cfcb7c4d06058b8` |
| **M3D.4.5R Forensic Audit** | `docs/research/M3D_4_5R_FORENSIC_AUDIT.md` | `b60507a6dc957f13b94fb1117e22fca6f9d261269df5f990781cdcb3c33a99c5` |
| **Development Trade Ledger** | `scratch/m3d_4r_trade_ledger.json` | `b07a4076f8ef1f5a36970fa31f37a9cdfe2fe5dc2d2fb5103b63a8690a0ed7d8` |
| **Development Equity Curve** | `scratch/m3d_4r_equity_curve.json` | `860867894bf4d32ad0f47f231a4f7f4fc827df803745308e1e6d53f8ec2eafb8` |
| **Development Cash Ledger** | `scratch/m3d_4r_cash_ledger.json` | `71b3b14fa576dfb7e727e145d06e45dc6584301ad9b561552d052d903dc063c7` |
| **Authenticity Certificate** | `scratch/m3d_4r_authenticity_certificate.json` | `b7fc2c0318037500ea403da9f7a2873a4b9a6eef9f9e33df3060c895bffa3486` |

---

## 4. ENVIRONMENT REPRODUCIBILITY METADATA

- **Python Version**: `3.11.9`
- **Operating System**: `Windows-10`
- **Git Commit Hash**: `f9ec533091c41f4f36b4963b6255df72daff7d81`
- **SQLite Version**: `3.45.1`
- **Timezone**: `UTC`
- **Random Seed**: `42`
- **Lock Timestamp**: `2026-08-05 14:36:03 UTC`

---

## 5. ONE-SHOT VALIDATION PROTOCOL & PREFLIGHT GATE

1. **Mandatory Execution Preflight Gate**: The M3ER validation runner MUST execute preflight checks verifying all 15 SHA-256 fingerprints match the manifest before opening a single market bar from `2022-01-01`.
2. **Single Execution**: Exactly one backtest run on `VALIDATION` split (`2022-01-01` $\rightarrow$ `2024-06-30`). Zero retries permitted.
3. **Immutability Guarantee**: Any failure of the preflight gate or decision thresholds results in immediate permanent retirement of the strategy family.
