# TRADECRAFT PLATFORM OVERVIEW & CORE PHILOSOPHIES

## 1. Executive Summary
TradeCraft is an institutional quantitative research and algorithmic trading platform engineered specifically for Indian equities (NSE NIFTY 50, NIFTY 100, NIFTY 200, NIFTY 250, NIFTY 500). The platform eliminates survivorship bias, look-ahead bias, and overfitting by combining point-in-time universe management, cryptographic experiment tracking, an institutional alpha library, and zero-tolerance double-entry cash accounting.

---

## 2. Core Operational Philosophies

### Scientific Anti-Overfitting Discipline
- **Single DEVELOPMENT Backtest Policy**: Exactly ONE backtest execution is permitted on the DEVELOPMENT dataset per hypothesis. Grid searches, parameter tuning, and indicator sweeps are strictly prohibited.
- **Pre-Registration Lock**: Hypotheses must be pre-registered into `HypothesisRegistry` with pre-declared quantitative falsification criteria before writing strategy code.
- **Sealed Datasets**: Validation (`2022-01-01` $\rightarrow$ `2024-06-30`) and Final Test (`2024-07-01` $\rightarrow$ `2026-07-28`) datasets remain 100% sealed until pre-registered DEVELOPMENT criteria are met and formally approved.
- **Research Graveyard Protection**: Failed strategy lineages are permanently locked into the Research Graveyard. Novelty engines automatically reject future proposals with token similarity $> 0.35$ against Graveyard lineages.

### Institutional Accounting & Data Integrity
- **Zero-Tolerance Accounting**: Double-entry cash accounting enforces exact tracking of cash, position market value, realized P&L, STT, exchange charges, and brokerage with $₹0.0000$ residual error.
- **Point-in-Time Gating**: All market data, universe membership, corporate actions, and features are served strictly via `DataPortal` and `UniverseAPI` with clock date boundary checks.
