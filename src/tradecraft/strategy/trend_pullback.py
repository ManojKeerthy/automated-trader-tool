"""Family A: Trend Pullback Strategy.

Hypothesis: Securities in established uptrends offer favorable swing continuation
after a controlled pullback to dynamic support once buying strength resumes.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.features import indicators
from tradecraft.strategy.base import SignalIntent


class TrendPullbackStrategy:
    """Strategy Family A: Trend Pullback."""

    def __init__(
        self,
        trend_ma: int = 50,
        pullback_atr_dist: float = 1.5,
        rsi_trigger: float = 45.0,
        atr_stop_mult: float = 2.0,
        benchmark_symbol: str = "NIFTY 50",
    ):
        self.trend_ma = trend_ma
        self.pullback_atr_dist = pullback_atr_dist
        self.rsi_trigger = rsi_trigger
        self.atr_stop_mult = atr_stop_mult
        self.benchmark_symbol = benchmark_symbol

    @property
    def strategy_id(self) -> str:
        return "strat_trend_pullback"

    @property
    def name(self) -> str:
        return "Trend Pullback Strategy"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Medium-term trend pullback strategy with deterministic stop placement."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "trend_ma": self.trend_ma,
            "pullback_atr_dist": self.pullback_atr_dist,
            "rsi_trigger": self.rsi_trigger,
            "atr_stop_mult": self.atr_stop_mult,
            "benchmark_symbol": self.benchmark_symbol,
        }

    @property
    def required_history(self) -> int:
        return 210  # Needs 200-MA + lookback buffer

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent]:
        """Evaluate strategy across universe at current_date Close."""
        universe_members = data_portal.get_universe_members(current_date)
        signals: list[SignalIntent] = []
        for inst in universe_members:
            sig = self.evaluate_instrument(inst.id, current_date, data_portal)
            if sig:
                signals.append(sig)
        signals.sort(key=lambda s: float(s.confidence), reverse=True)
        return signals

    def evaluate_instrument(
        self,
        instrument_id: uuid.UUID,
        current_date: date,
        data_portal: DataPortal,
        benchmark_id: uuid.UUID | None = None,
    ) -> SignalIntent | None:
        """Evaluate single instrument for Trend Pullback entry setup."""
        # 1. Fetch price history
        history = data_portal.get_history(instrument_id, current_date, self.required_history)
        if len(history) < 200:
            return None

        closes = [Decimal(str(b["close"])) for b in history]
        highs = [Decimal(str(b["high"])) for b in history]
        lows = [Decimal(str(b["low"])) for b in history]

        current_close = closes[-1]
        current_low = lows[-1]
        prev_high = highs[-2]

        # 2. Indicators
        sma_20 = indicators.calculate_sma(closes, 20)
        sma_50 = indicators.calculate_sma(closes, self.trend_ma)
        sma_200 = indicators.calculate_sma(closes, 200)
        atr_14 = indicators.calculate_atr(highs, lows, closes, 14)
        rsi_14 = indicators.calculate_rsi(closes, 14)

        if (
            sma_20[-1] is None
            or sma_50[-1] is None
            or sma_200[-1] is None
            or atr_14[-1] is None
            or rsi_14[-1] is None
        ):
            return None

        c_sma_50 = sma_50[-1]
        c_sma_200 = sma_200[-1]
        c_sma_20 = sma_20[-1]
        c_atr_14 = atr_14[-1]
        c_rsi_14 = rsi_14[-1]

        assert c_sma_50 is not None and c_sma_200 is not None and c_sma_20 is not None
        assert c_atr_14 is not None and c_rsi_14 is not None

        # Benchmark filter check if provided
        if benchmark_id:
            bench_history = data_portal.get_history(benchmark_id, current_date, 60)
            if len(bench_history) >= 50:
                bench_closes = [Decimal(str(b["close"])) for b in bench_history]
                bench_sma = indicators.calculate_sma(bench_closes, 50)
                if bench_sma[-1] is not None and bench_closes[-1] < bench_sma[-1]:
                    return None  # Benchmark below 50-MA

        # 3. Established Trend
        if not (current_close > c_sma_50 and c_sma_50 > c_sma_200):
            return None

        # 4. Controlled Pullback
        atr_dist = abs(current_close - c_sma_20)
        is_pullback = (atr_dist <= (Decimal(str(self.pullback_atr_dist)) * c_atr_14)) or (
            c_rsi_14 <= Decimal(str(self.rsi_trigger))
        )
        if not is_pullback:
            return None

        # 5. Structure Intact
        if current_low <= c_sma_50:
            return None

        # 6. Resumption / Confirmation (Close > Previous High)
        if current_close <= prev_high:
            return None

        # 7. Deterministic Stop Loss Selection (min of Low_pullback vs Entry - 2*ATR)
        low_pullback = min([b["low"] for b in history[-3:]])
        atr_stop_level = current_close - (Decimal(str(self.atr_stop_mult)) * c_atr_14)
        stop_level = min(low_pullback, atr_stop_level)

        # 8. Family-Specific Setup Quality Score
        quality_score = (
            (current_close - current_low) / c_atr_14 if c_atr_14 > Decimal("0") else Decimal("0.5")
        )

        return SignalIntent(
            instrument_id=instrument_id,
            direction="BUY",
            order_type="MARKET",
            stop_loss_level=stop_level,
            confidence=quality_score,
            rationale="Trend Pullback setup confirmed",
            metadata={
                "family": "trend_pullback",
                "setup_quality_score": float(quality_score),
                "stop_loss_level": float(stop_level),
            },
        )
