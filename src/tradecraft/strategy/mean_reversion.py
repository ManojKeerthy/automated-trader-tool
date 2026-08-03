"""Family D: Mean Reversion Strategy.

Hypothesis: Equities in long-term structural uptrends experiencing extreme,
short-term selling exhaustion will revert toward their medium-term moving average.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.features import indicators
from tradecraft.strategy.base import SignalIntent


class MeanReversionStrategy:
    """Strategy Family D: Mean Reversion."""

    def __init__(
        self,
        rsi_oversold: float = 30.0,
        displacement_atr: float = 2.0,
        max_holding_days: int = 8,
        atr_stop_mult: float = 1.5,
    ):
        self.rsi_oversold = rsi_oversold
        self.displacement_atr = displacement_atr
        self.max_holding_days = max_holding_days
        self.atr_stop_mult = atr_stop_mult

    @property
    def strategy_id(self) -> str:
        return "strat_mean_reversion"

    @property
    def name(self) -> str:
        return "Mean Reversion Strategy"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Oversold mean reversion strategy in long-term structural uptrends."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "rsi_oversold": self.rsi_oversold,
            "displacement_atr": self.displacement_atr,
            "max_holding_days": self.max_holding_days,
            "atr_stop_mult": self.atr_stop_mult,
        }

    @property
    def required_history(self) -> int:
        return 210  # Needs 200-MA

    def evaluate(self, current_date: date, data_portal: DataPortal) -> list[SignalIntent]:
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
        """Evaluate single instrument for Mean Reversion setup."""
        history = data_portal.get_history(instrument_id, current_date, self.required_history)
        if len(history) < 200:
            return None

        closes = [Decimal(str(b["close"])) for b in history]
        highs = [Decimal(str(b["high"])) for b in history]
        lows = [Decimal(str(b["low"])) for b in history]

        current_close = closes[-1]

        # Indicators
        sma_20 = indicators.calculate_sma(closes, 20)
        sma_200 = indicators.calculate_sma(closes, 200)
        atr_14 = indicators.calculate_atr(highs, lows, closes, 14)
        rsi_14 = indicators.calculate_rsi(closes, 14)

        if (
            sma_20[-1] is None
            or sma_200[-1] is None
            or atr_14[-1] is None
            or rsi_14[-1] is None
        ):
            return None

        c_sma20 = sma_20[-1]
        c_sma200 = sma_200[-1]
        c_atr = atr_14[-1]
        c_rsi = rsi_14[-1]

        assert c_sma20 is not None and c_sma200 is not None and c_atr is not None and c_rsi is not None

        # 1. Structural Uptrend Anchor
        if current_close <= c_sma200:
            return None

        # 2. Extreme Oversold Condition
        if c_rsi > Decimal(str(self.rsi_oversold)):
            return None

        displacement = c_sma20 - current_close
        if displacement < (Decimal(str(self.displacement_atr)) * c_atr):
            return None

        # 3. Deterministic Stop Loss Selection
        stop_level = current_close - (Decimal(str(self.atr_stop_mult)) * c_atr)

        # 4. Family-Specific Setup Quality Score (ATR-normalised displacement)
        quality_score = displacement / c_atr if c_atr > Decimal("0") else Decimal("0.5")

        return SignalIntent(
            instrument_id=instrument_id,
            direction="BUY",
            order_type="MARKET",
            stop_loss_level=stop_level,
            target_level=c_sma20,
            confidence=quality_score,
            rationale="Oversold mean reversion setup",
            metadata={
                "family": "mean_reversion",
                "max_holding_days": self.max_holding_days,
                "setup_quality_score": float(quality_score),
                "stop_loss_level": float(stop_level),
            },
        )
