"""Family C: Momentum / Relative Strength Strategy.

Hypothesis: Securities demonstrating persistent strength relative to the benchmark
continue to outperform over swing horizons due to institutional inflows.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.features import indicators
from tradecraft.strategy.base import SignalIntent


class MomentumRSStrategy:
    """Strategy Family C: Momentum / Relative Strength."""

    def __init__(
        self,
        rs_lookback: int = 63,
        top_percentile: float = 0.10,
        atr_stop_mult: float = 2.5,
    ):
        self.rs_lookback = rs_lookback
        self.top_percentile = top_percentile
        self.atr_stop_mult = atr_stop_mult

    @property
    def strategy_id(self) -> str:
        return "strat_momentum_rs"

    @property
    def name(self) -> str:
        return "Relative Strength Momentum Strategy"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Point-in-time relative strength momentum strategy vs market benchmark."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "rs_lookback": self.rs_lookback,
            "top_percentile": self.top_percentile,
            "atr_stop_mult": self.atr_stop_mult,
        }

    @property
    def required_history(self) -> int:
        return self.rs_lookback + 20

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
        """Evaluate single instrument for Momentum RS setup."""
        history = data_portal.get_history(instrument_id, current_date, self.required_history)
        if len(history) < self.rs_lookback:
            return None

        closes = [Decimal(str(b["close"])) for b in history]
        highs = [Decimal(str(b["high"])) for b in history]
        lows = [Decimal(str(b["low"])) for b in history]

        current_close = closes[-1]
        past_close = closes[-self.rs_lookback]

        if past_close <= Decimal("0"):
            return None

        stock_return = (current_close - past_close) / past_close

        # Calculate RS ratio relative to benchmark if available
        bench_return = Decimal("0.0")
        if benchmark_id:
            bench_history = data_portal.get_history(benchmark_id, current_date, self.rs_lookback)
            if len(bench_history) >= self.rs_lookback:
                b_curr = Decimal(str(bench_history[-1]["close"]))
                b_past = Decimal(str(bench_history[0]["close"]))
                if b_past > Decimal("0"):
                    bench_return = (b_curr - b_past) / b_past

        rs_score = stock_return - bench_return

        # Trend filter
        sma_50 = indicators.calculate_sma(closes, 50)
        atr_14 = indicators.calculate_atr(highs, lows, closes, 14)

        if sma_50[-1] is None or atr_14[-1] is None:
            return None

        c_sma = sma_50[-1]
        c_atr = atr_14[-1]
        assert c_sma is not None and c_atr is not None

        if current_close <= c_sma or rs_score <= Decimal("0"):
            return None

        # 5-day Rate of Change check
        roc_5 = indicators.calculate_roc(closes, 5)
        if roc_5[-1] is None or roc_5[-1] <= Decimal("0"):
            return None

        stop_level = current_close - (Decimal(str(self.atr_stop_mult)) * c_atr)

        return SignalIntent(
            instrument_id=instrument_id,
            direction="BUY",
            order_type="MARKET",
            stop_loss_level=stop_level,
            confidence=rs_score,
            rationale="Top relative strength momentum setup",
            metadata={
                "family": "momentum_rs",
                "rs_score": float(rs_score),
                "setup_quality_score": float(rs_score),
                "stop_loss_level": float(stop_level),
            },
        )
