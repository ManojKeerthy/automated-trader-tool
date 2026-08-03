# FEATURE REGISTRY SPECIFICATION

The `FeatureRegistry` maintains immutable definitions for core quantitative features (`RSI`, `ATR`, `EMA`, `SMA`, `ADX`, `MACD`, `ROC`, `Relative Strength`, `Volatility`, `Liquidity`, `Sector Strength`, `Market Regime`).

Strategies consume registered features via the Research SDK and are prohibited from calculating technical indicators internally.
