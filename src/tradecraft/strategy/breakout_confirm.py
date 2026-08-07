"""Family B: Breakout + Confirmation Strategy.

Hypothesis: Securities emerging from multi-session consolidation ranges
demonstrate strong continuation when accompanied by volume and volatility expansion.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.features import indicators
from tradecraft.strategy.base import SignalIntent


class BreakoutConfirmStrategy:
    """Strategy Family B: Breakout + Confirmation."""

    def __init__(
        self,
        channel_period: int = 20,
        rvol_min: float = 1.5,
        max_consolidation_pct: float = 0.12,
        atr_stop_mult: float = 1.5,
    ):
        self.channel_period = channel_period
        self.rvol_min = rvol_min
        self.max_consolidation_pct = max_consolidation_pct
        self.atr_stop_mult = atr_stop_mult

    @property
    def strategy_id(self) -> str:
        return "strat_breakout_confirm"

    @property
    def name(self) -> str:
        return "Breakout Confirmation Strategy"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Point-in-time Donchian breakout strategy with RVOL and volatility expansion."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "channel_period": self.channel_period,
            "rvol_min": self.rvol_min,
            "max_consolidation_pct": self.max_consolidation_pct,
            "atr_stop_mult": self.atr_stop_mult,
        }

    @property
    def required_history(self) -> int:
        return self.channel_period + 30

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
    ) -> SignalIntent | None:
        """Evaluate single instrument for Breakout setup at session T Close."""
        history = data_portal.get_history(instrument_id, current_date, self.required_history)
        if len(history) < self.channel_period + 1:
            return None

        closes = [Decimal(str(b["close"])) for b in history]
        highs = [Decimal(str(b["high"])) for b in history]
        lows = [Decimal(str(b["low"])) for b in history]
        volumes = [Decimal(str(b["volume"])) for b in history]

        current_close = closes[-1]

        # 1. Point-in-Time Channel calculation EXCLUDING current bar T (uses T-N ... T-1)
        prior_highs = highs[-self.channel_period - 1 : -1]
        prior_lows = lows[-self.channel_period - 1 : -1]

        channel_high = max(prior_highs)
        channel_low = min(prior_lows)
        channel_middle = (channel_high + channel_low) / Decimal("2.0")

        # 2. Consolidation Filter
        if channel_high <= channel_low or current_close <= Decimal("0"):
            return None
        consolidation_width = (channel_high - channel_low) / current_close
        if consolidation_width > Decimal(str(self.max_consolidation_pct)):
            return None

        # 3. Breakout Signal at T Close
        if current_close <= channel_high:
            return None

        # 4. Volume & Volatility Confirmation
        rvol = indicators.calculate_rvol(volumes, 20)
        atr_14 = indicators.calculate_atr(highs, lows, closes, 14)
        if rvol[-1] is None or atr_14[-1] is None:
            return None

        c_rvol = rvol[-1]
        c_atr = atr_14[-1]
        assert c_rvol is not None and c_atr is not None

        if c_rvol < Decimal(str(self.rvol_min)):
            return None

        # 5. Deterministic Stop Loss Selection (min of Donchian Middle vs Entry - 1.5*ATR)
        atr_stop_level = current_close - (Decimal(str(self.atr_stop_mult)) * c_atr)
        stop_level = min(channel_middle, atr_stop_level)

        # 6. Family-Specific Setup Quality Score (Breakout Strength * RVOL)
        breakout_dist = (
            (current_close - channel_high) / c_atr if c_atr > Decimal("0") else Decimal("0.5")
        )
        quality_score = breakout_dist * c_rvol

        return SignalIntent(
            instrument_id=instrument_id,
            direction="BUY",
            order_type="MARKET",
            stop_loss_level=stop_level,
            confidence=quality_score,
            rationale="Breakout + RVOL confirmation",
            metadata={
                "family": "breakout_confirm",
                "breakout_bar_open": float(history[-1]["open"]),
                "channel_high": float(channel_high),
                "setup_quality_score": float(quality_score),
                "stop_loss_level": float(stop_level),
            },
        )
