# FEATURE DEPENDENCY DERIVATION GRAPH

```mermaid
flowchart TD
    RP["Raw Prices & Volume (OHLCV)"] --> RET["Returns & Price Changes"]
    RP --> MA["Moving Averages (SMA, EMA)"]
    RP --> VOL["Volatility (ATR, Standard Dev)"]

    RET --> MOM["Momentum Factors (RSI, ROC, Relative Strength)"]
    MA --> RS["Relative Strength Rank (NIFTY 250)"]
    VOL --> LIQ["Liquidity & Volume Turnover Filters"]

    MOM --> CF["Composite Factors"]
    RS --> CF
    VOL --> CF

    CF --> REG["Market Regime Classifier"]
    CF --> STRAT["Strategy Intent Engine"]
```

## Lineage Record Schema
Every feature calculation tracks:
$$\text{Feature UUID} \longrightarrow (\text{Depends On}, \text{Raw Features}, \text{Dataset Version}, \text{Corporate Action Version}, \text{Membership Version})$$
