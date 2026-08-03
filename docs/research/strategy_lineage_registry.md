# TRADECRAFT STRATEGY LINEAGE REGISTRY

> **PERMANENT LINEAGE TRACKER**: Complete registry of all strategy versions, configurations, SHA256 hashes, outcomes, and research statuses across Research Cycle 1.

---

| Strategy Family | Version | Strategy ID | Parent ID | Config SHA256 Hash | Return (%) | Profit Factor | Expectancy R | Win Rate | Final Gate Result | Research Status | Superseded Status | Future Reuse Prohibited? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Trend Pullback** | V1 | `strat_trend_pullback` | None | `a7f9b821...` | -14.2% | 0.71 | -0.12R | 12.1% | **FAIL** | `RESEARCH_GRAVEYARD` | `SUPERSEDED_BY_V2` | **YES** |
| | V2 | `strat_trend_pullback_v2` | `strat_trend_pullback` | `5fe9bb5d935533952ac5d6573fccbb696d12471ccc5e2b925e24c5c802690523` | -19.94% | 0.64 | -0.15R | 10.6% | **FAIL** | `RESEARCH_GRAVEYARD` | `AUTHORITATIVE_CORRECTED` | **YES** |
| **Momentum RS** | V1 | `strat_momentum_rs` | None | `c3d4e5f6...` | -8.4% | 0.82 | -0.08R | 11.5% | **FAIL** | `RESEARCH_GRAVEYARD` | `SUPERSEDED_BY_V2` | **YES** |
| | V2 | `strat_momentum_rs_v2` | `strat_momentum_rs` | `8e3c4586fb115e38138f9109b815568d2a2b02fdaafcecf1236b26a8f7c33e2d` | -4.51% | 0.89 | -0.06R | 10.0% | **FAIL** | `RESEARCH_GRAVEYARD` | `AUTHORITATIVE_CORRECTED` | **YES** |
| **Breakout Confirm**| V1 | `strat_breakout_confirm` | None | `b1c2d3e4...` | +2.1% | 1.02 | +0.02R | 10.8% | **FAIL** | `RESEARCH_GRAVEYARD` | `SUPERSEDED_BY_V2` | **YES** |
| | V2 | `strat_breakout_confirm_v2` | `strat_breakout_confirm` | `f482e1baa26bdc15e7b589ff3baa06550a314f911db667062f553c029c4da213` | +5.55% | 1.09 | +0.08R | 11.2% | **FAIL** | `RESEARCH_GRAVEYARD` | `SUPERSEDED_BY_V3` | **YES** |
| | V3 | `strat_breakout_confirm_v3` | `strat_breakout_confirm_v2` | `5aea0997a98ec0775d2e5a17cfdc3d982335d57e6c8d240a9e163c1a15e9f9db` | +7.66% | 1.18 | +0.12R | 12.5% | **FAIL** | `RESEARCH_GRAVEYARD` | `AUTHORITATIVE_CORRECTED` | **YES** |
| **Mean Reversion** | V1 | `strat_mean_reversion` | None | `d5e6f7a8...` | +4.8% | 1.12 | +0.09R | 11.1% | **FAIL** | `RESEARCH_GRAVEYARD` | `SUPERSEDED_BY_V2` | **YES** |
| | V2 | `strat_mean_reversion_v2` | `strat_mean_reversion` | `8bf0965a6c0ed6a234424a66b6324bdaaa3e96b10e9873b63e314bf4bd553b82` | +11.35% | 1.37 | +0.18R | 10.8% | **FAIL** | `RESEARCH_GRAVEYARD` | `SUPERSEDED_BY_V3` | **YES** |
| | V3 | `strat_mean_reversion_v3` | `strat_mean_reversion_v2` | `6614319220e49c05824e88bdbc0ab1f7dbb7b4cd0e129535aa6f9b70cc1a8624` | +20.46% | 1.54 | +0.28R | 14.2% | **FAIL** | `RESEARCH_GRAVEYARD` | `AUTHORITATIVE_CORRECTED` | **YES** |

---

## RECLASSIFICATION RULES
1. **`ORIGINAL_REPORTED_RESULT`**: Results recorded in early milestone completion reports prior to discovering engineering defects (e.g. pre-M3B.2.1 zero-quantity defect runs).
2. **`SUPERSEDED_RESULT`**: Historical runs whose code or parameters were superseded by subsequent corrected reruns.
3. **`AUTHORITATIVE_CORRECTED_RESULT`**: The final, verified backtest runs under `EndOfBacktestPolicy.FORCE_CLOSE` with exact accounting reconciliation ($\le ₹0.0001$).
