# C3R.1.5 — STRATEGY DESIGN REVIEW & ASSUMPTION REGISTER (ALPHA-015)

> **DOCUMENT TYPE**: **`STRATEGY DESIGN REVIEW & ASSUMPTION REGISTER`**  
> **TARGET HYPOTHESIS**: **`ALPHA-015` — Dual-Momentum Relative Strength & Sector Leadership**  
> **SPECIFICATION VERSION**: **`0.95 (Pre-Engineering Draft)`**  
> **HYPOTHESIS READINESS SCORE**: **`25 / 30`**  
> **GOVERNANCE STATUS**: **`APPROVED FOR DATA FEASIBILITY AUDIT (C3R.2)`**

---

## 1. DECISION FLOW ARCHITECTURE & STRATEGY DIAGRAM

```mermaid
graph TD
    A["1. Benchmark Universe (NIFTY 50 / NIFTY 500)"] --> B["2. Liquidity & Turnover Filter"]
    B --> C["3. Market Regime Guard (Absolute Momentum)"]
    C -->|Regime Pass| D["4. Sector Relative Strength Ranking"]
    C -->|Regime Fail (Cash)| J["10. Hold 100% Cash / Liquid Risk-Off"]
    D --> E["5. Cross-Sectional Stock RS Ranking"]
    E --> F["6. Volatility Budgeting & Risk Sizing"]
    F --> G["7. Portfolio Construction (Max 10 Holdings)"]
    G --> H["8. Friction Drag Modeling & Order Execution"]
    H --> I["9. Dynamic Trailing Risk Management & Exits"]
    I --> J
```

---

## 2. ARCHITECTURAL DECISION LOG

| Decision ID | Choice | Alternatives Considered | Rationale | Supporting Evidence |
| :---: | :--- | :--- | :--- | :--- |
| **`DEC-001`** | **Long-Only Equities Portfolio** | Long-Short, Options Overlay | Indian cash equity delivery market does not support easy short-holding without borrow fees. | Indian Equity Market Microstructure Rules |
| **`DEC-002`** | **Max 10 Positions Constraint** | 5 Positions, 20 Positions, Market-Cap Weight | Balances idiosyncratic risk diversification against portfolio turnover friction. | Antonacci (2014); Jegadeesh & Titman (1993) |
| **`DEC-003`** | **NIFTY 50 / NIFTY 500 Benchmark** | Small-Cap Microcaps, All NSE | Guarantees execution liquidity and robust point-in-time constituent tracking in `tradecraft.db`. | TradeCraft DataPortal Verification Audit |

---

## 3. INSTITUTIONAL ASSUMPTION REGISTER

| Assumption ID | Core Assumption | Why It Exists | Failure Scenario | Verification Method |
| :---: | :--- | :--- | :--- | :--- |
| **`ASM-001`** | **Relative Strength Persistence** | Institutional capital flows sluggishly into top-performing equities over 30–60 session horizons. | Rapid sector rotation causes high whipsaws and win rate $< 35\%$. | Cross-sectional trend persistence audit in C3R.2 / C3D.0. |
| **`ASM-002`** | **Point-in-Time Universe Integrity** | DataPortal dynamically reconstructs historical index constituents on every bar. | Survivorship bias distorts historical returns if delisted stocks are omitted. | DataPortal point-in-time constituent audit in C3R.2. |
| **`ASM-003`** | **Friction Realism** | Indian equity delivery costs (STT, GST, SEBI fees) + 5 bps fixed slippage bound friction drag. | Excess turnover erodes $> 50\%$ of gross alpha. | Friction sensitivity analysis in C3R.3 and C3D.0. |
| **`ASM-004`** | **Regime Guard Effectiveness** | Absolute momentum filter transitions portfolio to cash during macro downtrends. | False crash exits trigger during minor bull pullbacks. | Macro trend guard simulation in C3R.3 / C3D.0. |

---

## 4. RESEARCH INTEGRITY COMMITMENTS (NON-OPTIMIZATION BOUNDS)

1. **No In-Sample Lookback Curve-Fitting**: Pre-registered lookbacks (e.g. 6-month vs 12-month) will be evaluated without fine-tuning day-by-day parameters (e.g. trying 127 vs 128 days).
2. **No Arbitrary Indicator Toggling**: No ad-hoc technical indicators (RSI, MACD, Stochastic) will be added post-hoc to "patch" losing trades.
3. **Locked Risk Management**: ATR trailing stop multipliers will be locked prior to Development backtest execution.

---

## 5. STAGE KILL CRITERIA (DATA & RESEARCH GATE)

- **C3R.2 Data Feasibility Audit Gate**: If point-in-time constituent history or sector benchmark data cannot be fully reconstructed in `tradecraft.db`, mark project as **`BLOCKED_PENDING_DATA`** rather than mutating the hypothesis.
- **C3R.3 Engineering Design Gate**: If transaction cost modeling proves expected turnover erodes $> 50\%$ of expected gross edge, mark project as **`UNFEASIBLE_FRICTION`** and halt engineering.

---

## 6. STRUCTURED RESEARCH QUESTIONS REGISTER

| Question ID | Formal Research Question | Planned Experiment |
| :---: | :--- | :--- |
| **`Q-001`** | Is sector-level relative strength superior to stock-level momentum alone? | Compare single-factor stock RS against dual sector-stock RS in C3R.3 / C3D.0. |
| **`Q-002`** | Does an absolute momentum market trend guard significantly reduce max drawdown? | Simulate strategy with vs without absolute trend filter during market crash periods in C3D.0. |
| **`Q-003`** | Does equal-weight construction outperform volatility-inverse weighting? | Compare equal-weighted 10% sizing against inverse-volatility weighting in C3R.3. |
| **`Q-004`** | Is bi-weekly rebalancing more net-profitable than monthly rebalancing after costs? | Evaluate bi-weekly vs monthly rebalancing frequency in C3R.3. |

---

## 7. GOVERNANCE STATUS & NEXT AUTHORIZED MILESTONE

- **Specification Status**: **Version 0.95 (Pre-Engineering Draft)**
- **Hypothesis Readiness Score**: **`25 / 30`**
- **HARD STOP ENFORCED**: Zero strategy code written, zero backtests run, `FINAL TEST` dataset 100% SEALED (`FINAL_TEST_ACCESS_COUNT = 0`).
- **Next Authorized Milestone**: **Milestone C3R.2 — Data Feasibility Audit for ALPHA-015**.
