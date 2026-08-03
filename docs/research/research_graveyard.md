# TRADECRAFT PERMANENT RESEARCH GRAVEYARD

> **IMMUTABLE GRAVEYARD REGISTRY**: Formal record of all abandoned strategy families, rejected hypotheses, and empirical failure mechanisms.

---

## 1. GRAVEYARD ENTRY: TREND PULLBACK FAMILY (`strat_trend_pullback`)

- **Parent Lineage**: V1 $\rightarrow$ V2 $\rightarrow$ `ABANDON_FAMILY`
- **Believed Edge**: Stocks in medium-term uptrends (Close > SMA50) experiencing orderly pullbacks toward EMA20 baseline and subsequent daily price resumption offer trend continuation edge.
- **Empirical Failure Mechanism**: **`NEGATIVE_GROSS_EDGE`** (Gross P&L -₹159.48k, Net P&L -₹199.35k, Return -19.94%).
- **Why It Failed**: Structural trend pullbacks in NIFTY 50 large-caps suffer high regime dependency and false resumption triggers during sideways/bearish markets. The strategy lost money across all 6 years prior to transaction fees.
- **Rules Prohibiting Disguised Retries**:
  - No future strategy may use SMA50 pullback + EMA20 resumption triggers on NIFTY 50.
  - Changing EMA/SMA lookback periods or RSI filters does NOT constitute a new hypothesis.

---

## 2. GRAVEYARD ENTRY: MOMENTUM RELATIVE STRENGTH FAMILY (`strat_momentum_rs`)

- **Parent Lineage**: V1 $\rightarrow$ V2 $\rightarrow$ `ABANDON_FAMILY`
- **Believed Edge**: Stocks ranking in the top 25th percentile of 63-day relative strength performance in bullish markets exhibit momentum continuation.
- **Empirical Failure Mechanism**: **`NEGATIVE_GROSS_EDGE`** (Gross P&L -₹24.48k, Net P&L -₹45.06k, Return -4.51%).
- **Why It Failed**: Cross-sectional momentum ranking over a 63-day lookback without sector neutralization suffers severe whipsaws during market sector rotations.
- **Rules Prohibiting Disguised Retries**:
  - No future strategy may use raw 63-day unadjusted price momentum ranking on NIFTY 50.
  - Altering the lookback from 63 to 50 or 75 days does NOT constitute a new hypothesis.

---

## 3. GRAVEYARD ENTRY: BREAKOUT CONFIRMATION FAMILY (`strat_breakout_confirm`)

- **Parent Lineage**: V1 $\rightarrow$ V2 $\rightarrow$ V3 $\rightarrow$ `ABANDON_FAMILY`
- **Believed Edge**: Stocks emerging from 20-day Donchian channel consolidations with volume expansion (RVOL $\ge 1.2$) exhibit trend continuation momentum.
- **Empirical Failure Mechanism**: **`FRICTION_EROSION`** & **`LOW_WIN_RATE`** (V3 Net Return +7.66%, PF 1.18, Win Rate 12.5% vs 35.0% gate requirement).
- **Why It Failed**: Intra-day breakouts in Indian delivery equity suffer frequent false breakouts. Transaction costs (STT + GST + DP charges) and slippage consume nearly 50% of gross breakout profits.
- **Rules Prohibiting Disguised Retries**:
  - No future strategy may use 20-day Donchian channel breakouts with RVOL filters on NIFTY 50.
  - Adjusting consolidation width or confirmation sessions does NOT constitute a new hypothesis.

---

## 4. GRAVEYARD ENTRY: MEAN REVERSION FAMILY (`strat_mean_reversion`)

- **Parent Lineage**: V1 $\rightarrow$ V2 $\rightarrow$ V3 $\rightarrow$ `ABANDON_FAMILY`
- **Believed Edge**: Stocks in structural uptrends (Close > SMA200) experiencing short-term oversold dips (RSI(5) $\le 35.0$) with 1.0 ATR displacement and bullish reversal candles exhibit rapid mean reversion.
- **Empirical Failure Mechanism**: **`LOW_WIN_RATE`** (V3 Net Return +20.46%, PF 1.54, Expectancy +0.28R, Win Rate 14.2% vs 35.0% gate requirement).
- **Why It Failed**: While Mean Reversion V3 achieved strong gross (+₹232.4k) and net (+₹204.6k) P&L with positive expectancy (+0.28R), its low win rate (14.2%) failed the pre-declared 35.0% Win Rate gate threshold. Under non-override research discipline, the strategy is abandoned.
- **Rules Prohibiting Disguised Retries**:
  - Mean Reversion V3 CANNOT be rescued by lowering the Win Rate gate post-hoc or running on Validation.
  - The family is locked in the Graveyard for Research Cycle 1.
