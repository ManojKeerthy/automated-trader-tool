"""Market Regime Classification Engine.

Per M3A approved amendments:
- RegimeDefinition is a versioned configuration specifying methodology, thresholds,
  and lookback periods for deterministic regime classification.
- BULLISH/BEARISH/SIDEWAYS and LOW/NORMAL/HIGH/EXTREME are deterministic outputs
  of documented definitions, not undocumented constants.
- Regime classification at T uses only information available at T.
- Breadth calculations carry universe/source quality. Unverified breadth cannot
  contribute to a TRUSTWORTHY regime classification.
- Market breadth using today's constituents for historical dates is classified UNVERIFIED.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date  # noqa: TC003
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Regime enumerations
# ---------------------------------------------------------------------------

TREND_BULLISH = "BULLISH"
TREND_BEARISH = "BEARISH"
TREND_SIDEWAYS = "SIDEWAYS"

VOL_LOW = "LOW"
VOL_NORMAL = "NORMAL"
VOL_HIGH = "HIGH"
VOL_EXTREME = "EXTREME"

BREADTH_STRONG = "STRONG"
BREADTH_NEUTRAL = "NEUTRAL"
BREADTH_WEAK = "WEAK"
BREADTH_UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class RegimeDefinition:
    """Versioned, documented regime classification methodology.

    All thresholds and methodology are explicit and deterministic.
    Changes to methodology produce a new version.

    Attributes:
        version: Unique version identifier for this regime definition.
        benchmark_source: Description of the benchmark used (e.g. "Nifty 50 ETF Proxy").
        trend_methodology: Human-readable description of trend classification logic.
        trend_fast_ma: Period for the fast moving average used in trend classification.
        trend_slow_ma: Period for the slow moving average used in trend classification.
        volatility_methodology: Human-readable description of volatility classification logic.
        volatility_atr_period: ATR period for volatility measurement.
        volatility_lookback: Lookback for volatility percentile ranking.
        volatility_high_percentile: Percentile threshold above which volatility is HIGH.
        volatility_extreme_percentile: Percentile threshold above which volatility is EXTREME.
        volatility_low_percentile: Percentile threshold below which volatility is LOW.
        breadth_methodology: Human-readable description of breadth classification logic.
        breadth_ma_period: MA period for breadth computation (% above this MA).
        breadth_strong_threshold: Fraction of constituents above MA for STRONG breadth.
        breadth_weak_threshold: Fraction of constituents above MA for WEAK breadth.
        quality_requirements: Research quality required for each component.
    """

    version: str = "v1.0"
    benchmark_source: str = "Nifty 50 universe (ETF proxy or constituent average)"

    # Trend methodology
    trend_methodology: str = (
        "BULLISH: Benchmark close > SMA(trend_fast_ma) AND SMA(trend_fast_ma) > SMA(trend_slow_ma). "
        "BEARISH: Benchmark close < SMA(trend_fast_ma) AND SMA(trend_fast_ma) < SMA(trend_slow_ma). "
        "SIDEWAYS: Otherwise."
    )
    trend_fast_ma: int = 50
    trend_slow_ma: int = 200

    # Volatility methodology
    volatility_methodology: str = (
        "ATR% ranked against its own rolling history (volatility_lookback bars). "
        "EXTREME: percentile >= volatility_extreme_percentile. "
        "HIGH: percentile >= volatility_high_percentile. "
        "LOW: percentile <= volatility_low_percentile. "
        "NORMAL: otherwise."
    )
    volatility_atr_period: int = 14
    volatility_lookback: int = 252  # ~1 year for percentile ranking
    volatility_high_percentile: float = 75.0
    volatility_extreme_percentile: float = 90.0
    volatility_low_percentile: float = 25.0

    # Breadth methodology
    breadth_methodology: str = (
        "Fraction of universe constituents with close > SMA(breadth_ma_period). "
        "STRONG: fraction >= breadth_strong_threshold. "
        "WEAK: fraction <= breadth_weak_threshold. "
        "NEUTRAL: otherwise. "
        "UNAVAILABLE: if universe is UNVERIFIED for the query date."
    )
    breadth_ma_period: int = 50
    breadth_strong_threshold: float = 0.60  # 60%+ above MA = strong breadth
    breadth_weak_threshold: float = 0.40  # 40%- above MA = weak breadth

    quality_requirements: str = (
        "Trend: requires benchmark price history >= trend_slow_ma bars. "
        "Volatility: requires ATR history >= volatility_lookback bars. "
        "Breadth: requires verified universe membership for query date. "
        "UNVERIFIED breadth cannot contribute to TRUSTWORTHY regime."
    )


# Default regime definition
DEFAULT_REGIME_DEFINITION = RegimeDefinition()


@dataclass(frozen=True)
class MarketRegimeSnapshot:
    """Point-in-time market regime classification result.

    Attributes:
        observation_date: The date for which the regime was computed.
        regime_version: Version of the RegimeDefinition used.
        trend: BULLISH, BEARISH, or SIDEWAYS.
        volatility: LOW, NORMAL, HIGH, or EXTREME.
        breadth: STRONG, NEUTRAL, WEAK, or UNAVAILABLE.
        trend_quality: Quality of the trend classification data.
        volatility_quality: Quality of the volatility classification data.
        breadth_quality: Quality of the breadth classification data.
        overall_quality: Minimum quality across all components.
        metrics: Underlying computed metric values for transparency.
    """

    observation_date: date
    regime_version: str
    trend: str
    volatility: str
    breadth: str
    trend_quality: str = "COMPUTED"  # COMPUTED, INSUFFICIENT_DATA, UNAVAILABLE
    volatility_quality: str = "COMPUTED"
    breadth_quality: str = "COMPUTED"  # COMPUTED, UNVERIFIED_UNIVERSE, UNAVAILABLE
    overall_quality: str = "COMPUTED"
    metrics: dict[str, Any] = field(default_factory=dict)


class MarketRegimeEngine:
    """Deterministic point-in-time market regime classifier.

    Uses only information available at or before the classification date.
    Breadth quality tracks whether the constituent universe is verified.
    """

    def __init__(self, definition: RegimeDefinition | None = None):
        self.definition = definition or DEFAULT_REGIME_DEFINITION

    def classify(
        self,
        observation_date: date,
        benchmark_close: pd.Series,
        benchmark_high: pd.Series | None = None,
        benchmark_low: pd.Series | None = None,
        constituent_closes: dict[str, pd.Series] | None = None,
        universe_verified: bool = True,
    ) -> MarketRegimeSnapshot:
        """Classify market regime at observation_date.

        Args:
            observation_date: The date for which to compute the regime.
            benchmark_close: Historical closing prices of the benchmark/index proxy.
                Must be date-indexed and contain only data <= observation_date.
            benchmark_high: Historical high prices (for ATR computation).
            benchmark_low: Historical low prices (for ATR computation).
            constituent_closes: Dict of {symbol: close_series} for breadth computation.
                Must contain only data <= observation_date.
            universe_verified: Whether the constituent universe is verified for this date.

        Returns:
            MarketRegimeSnapshot with regime classification and quality indicators.
        """
        defn = self.definition
        metrics: dict[str, Any] = {"regime_definition_version": defn.version}

        # --- Trend Classification ---
        trend, trend_quality, trend_metrics = self._classify_trend(benchmark_close, defn)
        metrics.update(trend_metrics)

        # --- Volatility Classification ---
        vol, vol_quality, vol_metrics = self._classify_volatility(
            benchmark_close, benchmark_high, benchmark_low, defn
        )
        metrics.update(vol_metrics)

        # --- Breadth Classification ---
        breadth, breadth_quality, breadth_metrics = self._classify_breadth(
            constituent_closes, universe_verified, defn
        )
        metrics.update(breadth_metrics)

        # Overall quality = minimum across components
        quality_levels = {
            "COMPUTED": 3,
            "UNVERIFIED_UNIVERSE": 2,
            "INSUFFICIENT_DATA": 1,
            "UNAVAILABLE": 0,
        }
        all_qualities = [trend_quality, vol_quality, breadth_quality]
        overall_quality = min(all_qualities, key=lambda q: quality_levels.get(q, 0))

        return MarketRegimeSnapshot(
            observation_date=observation_date,
            regime_version=defn.version,
            trend=trend,
            volatility=vol,
            breadth=breadth,
            trend_quality=trend_quality,
            volatility_quality=vol_quality,
            breadth_quality=breadth_quality,
            overall_quality=overall_quality,
            metrics=metrics,
        )

    def _classify_trend(
        self, benchmark_close: pd.Series, defn: RegimeDefinition
    ) -> tuple[str, str, dict[str, Any]]:
        """Classify trend regime."""
        metrics: dict[str, Any] = {}

        if len(benchmark_close) < defn.trend_slow_ma:
            return TREND_SIDEWAYS, "INSUFFICIENT_DATA", {"trend_note": "insufficient history"}

        fast_ma = benchmark_close.rolling(
            window=defn.trend_fast_ma, min_periods=defn.trend_fast_ma
        ).mean()
        slow_ma = benchmark_close.rolling(
            window=defn.trend_slow_ma, min_periods=defn.trend_slow_ma
        ).mean()

        latest_close = benchmark_close.iloc[-1]
        latest_fast = fast_ma.iloc[-1]
        latest_slow = slow_ma.iloc[-1]

        if np.isnan(latest_fast) or np.isnan(latest_slow):
            return (
                TREND_SIDEWAYS,
                "INSUFFICIENT_DATA",
                {"trend_note": "MA values not yet available"},
            )

        metrics["benchmark_close"] = float(latest_close)
        metrics["fast_ma"] = float(latest_fast)
        metrics["slow_ma"] = float(latest_slow)

        if latest_close > latest_fast and latest_fast > latest_slow:
            return TREND_BULLISH, "COMPUTED", metrics
        elif latest_close < latest_fast and latest_fast < latest_slow:
            return TREND_BEARISH, "COMPUTED", metrics
        else:
            return TREND_SIDEWAYS, "COMPUTED", metrics

    def _classify_volatility(
        self,
        benchmark_close: pd.Series,
        benchmark_high: pd.Series | None,
        benchmark_low: pd.Series | None,
        defn: RegimeDefinition,
    ) -> tuple[str, str, dict[str, Any]]:
        """Classify volatility regime using ATR% percentile ranking."""
        metrics: dict[str, Any] = {}

        if benchmark_high is None or benchmark_low is None:
            return VOL_NORMAL, "UNAVAILABLE", {"volatility_note": "high/low data not provided"}

        if len(benchmark_close) < defn.volatility_lookback:
            return (
                VOL_NORMAL,
                "INSUFFICIENT_DATA",
                {"volatility_note": "insufficient history for percentile"},
            )

        # Compute ATR%
        prev_close = benchmark_close.shift(1)
        tr = pd.concat(
            [
                benchmark_high - benchmark_low,
                (benchmark_high - prev_close).abs(),
                (benchmark_low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr_val = tr.rolling(
            window=defn.volatility_atr_period, min_periods=defn.volatility_atr_period
        ).mean()
        atr_pct = (atr_val / benchmark_close) * 100

        # Percentile rank against rolling history
        current_atr_pct = atr_pct.iloc[-1]
        if np.isnan(current_atr_pct):
            return VOL_NORMAL, "INSUFFICIENT_DATA", {"volatility_note": "ATR% not available"}

        lookback_window = atr_pct.iloc[-defn.volatility_lookback :]
        valid_values = lookback_window.dropna()
        if len(valid_values) < 20:  # minimum for meaningful percentile
            return VOL_NORMAL, "INSUFFICIENT_DATA", {"volatility_note": "too few valid ATR% values"}

        percentile = (valid_values < current_atr_pct).sum() / len(valid_values) * 100

        metrics["current_atr_pct"] = float(current_atr_pct)
        metrics["volatility_percentile"] = float(percentile)

        if percentile >= defn.volatility_extreme_percentile:
            return VOL_EXTREME, "COMPUTED", metrics
        elif percentile >= defn.volatility_high_percentile:
            return VOL_HIGH, "COMPUTED", metrics
        elif percentile <= defn.volatility_low_percentile:
            return VOL_LOW, "COMPUTED", metrics
        else:
            return VOL_NORMAL, "COMPUTED", metrics

    def _classify_breadth(
        self,
        constituent_closes: dict[str, pd.Series] | None,
        universe_verified: bool,
        defn: RegimeDefinition,
    ) -> tuple[str, str, dict[str, Any]]:
        """Classify market breadth (% of constituents above MA)."""
        metrics: dict[str, Any] = {}

        if constituent_closes is None or len(constituent_closes) == 0:
            return BREADTH_UNAVAILABLE, "UNAVAILABLE", {"breadth_note": "no constituent data"}

        above_ma_count = 0
        total_valid = 0

        for _symbol, closes in constituent_closes.items():
            if len(closes) < defn.breadth_ma_period:
                continue
            ma = closes.rolling(
                window=defn.breadth_ma_period, min_periods=defn.breadth_ma_period
            ).mean()
            latest_close = closes.iloc[-1]
            latest_ma = ma.iloc[-1]
            if not np.isnan(latest_close) and not np.isnan(latest_ma):
                total_valid += 1
                if latest_close > latest_ma:
                    above_ma_count += 1

        if total_valid == 0:
            return BREADTH_UNAVAILABLE, "UNAVAILABLE", {"breadth_note": "no valid constituent MAs"}

        breadth_fraction = above_ma_count / total_valid
        metrics["breadth_fraction"] = float(breadth_fraction)
        metrics["breadth_above_ma"] = above_ma_count
        metrics["breadth_total_valid"] = total_valid

        # Quality: UNVERIFIED if universe is not verified for this date
        quality = "COMPUTED" if universe_verified else "UNVERIFIED_UNIVERSE"

        if breadth_fraction >= defn.breadth_strong_threshold:
            return BREADTH_STRONG, quality, metrics
        elif breadth_fraction <= defn.breadth_weak_threshold:
            return BREADTH_WEAK, quality, metrics
        else:
            return BREADTH_NEUTRAL, quality, metrics
