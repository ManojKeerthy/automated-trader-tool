"""Pure Technical Indicators for Feature Engineering.

Functions operate on pandas Series / numpy arrays and are strictly
stateless and side-effect free. No look-ahead is introduced by construction.
"""

import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    if period <= 0:
        raise ValueError("Period must be positive")
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    if period <= 0:
        raise ValueError("Period must be positive")
    return series.ewm(span=period, adjust=False).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range (ATR)."""
    if period <= 0:
        raise ValueError("Period must be positive")
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def donchian_channel(
    high: pd.Series, low: pd.Series, period: int = 20
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Donchian Channel (Upper, Middle, Lower)."""
    if period <= 0:
        raise ValueError("Period must be positive")
    upper = high.rolling(window=period).max()
    lower = low.rolling(window=period).min()
    middle = (upper + lower) / 2.0
    return upper, middle, lower
