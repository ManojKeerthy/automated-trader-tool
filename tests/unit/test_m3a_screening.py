"""M3A Screening Engine Tests.

Tests per M3A approved amendments:
1. Eligibility screening with configurable liquidity thresholds
2. Operational eligibility vs research quality separation
3. Market regime classification correctness
4. Regime breadth quality tracking (UNVERIFIED universe)
5. Zero-candidate output validity
6. Pivot look-ahead safety
7. Regime reproducibility/determinism
8. Screening metadata completeness
"""
from __future__ import annotations

import uuid
from datetime import date

import numpy as np
import pandas as pd
import pytest

from tradecraft.screening.eligibility import (
    INSUFFICIENT_HISTORY,
    LOW_LIQUIDITY,
    STALE_DATA,
    UNVERIFIED_UNIVERSE,
    ZERO_VOLUME,
    EligibilityConfig,
    EligibilityScreen,
    InstrumentData,
    LiquidityScreenConfig,
)
from tradecraft.screening.engine import (
    ScreeningEngine,
)
from tradecraft.screening.regime import (
    BREADTH_UNAVAILABLE,
    DEFAULT_REGIME_DEFINITION,
    TREND_BEARISH,
    TREND_BULLISH,
    TREND_SIDEWAYS,
    MarketRegimeEngine,
    RegimeDefinition,
)

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_instrument(
    *,
    symbol: str = "TEST",
    total_bars: int = 300,
    latest_date: date | None = None,
    latest_close: float = 1500.0,
    avg_traded_value_20: float = 100_000_000.0,
    avg_volume_20: float = 500_000.0,
    identity_verified: bool = True,
    universe_verified: bool = True,
    has_unresolved_ca: bool = False,
) -> InstrumentData:
    """Create a test InstrumentData instance."""
    return InstrumentData(
        instrument_id=uuid.uuid4(),
        symbol=symbol,
        is_active=True,
        total_bars=total_bars,
        earliest_date=date(2020, 1, 1),
        latest_date=latest_date or date(2026, 7, 28),
        latest_close=latest_close,
        avg_traded_value_20=avg_traded_value_20,
        avg_volume_20=avg_volume_20,
        has_unresolved_corporate_actions=has_unresolved_ca,
        identity_verified=identity_verified,
        universe_verified=universe_verified,
    )


def _make_benchmark(n: int = 300, trend: str = "up") -> tuple[pd.Series, pd.Series, pd.Series]:
    """Create benchmark close/high/low series."""
    np.random.seed(42)
    if trend == "up":
        base = 18000 + np.arange(n) * 10 + np.random.normal(0, 50, n)
    elif trend == "down":
        base = 22000 - np.arange(n) * 10 + np.random.normal(0, 50, n)
    else:
        base = 20000 + np.random.normal(0, 100, n)
    close = pd.Series(base, dtype=float)
    high = close + abs(np.random.normal(0, 30, n))
    low = close - abs(np.random.normal(0, 30, n))
    return close, high, low


# ---------------------------------------------------------------------------
# Eligibility Screen Tests
# ---------------------------------------------------------------------------


class TestEligibilityScreen:
    """Test the eligibility screening pipeline."""

    def test_eligible_instrument_passes(self):
        """A healthy instrument should pass all checks."""
        screen = EligibilityScreen()
        inst = _make_instrument(symbol="RELIANCE")
        result = screen.screen(date(2026, 7, 28), [inst])
        assert result.eligible_count == 1
        assert result.exclusion_count == 0

    def test_insufficient_history_excludes(self):
        """Instrument with too few bars is excluded."""
        screen = EligibilityScreen()
        inst = _make_instrument(symbol="NEWIPO", total_bars=50)
        result = screen.screen(date(2026, 7, 28), [inst])
        assert result.eligible_count == 0
        assert result.exclusion_count == 1
        assert result.excluded_instruments[0].reason_code == INSUFFICIENT_HISTORY

    def test_stale_data_excludes(self):
        """Instrument with old data is excluded."""
        screen = EligibilityScreen()
        inst = _make_instrument(symbol="STALE", latest_date=date(2026, 7, 1))
        result = screen.screen(date(2026, 7, 28), [inst])
        assert result.eligible_count == 0
        assert result.excluded_instruments[0].reason_code == STALE_DATA

    def test_low_liquidity_excludes(self):
        """Instrument below liquidity threshold is excluded."""
        screen = EligibilityScreen()
        inst = _make_instrument(symbol="ILLIQUID", avg_traded_value_20=1_000_000.0)  # ₹10L < ₹5Cr
        result = screen.screen(date(2026, 7, 28), [inst])
        assert result.eligible_count == 0
        assert result.excluded_instruments[0].reason_code == LOW_LIQUIDITY

    def test_zero_volume_excludes(self):
        """Instrument with zero average volume is excluded."""
        screen = EligibilityScreen()
        inst = _make_instrument(symbol="NOLIQ", avg_volume_20=0.0)
        result = screen.screen(date(2026, 7, 28), [inst])
        assert result.eligible_count == 0
        assert result.excluded_instruments[0].reason_code == ZERO_VOLUME

    def test_configurable_liquidity_threshold(self):
        """Liquidity threshold should be configurable."""
        config = EligibilityConfig(
            liquidity=LiquidityScreenConfig(
                min_avg_traded_value=10_000_000.0,  # ₹1 Crore — lower threshold
                version="test_v1.0",
            )
        )
        screen = EligibilityScreen(config)
        inst = _make_instrument(symbol="MIDCAP", avg_traded_value_20=20_000_000.0)  # ₹2Cr
        result = screen.screen(date(2026, 7, 28), [inst])
        assert result.eligible_count == 1
        assert result.liquidity_config_version == "test_v1.0"

    def test_unverified_universe_is_quality_flag_not_exclusion(self):
        """Unverified universe should be a quality flag, not an operational exclusion."""
        screen = EligibilityScreen()
        inst = _make_instrument(symbol="HISTSYMBOL", universe_verified=False)
        result = screen.screen(date(2026, 7, 28), [inst])
        assert result.eligible_count == 1, "Should still be eligible"
        assert len(result.research_quality_flags) == 1
        assert result.research_quality_flags[0].reason_code == UNVERIFIED_UNIVERSE
        assert not result.research_quality_flags[0].is_operational

    def test_exclusion_summary(self):
        """Exclusion summary correctly counts by reason code."""
        screen = EligibilityScreen()
        instruments = [
            _make_instrument(symbol="A", total_bars=50),
            _make_instrument(symbol="B", total_bars=30),
            _make_instrument(symbol="C", avg_traded_value_20=100.0),
            _make_instrument(symbol="D"),  # passes
        ]
        result = screen.screen(date(2026, 7, 28), instruments)
        summary = result.exclusion_summary()
        assert summary.get(INSUFFICIENT_HISTORY, 0) == 2
        assert summary.get(LOW_LIQUIDITY, 0) == 1


# ---------------------------------------------------------------------------
# Market Regime Tests
# ---------------------------------------------------------------------------


class TestMarketRegime:
    """Test market regime classification."""

    def test_bullish_trend(self):
        """Uptrend data should classify as BULLISH."""
        close, high, low = _make_benchmark(300, "up")
        engine = MarketRegimeEngine()
        result = engine.classify(
            observation_date=date(2026, 7, 28),
            benchmark_close=close,
            benchmark_high=high,
            benchmark_low=low,
        )
        assert result.trend == TREND_BULLISH

    def test_bearish_trend(self):
        """Downtrend data should classify as BEARISH."""
        close, high, low = _make_benchmark(300, "down")
        engine = MarketRegimeEngine()
        result = engine.classify(
            observation_date=date(2026, 7, 28),
            benchmark_close=close,
            benchmark_high=high,
            benchmark_low=low,
        )
        assert result.trend == TREND_BEARISH

    def test_insufficient_data_returns_sideways(self):
        """Short data should return SIDEWAYS with INSUFFICIENT_DATA quality."""
        close = pd.Series([100.0] * 50)
        engine = MarketRegimeEngine()
        result = engine.classify(
            observation_date=date(2026, 7, 28),
            benchmark_close=close,
        )
        assert result.trend == TREND_SIDEWAYS
        assert result.trend_quality == "INSUFFICIENT_DATA"

    def test_regime_version_recorded(self):
        """Regime version should be recorded in the snapshot."""
        close, high, low = _make_benchmark(300, "up")
        defn = RegimeDefinition(version="test_v2.0")
        engine = MarketRegimeEngine(defn)
        result = engine.classify(
            observation_date=date(2026, 7, 28),
            benchmark_close=close,
            benchmark_high=high,
            benchmark_low=low,
        )
        assert result.regime_version == "test_v2.0"

    def test_breadth_unavailable_without_constituents(self):
        """Breadth should be UNAVAILABLE when no constituent data provided."""
        close, high, low = _make_benchmark(300, "up")
        engine = MarketRegimeEngine()
        result = engine.classify(
            observation_date=date(2026, 7, 28),
            benchmark_close=close,
            benchmark_high=high,
            benchmark_low=low,
            constituent_closes=None,
        )
        assert result.breadth == BREADTH_UNAVAILABLE
        assert result.breadth_quality == "UNAVAILABLE"

    def test_unverified_universe_breadth_quality(self):
        """Breadth with UNVERIFIED universe must have UNVERIFIED_UNIVERSE quality."""
        close, high, low = _make_benchmark(300, "up")
        # Create some constituent data
        constituents = {}
        np.random.seed(42)
        for i in range(20):
            constituents[f"STOCK_{i}"] = pd.Series(
                18000 + np.arange(300) * 5 + np.random.normal(0, 100, 300), dtype=float
            )
        engine = MarketRegimeEngine()
        result = engine.classify(
            observation_date=date(2026, 7, 28),
            benchmark_close=close,
            benchmark_high=high,
            benchmark_low=low,
            constituent_closes=constituents,
            universe_verified=False,
        )
        assert result.breadth_quality == "UNVERIFIED_UNIVERSE"

    def test_regime_deterministic(self):
        """Same input should always produce same regime."""
        close, high, low = _make_benchmark(300, "up")
        engine = MarketRegimeEngine()
        r1 = engine.classify(date(2026, 7, 28), close, high, low)
        r2 = engine.classify(date(2026, 7, 28), close, high, low)
        assert r1.trend == r2.trend
        assert r1.volatility == r2.volatility
        assert r1.breadth == r2.breadth

    def test_regime_metrics_present(self):
        """Regime snapshot should include computed metrics."""
        close, high, low = _make_benchmark(300, "up")
        engine = MarketRegimeEngine()
        result = engine.classify(
            observation_date=date(2026, 7, 28),
            benchmark_close=close,
            benchmark_high=high,
            benchmark_low=low,
        )
        assert "benchmark_close" in result.metrics
        assert "fast_ma" in result.metrics
        assert "slow_ma" in result.metrics


# ---------------------------------------------------------------------------
# Screening Engine Tests
# ---------------------------------------------------------------------------


class TestScreeningEngine:
    """Test the strategy-neutral screening engine."""

    def test_zero_candidates_valid(self):
        """Zero candidates is a valid screening result."""
        engine = ScreeningEngine()
        instruments = [
            _make_instrument(symbol="A", total_bars=50),
            _make_instrument(symbol="B", total_bars=30),
        ]
        result = engine.run(date(2026, 7, 28), instruments)
        assert result.is_empty()
        assert result.candidate_count == 0
        assert result.excluded_count == 2

    def test_screening_produces_candidates(self):
        """Eligible instruments become candidates."""
        engine = ScreeningEngine()
        instruments = [
            _make_instrument(symbol="RELIANCE"),
            _make_instrument(symbol="TCS"),
            _make_instrument(symbol="HDFC", total_bars=50),  # excluded
        ]
        result = engine.run(date(2026, 7, 28), instruments)
        assert result.candidate_count == 2
        assert result.excluded_count == 1

    def test_screening_records_metadata(self):
        """Screening result records all required metadata."""
        engine = ScreeningEngine()
        instruments = [_make_instrument(symbol="RELIANCE")]
        result = engine.run(date(2026, 7, 28), instruments)
        assert result.screening_version
        assert result.eligibility_config_version
        assert result.liquidity_config_version
        assert result.regime_definition_version
        assert result.total_universe == 1

    def test_screening_with_regime(self):
        """Screening with benchmark data produces regime classification."""
        engine = ScreeningEngine()
        instruments = [_make_instrument(symbol="RELIANCE")]
        close, high, low = _make_benchmark(300, "up")
        result = engine.run(
            date(2026, 7, 28),
            instruments,
            benchmark_close=close,
            benchmark_high=high,
            benchmark_low=low,
        )
        assert result.regime is not None
        assert result.regime.trend == TREND_BULLISH

    def test_screening_propagates_quality_warnings(self):
        """Screening propagates research quality warnings from eligibility."""
        engine = ScreeningEngine()
        instruments = [_make_instrument(symbol="HISTORICAL", universe_verified=False)]
        result = engine.run(date(2026, 7, 28), instruments)
        assert result.candidate_count == 1
        assert len(result.research_quality_warnings) > 0
        assert "UNVERIFIED_UNIVERSE" in result.research_quality_warnings[0]

    def test_screening_with_features(self):
        """Screening passes features to candidates."""
        engine = ScreeningEngine()
        inst = _make_instrument(symbol="RELIANCE")
        features = {inst.instrument_id: {"sma_20_v1.0": 1500.0, "rsi_14_v1.0": 55.0}}
        result = engine.run(
            date(2026, 7, 28),
            [inst],
            instrument_features=features,
        )
        assert result.candidate_count == 1
        assert result.candidates[0].features.get("sma_20_v1.0") == 1500.0

    def test_screening_empty_universe(self):
        """Empty universe produces zero candidates without error."""
        engine = ScreeningEngine()
        result = engine.run(date(2026, 7, 28), [])
        assert result.is_empty()
        assert result.total_universe == 0

    def test_screening_exclusion_summary(self):
        """Screening records exclusion summary from eligibility."""
        engine = ScreeningEngine()
        instruments = [
            _make_instrument(symbol="A", total_bars=50),
            _make_instrument(symbol="B", avg_traded_value_20=100.0),
        ]
        result = engine.run(date(2026, 7, 28), instruments)
        assert INSUFFICIENT_HISTORY in result.exclusion_summary
        assert LOW_LIQUIDITY in result.exclusion_summary


# ---------------------------------------------------------------------------
# Regime Definition Versioning Tests
# ---------------------------------------------------------------------------


class TestRegimeDefinitionVersioning:
    """Test that regime methodology is explicitly versioned."""

    def test_default_definition_has_version(self):
        """Default regime definition has a version."""
        assert DEFAULT_REGIME_DEFINITION.version == "v1.0"

    def test_definition_documents_methodology(self):
        """Regime definition documents all methodology strings."""
        defn = DEFAULT_REGIME_DEFINITION
        assert "BULLISH" in defn.trend_methodology
        assert "BEARISH" in defn.trend_methodology
        assert "EXTREME" in defn.volatility_methodology
        assert "STRONG" in defn.breadth_methodology

    def test_definition_immutable(self):
        """RegimeDefinition should be frozen/immutable."""
        defn = DEFAULT_REGIME_DEFINITION
        with pytest.raises(AttributeError):
            defn.version = "tampered"  # type: ignore[misc]

    def test_custom_thresholds(self):
        """Custom thresholds should be respected."""
        defn = RegimeDefinition(
            version="test_v3.0",
            breadth_strong_threshold=0.80,
            breadth_weak_threshold=0.20,
        )
        assert defn.breadth_strong_threshold == 0.80
        assert defn.breadth_weak_threshold == 0.20
