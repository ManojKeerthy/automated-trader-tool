"""Point-in-Time Feature Framework.

Design decisions per M3A approved amendments:
- Features are named, versioned, parameterized, reproducible, and point-in-time safe.
- Feature definitions record enough metadata to reproduce any computation.
- Derived feature values are computed deterministically on demand (no automatic persistence).
- Feature calculation at date T uses only information available at or before T.
- Insufficient lookback produces NaN rather than silently returning partial calculations.
"""

from __future__ import annotations

import uuid  # noqa: TC003
from dataclasses import dataclass, field
from datetime import date  # noqa: TC003
from typing import Any


@dataclass(frozen=True)
class FeatureDefinition:
    """Immutable metadata describing a single feature.

    Every feature definition records enough information to reproduce its
    calculation, including the formula methodology, required lookback,
    expected input series, and availability semantics.
    """

    name: str
    version: str
    family: str  # TREND, MOMENTUM, VOLATILITY, VOLUME, BREAKOUT, SUPPORT_RESISTANCE
    parameters: dict[str, Any] = field(default_factory=dict)
    required_lookback: int = 0  # Minimum bars of history needed for first valid value
    formula: str = ""  # Human-readable formula / methodology description
    input_series: list[str] = field(
        default_factory=list
    )  # e.g. ["close"], ["high", "low", "close"]
    intuition: str = ""  # Economic / market intuition for why this feature exists
    known_limitations: str = ""
    availability: str = "IMMEDIATE"  # IMMEDIATE or CONFIRMATION_REQUIRED

    @property
    def feature_id(self) -> str:
        """Unique identifier combining name and version."""
        return f"{self.name}_v{self.version}"


@dataclass(frozen=True)
class FeatureValue:
    """A single computed feature observation at a specific point in time."""

    feature_id: str
    instrument_id: uuid.UUID | None  # None for market-level features
    observation_date: date
    value: float | None  # None when insufficient lookback
    quality: str = "COMPUTED"  # COMPUTED, INSUFFICIENT_LOOKBACK, UNAVAILABLE


@dataclass
class FeatureSet:
    """A collection of feature values computed for a specific date and instrument."""

    instrument_id: uuid.UUID | None
    observation_date: date
    values: dict[str, FeatureValue] = field(default_factory=dict)

    def get(self, feature_id: str) -> float | None:
        """Get a feature value by feature_id, returning None if missing."""
        fv = self.values.get(feature_id)
        return fv.value if fv else None

    def has_sufficient_data(self, feature_id: str) -> bool:
        """Check if a feature was computed with sufficient lookback."""
        fv = self.values.get(feature_id)
        return fv is not None and fv.quality == "COMPUTED" and fv.value is not None


# ---------------------------------------------------------------------------
# Feature Registry — catalog of all defined features
# ---------------------------------------------------------------------------

# Trend features
SMA_20 = FeatureDefinition(
    name="sma_20",
    version="1.0",
    family="TREND",
    parameters={"period": 20},
    required_lookback=20,
    formula="SMA(close, 20) = mean of last 20 closing prices",
    input_series=["close"],
    intuition="Short-term trend direction indicator. Price above SMA suggests short-term uptrend.",
    known_limitations="Lags price by half the period. Whipsaws in sideways markets.",
)

SMA_50 = FeatureDefinition(
    name="sma_50",
    version="1.0",
    family="TREND",
    parameters={"period": 50},
    required_lookback=50,
    formula="SMA(close, 50) = mean of last 50 closing prices",
    input_series=["close"],
    intuition="Medium-term trend direction. Used for regime classification and trend-following filters.",
    known_limitations="Lags price significantly. Insensitive to recent sharp moves.",
)

SMA_200 = FeatureDefinition(
    name="sma_200",
    version="1.0",
    family="TREND",
    parameters={"period": 200},
    required_lookback=200,
    formula="SMA(close, 200) = mean of last 200 closing prices",
    input_series=["close"],
    intuition="Long-term trend direction. Classic bull/bear market divider.",
    known_limitations="Requires ~10 months of history. Very lagging.",
)

EMA_20 = FeatureDefinition(
    name="ema_20",
    version="1.0",
    family="TREND",
    parameters={"period": 20},
    required_lookback=20,
    formula="EMA(close, 20) = exponentially weighted moving average with span=20",
    input_series=["close"],
    intuition="Trend indicator more responsive to recent prices than SMA.",
    known_limitations="Slightly more prone to whipsaws than SMA.",
)

MA_SLOPE_50 = FeatureDefinition(
    name="ma_slope_50",
    version="1.0",
    family="TREND",
    parameters={"ma_period": 50, "slope_period": 5},
    required_lookback=55,
    formula="(SMA_50[T] - SMA_50[T-5]) / SMA_50[T-5], percentage change over slope_period bars",
    input_series=["close"],
    intuition="Rate of change of the 50-period MA. Positive slope confirms strengthening trend.",
    known_limitations="Small slope values may be noise.",
)

PRICE_TO_MA_50 = FeatureDefinition(
    name="price_to_ma_50",
    version="1.0",
    family="TREND",
    parameters={"period": 50},
    required_lookback=50,
    formula="(close - SMA_50) / SMA_50, expressed as percentage deviation",
    input_series=["close"],
    intuition="Measures how far price has moved from its trend anchor. Extreme values may indicate extension.",
    known_limitations="Not normalised by volatility.",
)

# Momentum features
RSI_14 = FeatureDefinition(
    name="rsi_14",
    version="1.0",
    family="MOMENTUM",
    parameters={"period": 14},
    required_lookback=15,  # 14 periods + 1 for first diff
    formula="RSI = 100 - 100 / (1 + avg_gain / avg_loss) over 14-period Wilder smoothing",
    input_series=["close"],
    intuition="Measures speed/magnitude of price changes. Values >70 overbought, <30 oversold.",
    known_limitations="Can remain extreme in strong trends. Not a standalone buy/sell signal.",
)

ROC_20 = FeatureDefinition(
    name="roc_20",
    version="1.0",
    family="MOMENTUM",
    parameters={"period": 20},
    required_lookback=20,
    formula="ROC = (close[T] - close[T-20]) / close[T-20] * 100",
    input_series=["close"],
    intuition="Simple 20-day price momentum. Positive values indicate upward price change.",
    known_limitations="Sensitive to the single comparison bar. Does not account for path.",
)

# Volatility features
ATR_14 = FeatureDefinition(
    name="atr_14",
    version="1.0",
    family="VOLATILITY",
    parameters={"period": 14},
    required_lookback=15,
    formula="ATR = SMA(TrueRange, 14) where TR = max(H-L, |H-prevC|, |L-prevC|)",
    input_series=["high", "low", "close"],
    intuition="Average daily price range. Measures absolute volatility for stop placement.",
    known_limitations="Absolute value depends on price level. Use ATR% for cross-security comparison.",
)

ATR_PERCENT_14 = FeatureDefinition(
    name="atr_percent_14",
    version="1.0",
    family="VOLATILITY",
    parameters={"period": 14},
    required_lookback=15,
    formula="ATR% = (ATR_14 / close) * 100",
    input_series=["high", "low", "close"],
    intuition="ATR normalised by price. Allows volatility comparison across different price levels.",
    known_limitations="Sensitive to ATR smoothing choice.",
)

ROLLING_VOLATILITY_20 = FeatureDefinition(
    name="rolling_volatility_20",
    version="1.0",
    family="VOLATILITY",
    parameters={"period": 20},
    required_lookback=21,
    formula="std(daily_returns, 20) * sqrt(252), annualised volatility over 20-bar window",
    input_series=["close"],
    intuition="Recent annualised volatility. Used for regime classification and position sizing context.",
    known_limitations="20-bar window may not capture full volatility cycles.",
)

# Volume/Liquidity features
AVG_VOLUME_20 = FeatureDefinition(
    name="avg_volume_20",
    version="1.0",
    family="VOLUME",
    parameters={"period": 20},
    required_lookback=20,
    formula="SMA(volume, 20) = mean of last 20 daily volumes",
    input_series=["volume"],
    intuition="Baseline daily volume for liquidity assessment and relative volume computation.",
    known_limitations="Does not account for traded value. Low-price high-volume is not necessarily liquid.",
)

AVG_TRADED_VALUE_20 = FeatureDefinition(
    name="avg_traded_value_20",
    version="1.0",
    family="VOLUME",
    parameters={"period": 20},
    required_lookback=20,
    formula="SMA(close * volume, 20) = mean of last 20 daily traded values",
    input_series=["close", "volume"],
    intuition="Average daily INR turnover. Primary liquidity measure for eligibility screening.",
    known_limitations="Uses closing price as proxy for VWAP. Actual intraday turnover may differ.",
)

RELATIVE_VOLUME = FeatureDefinition(
    name="relative_volume",
    version="1.0",
    family="VOLUME",
    parameters={"period": 20},
    required_lookback=20,
    formula="RVOL = volume[T] / SMA(volume, 20). Values > 1 indicate above-average activity.",
    input_series=["volume"],
    intuition="Volume relative to recent baseline. High RVOL may confirm breakouts or institutional activity.",
    known_limitations="Day-of-week and expiry effects can inflate RVOL. Single-bar measure.",
)

# Breakout / Price Structure features
DONCHIAN_20 = FeatureDefinition(
    name="donchian_20",
    version="1.0",
    family="BREAKOUT",
    parameters={"period": 20},
    required_lookback=20,
    formula="Upper = max(high, 20), Lower = min(low, 20), Middle = (Upper + Lower) / 2",
    input_series=["high", "low"],
    intuition="20-day price channel. Breakouts above upper band may signal trend continuation.",
    known_limitations="Simple range measure. Does not distinguish between consolidation and trending ranges.",
)

DISTANCE_FROM_52W_HIGH = FeatureDefinition(
    name="distance_from_52w_high",
    version="1.0",
    family="BREAKOUT",
    parameters={"period": 252},
    required_lookback=252,
    formula="(close - max(high, 252)) / max(high, 252) * 100, percentage distance from 52-week high",
    input_series=["high", "close"],
    intuition="Proximity to yearly peak. Near-zero values indicate strength; large negatives indicate weakness.",
    known_limitations="Requires ~1 year of history. Not useful for recently listed securities.",
)

# Support / Resistance features (with confirmation semantics)
PIVOT_HIGH = FeatureDefinition(
    name="pivot_high",
    version="1.0",
    family="SUPPORT_RESISTANCE",
    parameters={"left_bars": 5, "right_bars": 5},
    required_lookback=11,  # left_bars + 1 + right_bars
    formula="A bar is a pivot high if its high is strictly greater than the high of the left_bars "
    "bars before it AND the right_bars bars after it. The pivot is confirmed only after "
    "right_bars future bars are observed.",
    input_series=["high"],
    intuition="Identifies local price peaks as potential resistance levels.",
    known_limitations="Confirmation requires right_bars future bars. The pivot is NOT available at the "
    "date of the peak itself — it becomes available only at T + right_bars.",
    availability="CONFIRMATION_REQUIRED",
)

PIVOT_LOW = FeatureDefinition(
    name="pivot_low",
    version="1.0",
    family="SUPPORT_RESISTANCE",
    parameters={"left_bars": 5, "right_bars": 5},
    required_lookback=11,
    formula="A bar is a pivot low if its low is strictly less than the low of the left_bars "
    "bars before it AND the right_bars bars after it. The pivot is confirmed only after "
    "right_bars future bars are observed.",
    input_series=["low"],
    intuition="Identifies local price troughs as potential support levels.",
    known_limitations="Confirmation requires right_bars future bars. The pivot is NOT available at the "
    "date of the trough itself — it becomes available only at T + right_bars.",
    availability="CONFIRMATION_REQUIRED",
)

ATR_DISTANCE_TO_SUPPORT = FeatureDefinition(
    name="atr_distance_to_support",
    version="1.0",
    family="SUPPORT_RESISTANCE",
    parameters={"pivot_left": 5, "pivot_right": 5, "atr_period": 14, "lookback_pivots": 50},
    required_lookback=65,
    formula="(close - nearest_confirmed_pivot_low) / ATR_14. Measures how many ATRs price is "
    "above the nearest support level.",
    input_series=["high", "low", "close"],
    intuition="Proximity to support normalised by volatility. Low values suggest support is nearby.",
    known_limitations="Inherits pivot confirmation delay. Only uses confirmed pivots (PIT-safe).",
    availability="CONFIRMATION_REQUIRED",
)

# Registry of all defined features
ALL_FEATURES: dict[str, FeatureDefinition] = {
    f.feature_id: f
    for f in [
        SMA_20,
        SMA_50,
        SMA_200,
        EMA_20,
        MA_SLOPE_50,
        PRICE_TO_MA_50,
        RSI_14,
        ROC_20,
        ATR_14,
        ATR_PERCENT_14,
        ROLLING_VOLATILITY_20,
        AVG_VOLUME_20,
        AVG_TRADED_VALUE_20,
        RELATIVE_VOLUME,
        DONCHIAN_20,
        DISTANCE_FROM_52W_HIGH,
        PIVOT_HIGH,
        PIVOT_LOW,
        ATR_DISTANCE_TO_SUPPORT,
    ]
}
