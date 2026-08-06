# C3R.0 — CANDIDATE ALPHA RESEARCH BACKLOG

> **BACKLOG CAPACITY**: **`35 Candidate Alpha Hypotheses Registered (ALPHA-014 through ALPHA-048)`**

---

## 1. INSTITUTIONAL HYPOTHESIS CARDS (TOP 5 CANDIDATES)

### 1.1 ALPHA-015 — Dual-Momentum Relative Strength & Sector Leadership
- **Alpha ID**: `ALPHA-015`
- **Category**: Relative Strength & Momentum
- **Economic Mechanism**: Equities exhibiting both absolute trend momentum and relative strength versus sector benchmarks experience sustained institutional capital inflows driven by momentum mandate fund allocations.
- **Behavioral Basis**: Herding behavior and performance chasing by institutional asset managers.
- **Academic Support**: Strong (Jegadeesh & Titman 1993; Antonacci 2014)
- **Research Maturity**: Well-Studied
- **Implementation Originality**: Standard Architecture
- **Falsification Criteria**: Profit Factor < 1.25, Sharpe < 0.55, CAGR < 10.0%, Max Drawdown > 25.0%.
- **Data Requirements**: OHLCV (Available ✅), Volume (Available ✅), Index Constituents (Available ✅). Feasibility: **100% FEASIBLE**.
- **Holding Period & Turnover**: 30 to 60 sessions; Low-Medium Turnover.
- **Prioritization Score**: **45.5** (Rank #1)

---

### 1.2 ALPHA-014 — Multi-Factor PEAD with Market Regime & Volume Confirmation
- **Alpha ID**: `ALPHA-014`
- **Category**: PEAD & Multi-Factor Synergy
- **Economic Mechanism**: Institutional investors accumulate large-cap positions over 20-40 sessions following positive disclosures due to execution liquidity constraints. Adding market trend (SMA-200) and volume confirmation filters out false breakout whipsaws.
- **Behavioral Basis**: Delayed information diffusion and institutional execution pacing in large-cap equities.
- **Academic Support**: Strong (Bernard & Thomas 1989; Chan, Jegadeesh, Lakonishok 1996)
- **Research Maturity**: Well-Studied
- **Implementation Originality**: Custom Combination (PEAD + Market Regime + Volume Expansion Filter)
- **Falsification Criteria**: Profit Factor < 1.30, Sharpe < 0.60, CAGR < 12.0%, Alpha disappears after standard fees + 5 bps slippage.
- **Data Requirements**: OHLCV (Available ✅), Volume (Available ✅), Index Constituents (Available ✅), Earnings Disclosure Proxy (Available ✅). Feasibility: **FEASIBLE WITH PLATFORM**.
- **Holding Period & Turnover**: 20 to 40 sessions; Medium Turnover.
- **Prioritization Score**: **44.0** (Rank #2)

---

### 1.3 ALPHA-018 — Volatility Compression Keltner-Bollinger Squeeze
- **Alpha ID**: `ALPHA-018`
- **Category**: Volatility Expansion / Squeeze
- **Economic Mechanism**: Periods of extreme volatility contraction are systematically followed by volatility expansion as market participants re-price asset risk upon new catalyst arrival.
- **Behavioral Basis**: Investor apathy during low-volatility consolidation followed by FOMO chasing during expansion.
- **Academic Support**: Moderate (Carter 2005; Bollinger 2001)
- **Research Maturity**: Moderate
- **Implementation Originality**: Standard Architecture
- **Falsification Criteria**: Profit Factor < 1.25, Sharpe < 0.50, CAGR < 9.0%.
- **Data Requirements**: OHLCV (Available ✅), Volume (Available ✅). Feasibility: **100% FEASIBLE**.
- **Holding Period & Turnover**: 10 to 25 sessions; Medium-High Turnover.
- **Prioritization Score**: **39.5** (Rank #3)

---

### 1.4 ALPHA-017 — Institutional Volume Breakout & Delivery Accumulation
- **Alpha ID**: `ALPHA-017`
- **Category**: Volume & Order Flow Anomalies
- **Economic Mechanism**: Abnormal volume expansion accompanied by high delivery volume percentage reflects institutional position building prior to major price discovery.
- **Behavioral Basis**: Informed institutional order flow absorbing retail supply.
- **Academic Support**: Moderate (Gunduz 2018; Blume, Easley, O'Hara 1994)
- **Research Maturity**: Moderate
- **Implementation Originality**: Custom Combination
- **Falsification Criteria**: Profit Factor < 1.30, Sharpe < 0.60, CAGR < 12.0%.
- **Data Requirements**: OHLCV (Available ✅), Delivery Volume (Requires Delivery Feed ⚠️). Feasibility: **REQUIRES DELIVERY DATA**.
- **Holding Period & Turnover**: 15 to 30 sessions; High Turnover.
- **Prioritization Score**: **38.5** (Rank #4)

---

### 1.5 ALPHA-019 — Cross-Sectional Short-Term Reversal & Oversold Bounce
- **Alpha ID**: `ALPHA-019`
- **Category**: Mean Reversion
- **Economic Mechanism**: Short-term overreaction to non-fundamental news causes temporary price dislocations, which revert to mean as liquidity providers earn market-making spreads.
- **Behavioral Basis**: Investor panic and liquidity provider inventory constraints.
- **Academic Support**: Strong (Jegadeesh 1990; Lehmann 1990)
- **Research Maturity**: Well-Studied
- **Implementation Originality**: Standard Architecture
- **Falsification Criteria**: Profit Factor < 1.20, Sharpe < 0.45, Alpha destroyed by transaction fees/slippage.
- **Data Requirements**: OHLCV (Available ✅), Volume (Available ✅). Feasibility: **100% FEASIBLE**.
- **Holding Period & Turnover**: 3 to 10 sessions; Very High Turnover.
- **Prioritization Score**: **37.5** (Rank #5)
