"""Pure Technical Indicators for Feature Engineering.

Functions operate on pandas Series / numpy arrays and are strictly
stateless and side-effect free. No look-ahead is introduced by construction.

Each function documents:
- Economic/market intuition
- Formula
- Required lookback
- Known limitations
- Point-in-time behaviour

Functions return NaN for positions with insufficient lookback data.
"""

import numpy as np
import pandas as pd
from decimal import Decimal
from typing import Any

# ---------------------------------------------------------------------------
# TREND family
# ---------------------------------------------------------------------------


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average.

    Formula: SMA(t) = mean(series[t-period+1 : t+1])
    Intuition: Smooths price noise to reveal underlying trend direction.
    Lookback: `period` bars for first valid value.
    Limitations: Lags price by approximately period/2 bars.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average.

    Formula: EMA(t) = α * price(t) + (1-α) * EMA(t-1), where α = 2/(period+1)
    Intuition: More responsive to recent prices than SMA.
    Lookback: `period` bars for first valid value.
    Limitations: Slightly more prone to whipsaws than SMA.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    return series.ewm(span=period, min_periods=period, adjust=False).mean()


def ma_slope(series: pd.Series, ma_period: int, slope_period: int = 5) -> pd.Series:
    """Moving Average Slope (rate of change of MA).

    Formula: (SMA[t] - SMA[t - slope_period]) / SMA[t - slope_period]
    Intuition: Positive slope confirms strengthening trend; negative slope warns of deterioration.
    Lookback: ma_period + slope_period bars.
    Limitations: Small slope values near zero may be indistinguishable from noise.
    """
    if ma_period <= 0 or slope_period <= 0:
        raise ValueError("Periods must be positive")
    ma = sma(series, ma_period)
    prev_ma = ma.shift(slope_period)
    return (ma - prev_ma) / prev_ma


def price_to_ma_ratio(series: pd.Series, period: int) -> pd.Series:
    """Price deviation from Moving Average as percentage.

    Formula: (close - SMA) / SMA
    Intuition: Measures extension from trend anchor. Extreme values suggest overextension.
    Lookback: `period` bars.
    Limitations: Not normalised by volatility. A 5% deviation means different things in
    different volatility regimes.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    ma = sma(series, period)
    return (series - ma) / ma


def trend_structure(high: pd.Series, low: pd.Series, lookback: int = 10) -> pd.Series:
    """Higher-High / Higher-Low structure score.

    Formula: Counts how many of the last `lookback` bars have higher highs AND higher
    lows compared to the bar before them, minus bars with lower highs AND lower lows.
    Result normalised to [-1, +1].
    Intuition: +1 = perfect uptrend structure, -1 = perfect downtrend, 0 = mixed.
    Lookback: lookback + 1 bars.
    Limitations: Binary counting; does not weight by magnitude of moves.
    """
    if lookback <= 0:
        raise ValueError("Lookback must be positive")
    hh = (high > high.shift(1)).astype(int)
    hl = (low > low.shift(1)).astype(int)
    lh = (high < high.shift(1)).astype(int)
    ll = (low < low.shift(1)).astype(int)

    up_score = (hh & hl).rolling(window=lookback, min_periods=lookback).sum()
    down_score = (lh & ll).rolling(window=lookback, min_periods=lookback).sum()
    return (up_score - down_score) / lookback


# ---------------------------------------------------------------------------
# MOMENTUM family
# ---------------------------------------------------------------------------


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder smoothing).

    Formula: RSI = 100 - 100 / (1 + RS), RS = avg_gain / avg_loss over `period` bars.
    Uses Wilder's exponential smoothing (α = 1/period).
    Intuition: Measures speed and magnitude of directional price movement.
    Values > 70 traditionally considered overbought, < 30 oversold.
    Lookback: period + 1 bars (for first delta).
    Limitations: Can remain extreme in strong trends. Not a standalone buy/sell signal.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    result = 100.0 - (100.0 / (1.0 + rs))
    # Handle division by zero (all gains, no losses) — but preserve NaN for insufficient data
    zero_loss_mask = (avg_loss == 0) & avg_gain.notna()
    result = result.where(~zero_loss_mask, 100.0)
    # Ensure NaN where either avg is NaN (insufficient lookback)
    result = result.where(avg_gain.notna(), np.nan)
    return result


def roc(series: pd.Series, period: int = 20) -> pd.Series:
    """Rate of Change (percentage).

    Formula: ROC = (close[t] - close[t-period]) / close[t-period] * 100
    Intuition: Simple momentum measure. Positive = price rising over period.
    Lookback: `period` bars.
    Limitations: Sensitive to single comparison bar. Does not account for path.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    prev = series.shift(period)
    return ((series - prev) / prev) * 100


def multi_period_return(series: pd.Series, periods: list[int] | None = None) -> pd.DataFrame:
    """Multi-period returns for momentum persistence analysis.

    Formula: Returns for each period = (close[t] / close[t-p]) - 1
    Intuition: Persistent positive returns across multiple timeframes suggest genuine momentum.
    Limitations: Each period requires its own lookback.
    """
    if periods is None:
        periods = [5, 10, 20, 60]
    results = {}
    for p in periods:
        if p <= 0:
            raise ValueError("Period must be positive")
        prev = series.shift(p)
        results[f"return_{p}d"] = (series / prev) - 1
    return pd.DataFrame(results, index=series.index)


# ---------------------------------------------------------------------------
# VOLATILITY family
# ---------------------------------------------------------------------------


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range (ATR).

    Formula: ATR = SMA(TrueRange, period) where TR = max(H-L, |H-prevC|, |L-prevC|)
    Intuition: Measures average daily price range including gaps. Used for stop placement
    and volatility normalisation.
    Lookback: period + 1 bars (for previous close).
    Limitations: Absolute value depends on price level. Use atr_percent for cross-security comparison.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def atr_percent(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ATR as percentage of closing price.

    Formula: ATR% = (ATR / close) * 100
    Intuition: Volatility normalised by price level. Enables cross-security volatility comparison.
    Lookback: period + 1 bars.
    Limitations: Sensitive to ATR smoothing choice.
    """
    atr_val = atr(high, low, close, period)
    return (atr_val / close) * 100


def rolling_volatility(series: pd.Series, period: int = 20) -> pd.Series:
    """Annualised rolling volatility of daily returns.

    Formula: std(daily_returns, period) * sqrt(252)
    Intuition: Recent annualised volatility for regime classification and risk assessment.
    Lookback: period + 1 bars.
    Limitations: Assumes normal distribution. Short windows may not capture full volatility cycles.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    returns = series.pct_change()
    return returns.rolling(window=period, min_periods=period).std() * np.sqrt(252)


def volatility_expansion_ratio(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    short_period: int = 5,
    long_period: int = 20,
) -> pd.Series:
    """Short-term ATR relative to long-term ATR.

    Formula: ATR(short) / ATR(long)
    Intuition: Values > 1 indicate volatility expansion; < 1 indicate contraction.
    Lookback: long_period + 1 bars.
    Limitations: Ratio can be misleading when both ATRs are very small.
    """
    short_atr = atr(high, low, close, short_period)
    long_atr = atr(high, low, close, long_period)
    return short_atr / long_atr


# ---------------------------------------------------------------------------
# VOLUME / LIQUIDITY family
# ---------------------------------------------------------------------------


def avg_volume(volume: pd.Series, period: int = 20) -> pd.Series:
    """Average trading volume over period.

    Formula: SMA(volume, period)
    Intuition: Baseline volume for relative volume and liquidity assessment.
    Lookback: `period` bars.
    Limitations: Does not account for traded value.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    return volume.rolling(window=period, min_periods=period).mean()


def avg_traded_value(close: pd.Series, volume: pd.Series, period: int = 20) -> pd.Series:
    """Average daily traded value (close * volume) over period.

    Formula: SMA(close * volume, period)
    Intuition: Primary liquidity measure for eligibility screening. Captures both price
    and volume in a single INR turnover metric.
    Lookback: `period` bars.
    Limitations: Uses closing price as proxy for VWAP.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    daily_value = close * volume
    return daily_value.rolling(window=period, min_periods=period).mean()


def relative_volume(volume: pd.Series, period: int = 20) -> pd.Series:
    """Relative volume (current volume / average volume).

    Formula: volume[t] / SMA(volume, period)
    Intuition: Values > 1.5 indicate significant above-average activity.
    Used to confirm breakouts and institutional participation.
    Lookback: `period` bars.
    Limitations: Day-of-week and expiry effects can inflate RVOL.
    """
    avg_vol = avg_volume(volume, period)
    return volume / avg_vol


def volume_expansion(volume: pd.Series, short_period: int = 5, long_period: int = 20) -> pd.Series:
    """Short-term average volume relative to long-term average.

    Formula: SMA(volume, short) / SMA(volume, long)
    Intuition: Rising values indicate growing market interest.
    Lookback: long_period bars.
    Limitations: Cannot distinguish buying from selling volume with daily data.
    """
    short_avg = avg_volume(volume, short_period)
    long_avg = avg_volume(volume, long_period)
    return short_avg / long_avg


# ---------------------------------------------------------------------------
# BREAKOUT / PRICE STRUCTURE family
# ---------------------------------------------------------------------------


def donchian_channel(
    high: pd.Series, low: pd.Series, period: int = 20
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Donchian Channel (Upper, Middle, Lower).

    Formula: Upper = max(high, period), Lower = min(low, period), Middle = (Upper+Lower)/2
    Intuition: Price channel capturing the full range. Breakout above upper band may signal
    trend continuation; touch of lower band may indicate support.
    Lookback: `period` bars.
    Limitations: Simple range measure. Does not distinguish consolidation from trending ranges.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    upper = high.rolling(window=period, min_periods=period).max()
    lower = low.rolling(window=period, min_periods=period).min()
    middle = (upper + lower) / 2.0
    return upper, middle, lower


def breakout_distance(close: pd.Series, high: pd.Series, period: int = 20) -> pd.Series:
    """Distance from Donchian upper channel as percentage.

    Formula: (close - max(high, period)) / max(high, period) * 100
    Intuition: Near-zero or positive values indicate breakout proximity or confirmed breakout.
    Negative values indicate how far price is from breaking out.
    Lookback: `period` bars.
    Limitations: Does not account for volume or trend quality.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    upper = high.rolling(window=period, min_periods=period).max()
    return (close - upper) / upper * 100


def consolidation_range(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20
) -> pd.Series:
    """Consolidation range as ATR-normalised channel width.

    Formula: (max(high, period) - min(low, period)) / ATR(period)
    Intuition: Low values indicate tight consolidation (potential breakout setup).
    High values indicate wide, trending ranges.
    Lookback: `period` + 1 bars (for ATR prev close).
    Limitations: ATR denominator may amplify noise when volatility is very low.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    upper = high.rolling(window=period, min_periods=period).max()
    lower = low.rolling(window=period, min_periods=period).min()
    atr_val = atr(high, low, close, period)
    return (upper - lower) / atr_val


def distance_from_high(close: pd.Series, high: pd.Series, period: int = 252) -> pd.Series:
    """Distance from N-period high as percentage.

    Formula: (close - max(high, period)) / max(high, period) * 100
    Intuition: Proximity to peak. Near-zero indicates strength; large negatives indicate weakness.
    Lookback: `period` bars.
    Limitations: Requires sufficient history. Not useful for recently listed securities.
    """
    if period <= 0:
        raise ValueError("Period must be positive")
    rolling_high = high.rolling(window=period, min_periods=period).max()
    return (close - rolling_high) / rolling_high * 100


# ---------------------------------------------------------------------------
# SUPPORT / RESISTANCE family
# ---------------------------------------------------------------------------


def find_pivot_highs(high: pd.Series, left_bars: int = 5, right_bars: int = 5) -> pd.Series:
    """Identify pivot highs with confirmation delay.

    A bar at index i is a pivot high if high[i] is strictly greater than
    high[j] for all j in [i-left_bars, i+right_bars] (excluding i).

    CRITICAL POINT-IN-TIME SEMANTICS:
    The pivot at bar i is NOT available until bar i + right_bars has been observed.
    The returned Series has NaN for non-pivot bars and the pivot high value at the
    CONFIRMATION date (i + right_bars), not at the pivot date itself.

    This prevents look-ahead: a strategy running at date T can only see pivots
    that were confirmed on or before T.

    Returns:
        pd.Series with pivot high values at their confirmation dates.
    """
    if left_bars <= 0 or right_bars <= 0:
        raise ValueError("left_bars and right_bars must be positive")

    result = pd.Series(np.nan, index=high.index)
    values = high.values

    for i in range(left_bars, len(values) - right_bars):
        is_pivot = True
        for j in range(i - left_bars, i + right_bars + 1):
            if j == i:
                continue
            if values[j] >= values[i]:
                is_pivot = False
                break
        if is_pivot:
            # Place at confirmation date (i + right_bars), NOT at pivot date (i)
            confirmation_idx = i + right_bars
            if confirmation_idx < len(values):
                result.iloc[confirmation_idx] = values[i]

    return result


def find_pivot_lows(low: pd.Series, left_bars: int = 5, right_bars: int = 5) -> pd.Series:
    """Identify pivot lows with confirmation delay.

    Same point-in-time semantics as find_pivot_highs but for troughs.
    The pivot low at bar i is confirmed and available only at bar i + right_bars.

    Returns:
        pd.Series with pivot low values at their confirmation dates.
    """
    if left_bars <= 0 or right_bars <= 0:
        raise ValueError("left_bars and right_bars must be positive")

    result = pd.Series(np.nan, index=low.index)
    values = low.values

    for i in range(left_bars, len(values) - right_bars):
        is_pivot = True
        for j in range(i - left_bars, i + right_bars + 1):
            if j == i:
                continue
            if values[j] <= values[i]:
                is_pivot = False
                break
        if is_pivot:
            confirmation_idx = i + right_bars
            if confirmation_idx < len(values):
                result.iloc[confirmation_idx] = values[i]

    return result


def nearest_support_distance_atr(
    close: pd.Series,
    low: pd.Series,
    high: pd.Series,
    atr_series: pd.Series,
    left_bars: int = 5,
    right_bars: int = 5,
) -> pd.Series:
    """Distance to nearest confirmed pivot low, normalised by ATR.

    Formula: (close[t] - nearest_confirmed_pivot_low) / ATR[t]
    Only uses pivot lows that were confirmed on or before date t.

    Returns:
        pd.Series of ATR-normalised distance to nearest support.
        NaN if no confirmed pivot low exists yet.
    """
    confirmed_pivots = find_pivot_lows(low, left_bars, right_bars)
    result = pd.Series(np.nan, index=close.index)

    # Track the most recent confirmed pivot low value
    last_pivot_low = np.nan
    for i in range(len(close)):
        if not np.isnan(confirmed_pivots.iloc[i]):
            last_pivot_low = confirmed_pivots.iloc[i]

        if not np.isnan(last_pivot_low) and not np.isnan(atr_series.iloc[i]):
            atr_val = atr_series.iloc[i]
            if atr_val > 0:
                result.iloc[i] = (close.iloc[i] - last_pivot_low) / atr_val

    return result


# ---------------------------------------------------------------------------
# List-based wrapper functions for strategies
# ---------------------------------------------------------------------------


def calculate_sma(data: list[Any], period: int) -> list[Decimal | None]:
    s = pd.Series([float(x) for x in data])
    res = sma(s, period)
    return [Decimal(str(v)) if not np.isnan(v) else None for v in res]


def calculate_rsi(data: list[Any], period: int = 14) -> list[Decimal | None]:
    s = pd.Series([float(x) for x in data])
    res = rsi(s, period)
    return [Decimal(str(v)) if not np.isnan(v) else None for v in res]


def calculate_atr(highs: list[Any], lows: list[Any], closes: list[Any], period: int = 14) -> list[Decimal | None]:
    h = pd.Series([float(x) for x in highs])
    l = pd.Series([float(x) for x in lows])
    c = pd.Series([float(x) for x in closes])
    res = atr(h, l, c, period)
    return [Decimal(str(v)) if not np.isnan(v) else None for v in res]


def calculate_rvol(volumes: list[Any], period: int = 20) -> list[Decimal | None]:
    v = pd.Series([float(x) for x in volumes])
    res = relative_volume(v, period)
    return [Decimal(str(v_val)) if not np.isnan(v_val) else None for v_val in res]


def calculate_roc(data: list[Any], period: int = 12) -> list[Decimal | None]:
    s = pd.Series([float(x) for x in data])
    res = roc(s, period)
    return [Decimal(str(v)) if not np.isnan(v) else None for v in res]
