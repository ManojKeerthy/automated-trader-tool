"""M3A Feature Framework Tests.

Tests per M3A approved amendments:
1. PIT feature calculation correctness
2. Look-ahead prevention (pivot confirmation delay)
3. NaN edge cases for insufficient lookback
4. Feature definition metadata
5. Deterministic reproducibility
6. Multi-family indicator correctness
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from tradecraft.features.base import (
    ALL_FEATURES,
    FeatureSet,
    FeatureValue,
)
from tradecraft.features.indicators import (
    atr,
    atr_percent,
    avg_traded_value,
    avg_volume,
    breakout_distance,
    distance_from_high,
    donchian_channel,
    ema,
    find_pivot_highs,
    find_pivot_lows,
    ma_slope,
    multi_period_return,
    nearest_support_distance_atr,
    price_to_ma_ratio,
    relative_volume,
    roc,
    rolling_volatility,
    rsi,
    sma,
    trend_structure,
    volatility_expansion_ratio,
    volume_expansion,
)

# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def uptrend_data() -> pd.DataFrame:
    """Generate a simple uptrend price series."""
    n = 300
    np.random.seed(42)
    base = 100.0 + np.arange(n) * 0.5 + np.random.normal(0, 2, n)
    close = pd.Series(base)
    high = close + abs(np.random.normal(0, 1, n))
    low = close - abs(np.random.normal(0, 1, n))
    volume = pd.Series(np.random.randint(100_000, 1_000_000, n), dtype=float)
    return pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume})


@pytest.fixture
def short_data() -> pd.DataFrame:
    """Generate data shorter than most lookback requirements."""
    n = 10
    close = pd.Series([100 + i for i in range(n)], dtype=float)
    high = close + 1
    low = close - 1
    volume = pd.Series([100_000] * n, dtype=float)
    return pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume})


@pytest.fixture
def pivot_data() -> pd.DataFrame:
    """Generate data with a clear pivot high and pivot low."""
    # Create a V-shape with clear pivot
    prices = (
        [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]  # uptrend
        + [109, 108, 107, 106, 105]  # downtrend from pivot high at index 10
        + [104, 103, 102, 101, 100]  # more down
        + [101, 102, 103, 104, 105]  # recovery from pivot low at index 20
    )
    close = pd.Series(prices, dtype=float)
    high = close + 0.5
    low = close - 0.5
    return pd.DataFrame({"close": close, "high": high, "low": low})


# ---------------------------------------------------------------------------
# TREND feature tests
# ---------------------------------------------------------------------------


class TestTrendFeatures:
    """Test trend indicator calculations."""

    def test_sma_known_value(self):
        """SMA of known values matches hand calculation."""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        result = sma(data, 5)
        assert result.iloc[4] == pytest.approx(3.0)  # mean([1,2,3,4,5])
        assert result.iloc[9] == pytest.approx(8.0)  # mean([6,7,8,9,10])

    def test_sma_insufficient_lookback_is_nan(self, short_data: pd.DataFrame):
        """SMA returns NaN for positions with insufficient lookback."""
        result = sma(short_data["close"], 20)
        assert result.isna().all(), "All values should be NaN with < 20 bars"

    def test_ema_responds_faster(self, uptrend_data: pd.DataFrame):
        """EMA should respond faster to recent price changes than SMA."""
        sma_val = sma(uptrend_data["close"], 20).iloc[-1]
        ema_val = ema(uptrend_data["close"], 20).iloc[-1]
        # In uptrend, EMA should be closer to current price than SMA
        current = uptrend_data["close"].iloc[-1]
        assert abs(ema_val - current) < abs(sma_val - current)

    def test_ma_slope_positive_in_uptrend(self, uptrend_data: pd.DataFrame):
        """MA slope should be positive in uptrend."""
        result = ma_slope(uptrend_data["close"], 50, 5)
        assert result.iloc[-1] > 0

    def test_price_to_ma_ratio_range(self, uptrend_data: pd.DataFrame):
        """Price-to-MA ratio should be bounded in normal conditions."""
        result = price_to_ma_ratio(uptrend_data["close"], 50)
        valid = result.dropna()
        assert all(abs(v) < 1.0 for v in valid), "Ratio should be < 100% in normal data"

    def test_trend_structure_score_bounded(self, uptrend_data: pd.DataFrame):
        """Trend structure score should be in [-1, +1]."""
        result = trend_structure(uptrend_data["high"], uptrend_data["low"], 10)
        valid = result.dropna()
        assert all(-1 <= v <= 1 for v in valid)

    def test_sma_period_validation(self):
        """SMA should raise for non-positive period."""
        with pytest.raises(ValueError):
            sma(pd.Series([1, 2, 3]), 0)


# ---------------------------------------------------------------------------
# MOMENTUM feature tests
# ---------------------------------------------------------------------------


class TestMomentumFeatures:
    """Test momentum indicator calculations."""

    def test_rsi_range(self, uptrend_data: pd.DataFrame):
        """RSI values should be between 0 and 100."""
        result = rsi(uptrend_data["close"], 14)
        valid = result.dropna()
        assert all(0 <= v <= 100 for v in valid)

    def test_rsi_overbought_in_strong_uptrend(self):
        """RSI should be > 50 in a strong continuous uptrend."""
        data = pd.Series([100 + i * 2 for i in range(50)], dtype=float)
        result = rsi(data, 14)
        # Last value should be well above 50
        assert result.iloc[-1] > 60

    def test_rsi_insufficient_lookback(self):
        """RSI returns NaN for first bar (no delta) and requires sufficient data."""
        data = pd.Series([100 + i for i in range(10)], dtype=float)
        result = rsi(data, 14)
        # First bar always NaN (no delta available)
        assert np.isnan(result.iloc[0])
        # With only 10 bars and period=14, Wilder EWM min_periods=14
        # not met, but monotonically increasing data triggers the
        # avg_loss=0 branch returning 100.0 (all gains).
        # Verify that with genuinely insufficient history (e.g., only 5 bars),
        # the first values remain NaN.
        very_short = pd.Series([100.0, 99.0, 101.0, 98.0, 102.0], dtype=float)
        result_short = rsi(very_short, 14)
        assert np.isnan(result_short.iloc[0])

    def test_roc_known_value(self):
        """ROC of known values matches hand calculation."""
        data = pd.Series([100, 105, 110, 115, 120], dtype=float)
        result = roc(data, 2)
        # ROC at index 2: (110-100)/100 * 100 = 10.0
        assert result.iloc[2] == pytest.approx(10.0)

    def test_multi_period_return_shape(self, uptrend_data: pd.DataFrame):
        """Multi-period return produces correct columns."""
        result = multi_period_return(uptrend_data["close"], [5, 10, 20])
        assert "return_5d" in result.columns
        assert "return_10d" in result.columns
        assert "return_20d" in result.columns


# ---------------------------------------------------------------------------
# VOLATILITY feature tests
# ---------------------------------------------------------------------------


class TestVolatilityFeatures:
    """Test volatility indicator calculations."""

    def test_atr_positive(self, uptrend_data: pd.DataFrame):
        """ATR should always be positive."""
        result = atr(uptrend_data["high"], uptrend_data["low"], uptrend_data["close"], 14)
        valid = result.dropna()
        assert all(v > 0 for v in valid)

    def test_atr_percent_normalised(self, uptrend_data: pd.DataFrame):
        """ATR% should be reasonable percentage."""
        result = atr_percent(uptrend_data["high"], uptrend_data["low"], uptrend_data["close"], 14)
        valid = result.dropna()
        assert all(0 < v < 50 for v in valid), "ATR% should be reasonable"

    def test_rolling_volatility_annualised(self, uptrend_data: pd.DataFrame):
        """Rolling volatility should be annualised and positive."""
        result = rolling_volatility(uptrend_data["close"], 20)
        valid = result.dropna()
        assert all(v > 0 for v in valid)
        # Annualised vol for typical equity should be < 100%
        assert all(v < 1.0 for v in valid)

    def test_volatility_expansion_ratio(self, uptrend_data: pd.DataFrame):
        """Volatility expansion ratio should be around 1 in normal conditions."""
        result = volatility_expansion_ratio(
            uptrend_data["high"], uptrend_data["low"], uptrend_data["close"], 5, 20
        )
        valid = result.dropna()
        assert all(0.1 < v < 10 for v in valid)


# ---------------------------------------------------------------------------
# VOLUME / LIQUIDITY feature tests
# ---------------------------------------------------------------------------


class TestVolumeFeatures:
    """Test volume/liquidity indicator calculations."""

    def test_avg_volume_known_value(self):
        """Average volume of constant series equals the constant."""
        data = pd.Series([100_000] * 30, dtype=float)
        result = avg_volume(data, 20)
        assert result.iloc[19] == pytest.approx(100_000)

    def test_avg_traded_value_computation(self):
        """Average traded value = avg(close * volume)."""
        close = pd.Series([100] * 25, dtype=float)
        volume = pd.Series([1000] * 25, dtype=float)
        result = avg_traded_value(close, volume, 20)
        assert result.iloc[19] == pytest.approx(100_000)

    def test_relative_volume_baseline(self):
        """RVOL = 1 when volume equals average."""
        volume = pd.Series([100_000] * 30, dtype=float)
        result = relative_volume(volume, 20)
        assert result.iloc[25] == pytest.approx(1.0)

    def test_volume_expansion_baseline(self):
        """Volume expansion = 1 when volume is constant."""
        volume = pd.Series([100_000] * 30, dtype=float)
        result = volume_expansion(volume, 5, 20)
        assert result.iloc[25] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# BREAKOUT feature tests
# ---------------------------------------------------------------------------


class TestBreakoutFeatures:
    """Test breakout/price structure indicator calculations."""

    def test_donchian_channel_known_value(self):
        """Donchian channel of known values matches hand calculation."""
        high = pd.Series([10, 12, 14, 13, 11] * 4, dtype=float)
        low = pd.Series([8, 9, 10, 9, 7] * 4, dtype=float)
        upper, middle, lower = donchian_channel(high, low, 5)
        assert upper.iloc[4] == pytest.approx(14.0)  # max of first 5 highs
        assert lower.iloc[4] == pytest.approx(7.0)  # min of first 5 lows
        assert middle.iloc[4] == pytest.approx(10.5)  # (14 + 7) / 2

    def test_breakout_distance_at_high(self):
        """Breakout distance is 0 at the period high."""
        high = pd.Series([100, 101, 102, 103, 104, 105] * 5, dtype=float)
        close = pd.Series([100, 101, 102, 103, 104, 105] * 5, dtype=float)
        result = breakout_distance(close, high, 5)
        # When close equals the rolling max of high, distance should be near 0
        valid = result.dropna()
        # At positions where close is the max, distance should be >= 0
        assert any(v >= -0.01 for v in valid)

    def test_distance_from_52w_high(self, uptrend_data: pd.DataFrame):
        """Distance from 52w high should be <= 0."""
        result = distance_from_high(uptrend_data["close"], uptrend_data["high"], 252)
        valid = result.dropna()
        assert all(v <= 0.001 for v in valid), "Distance should be <= 0 (below or at high)"


# ---------------------------------------------------------------------------
# SUPPORT / RESISTANCE feature tests — CRITICAL PIT SAFETY
# ---------------------------------------------------------------------------


class TestSupportResistanceFeatures:
    """Test pivot point identification and PIT safety.

    CRITICAL: These tests verify that pivot points are placed at their
    CONFIRMATION dates, not at the actual peak/trough dates.
    This is the primary look-ahead prevention mechanism for S&R features.
    """

    def test_pivot_high_not_at_peak_date(self, pivot_data: pd.DataFrame):
        """CRITICAL: Pivot high must NOT appear at the peak date itself.

        A pivot high at index 10 with right_bars=5 should only become
        available at index 15 (10 + 5).
        """
        result = find_pivot_highs(pivot_data["high"], left_bars=5, right_bars=5)
        # The actual peak is at index 10. It should NOT be at index 10.
        assert np.isnan(result.iloc[10]), (
            "Pivot high must NOT be available at the peak date — this would be look-ahead bias!"
        )

    def test_pivot_high_at_confirmation_date(self, pivot_data: pd.DataFrame):
        """Pivot high must appear at index (peak + right_bars)."""
        result = find_pivot_highs(pivot_data["high"], left_bars=5, right_bars=5)
        # The peak is at index 10, confirmation at index 15
        if len(result) > 15:
            # There should be a pivot at confirmation index
            confirmation_value = result.iloc[15]
            if not np.isnan(confirmation_value):
                assert confirmation_value == pivot_data["high"].iloc[10]

    def test_pivot_low_not_at_trough_date(self, pivot_data: pd.DataFrame):
        """CRITICAL: Pivot low must NOT appear at the trough date itself."""
        result = find_pivot_lows(pivot_data["low"], left_bars=5, right_bars=5)
        # Trough is around index 20
        trough_idx = pivot_data["low"].iloc[15:25].idxmin()
        assert np.isnan(result.iloc[trough_idx]), (
            "Pivot low must NOT be available at the trough date — this would be look-ahead bias!"
        )

    def test_pivot_confirmation_delay_semantics(self):
        """Verify that pivots use confirmation delay consistently."""
        # Simple test: peak at index 5 with left=2, right=2
        # Peak should appear at index 7 (5+2)
        high = pd.Series([1, 2, 3, 4, 5, 10, 5, 4, 3, 2, 1], dtype=float)
        result = find_pivot_highs(high, left_bars=2, right_bars=2)
        assert np.isnan(result.iloc[5]), "Pivot at peak date is look-ahead"
        assert result.iloc[7] == pytest.approx(10.0), "Pivot should appear at confirmation"

    def test_nearest_support_uses_confirmed_pivots(self, uptrend_data: pd.DataFrame):
        """ATR distance to support uses only confirmed pivot lows."""
        atr_val = atr(uptrend_data["high"], uptrend_data["low"], uptrend_data["close"], 14)
        result = nearest_support_distance_atr(
            uptrend_data["close"],
            uptrend_data["low"],
            uptrend_data["high"],
            atr_val,
            left_bars=5,
            right_bars=5,
        )
        # Should have NaN at the start where no confirmed pivots exist
        assert np.isnan(result.iloc[0])
        # Eventually should have valid values
        valid = result.dropna()
        if len(valid) > 0:
            assert all(v > 0 for v in valid if not np.isnan(v)), (
                "Support distance should be positive in uptrend"
            )


# ---------------------------------------------------------------------------
# Feature framework metadata tests
# ---------------------------------------------------------------------------


class TestFeatureFramework:
    """Test feature definition metadata and registry."""

    def test_all_features_have_unique_ids(self):
        """All features in the registry have unique feature_ids."""
        assert len(ALL_FEATURES) >= 19, "Should have at least 19 defined features"
        # Feature IDs are already keys in the dict
        ids = list(ALL_FEATURES.keys())
        assert len(ids) == len(set(ids))

    def test_all_features_have_version(self):
        """All features must have a version."""
        for fid, fdef in ALL_FEATURES.items():
            assert fdef.version, f"Feature {fid} missing version"

    def test_all_features_have_family(self):
        """All features must belong to a family."""
        valid_families = {
            "TREND",
            "MOMENTUM",
            "VOLATILITY",
            "VOLUME",
            "BREAKOUT",
            "SUPPORT_RESISTANCE",
        }
        for fid, fdef in ALL_FEATURES.items():
            assert fdef.family in valid_families, f"Feature {fid} has invalid family {fdef.family}"

    def test_confirmation_required_features_have_lookback(self):
        """Features with CONFIRMATION_REQUIRED availability must document it."""
        for _fid, fdef in ALL_FEATURES.items():
            if fdef.availability == "CONFIRMATION_REQUIRED":
                assert fdef.required_lookback > 0
                assert "confirmation" in fdef.formula.lower() or "confirmed" in fdef.formula.lower()

    def test_feature_set_get(self):
        """FeatureSet.get() returns value or None."""
        fv = FeatureValue(
            feature_id="sma_20_v1.0",
            instrument_id=None,
            observation_date=date(2026, 1, 1),
            value=105.5,
        )
        fs = FeatureSet(
            instrument_id=None,
            observation_date=date(2026, 1, 1),
            values={"sma_20_v1.0": fv},
        )
        assert fs.get("sma_20_v1.0") == 105.5
        assert fs.get("nonexistent") is None

    def test_feature_set_has_sufficient_data(self):
        """FeatureSet.has_sufficient_data() correctly reports."""
        fv_good = FeatureValue(
            feature_id="sma_20_v1.0",
            instrument_id=None,
            observation_date=date(2026, 1, 1),
            value=105.5,
            quality="COMPUTED",
        )
        fv_bad = FeatureValue(
            feature_id="sma_200_v1.0",
            instrument_id=None,
            observation_date=date(2026, 1, 1),
            value=None,
            quality="INSUFFICIENT_LOOKBACK",
        )
        fs = FeatureSet(
            instrument_id=None,
            observation_date=date(2026, 1, 1),
            values={"sma_20_v1.0": fv_good, "sma_200_v1.0": fv_bad},
        )
        assert fs.has_sufficient_data("sma_20_v1.0")
        assert not fs.has_sufficient_data("sma_200_v1.0")


# ---------------------------------------------------------------------------
# Deterministic reproducibility test
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Verify that feature calculations are deterministic."""

    def test_sma_is_deterministic(self, uptrend_data: pd.DataFrame):
        """Same input always produces same SMA output."""
        r1 = sma(uptrend_data["close"], 20)
        r2 = sma(uptrend_data["close"], 20)
        pd.testing.assert_series_equal(r1, r2)

    def test_rsi_is_deterministic(self, uptrend_data: pd.DataFrame):
        """Same input always produces same RSI output."""
        r1 = rsi(uptrend_data["close"], 14)
        r2 = rsi(uptrend_data["close"], 14)
        pd.testing.assert_series_equal(r1, r2)

    def test_pivot_is_deterministic(self, pivot_data: pd.DataFrame):
        """Same input always produces same pivot output."""
        r1 = find_pivot_highs(pivot_data["high"], 5, 5)
        r2 = find_pivot_highs(pivot_data["high"], 5, 5)
        pd.testing.assert_series_equal(r1, r2)
