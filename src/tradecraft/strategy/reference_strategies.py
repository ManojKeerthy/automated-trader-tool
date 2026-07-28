"""Reference Strategies for Backtest Engine Validation.

IMPORTANT:
All reference strategies are created SOLELY to validate the backtest
engine mechanics (signal timing, execution, accounting, metrics, costs).
They are NOT approved for live trading or production use.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.features import indicators
from tradecraft.strategy.base import ExitSignal, SignalIntent

# Mandatory disclaimer label for all reference strategies
REFERENCE_DISCLAIMER = "REFERENCE / TEST STRATEGY — NOT APPROVED FOR LIVE TRADING"


class BuyAndHoldStrategy:
    """Simple Buy-and-Hold Reference Strategy.

    Buys the first available member of the universe on the first session
    and holds until the end of the backtest.
    Used to validate basic portfolio accounting and trade ledgering.
    """

    def __init__(self, target_instrument_id: uuid.UUID | None = None):
        self._target_id = target_instrument_id
        self._bought = False

    @property
    def strategy_id(self) -> str:
        return "ref_buy_and_hold"

    @property
    def name(self) -> str:
        return "Reference Buy & Hold"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return f"Buy and hold reference strategy. {REFERENCE_DISCLAIMER}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"target_id": str(self._target_id) if self._target_id else None}

    @property
    def required_history(self) -> int:
        return 1

    def evaluate(self, current_date: date, data_portal: DataPortal) -> list[SignalIntent | ExitSignal]:
        if self._bought:
            return []

        members = data_portal.get_universe_members(current_date)
        if not members:
            return []

        target_inst = None
        if self._target_id:
            target_inst = next((m for m in members if m.id == self._target_id), None)
        else:
            target_inst = members[0]

        if not target_inst:
            return []

        close_price = data_portal.get_close(target_inst.id, current_date)
        if close_price is None:
            return []

        self._bought = True
        return [
            SignalIntent(
                instrument_id=target_inst.id,
                direction="BUY",
                order_type="MARKET",
                quantity_hint=10,
                confidence=Decimal("1.0"),
                rationale=f"Reference buy and hold entry on {current_date}",
            )
        ]


class SMACrossoverStrategy:
    """Simple SMA Crossover Reference Strategy.

    Enters BUY when Fast SMA > Slow SMA.
    Exits when Fast SMA < Slow SMA.
    Used to validate indicator calculation, signal timing, and exit processing.
    """

    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self._positions: set[uuid.UUID] = set()

    @property
    def strategy_id(self) -> str:
        return "ref_sma_crossover"

    @property
    def name(self) -> str:
        return "Reference SMA Crossover"

    @property
    def version(self) -> str:
        return f"1.0.0-sma_{self.fast_period}_{self.slow_period}"

    @property
    def description(self) -> str:
        return f"Moving average crossover test strategy. {REFERENCE_DISCLAIMER}"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"fast_period": self.fast_period, "slow_period": self.slow_period}

    @property
    def required_history(self) -> int:
        return self.slow_period + 1

    def evaluate(self, current_date: date, data_portal: DataPortal) -> list[SignalIntent | ExitSignal]:
        signals: list[SignalIntent | ExitSignal] = []
        members = data_portal.get_universe_members(current_date)

        for inst in members:
            df = data_portal.get_bars(inst.id, current_date, lookback=self.slow_period + 5)
            if len(df) < self.slow_period + 1:
                continue

            closes = df["close"].astype(float)
            fast_sma = indicators.sma(closes, self.fast_period)
            slow_sma = indicators.sma(closes, self.slow_period)

            if len(fast_sma) < 2 or len(slow_sma) < 2:
                continue

            curr_fast, prev_fast = fast_sma.iloc[-1], fast_sma.iloc[-2]
            curr_slow, prev_slow = slow_sma.iloc[-1], slow_sma.iloc[-2]

            # Bullish crossover: Fast crosses above Slow
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                if inst.id not in self._positions:
                    self._positions.add(inst.id)
                    signals.append(
                        SignalIntent(
                            instrument_id=inst.id,
                            direction="BUY",
                            order_type="MARKET",
                            quantity_hint=5,
                            stop_loss_level=Decimal(str(closes.iloc[-1] * 0.95)),  # 5% stop
                            target_level=Decimal(str(closes.iloc[-1] * 1.10)),  # 10% target
                            rationale=f"SMA crossover ({self.fast_period}/{self.slow_period})",
                        )
                    )

            # Bearish crossover: Fast crosses below Slow
            elif prev_fast >= prev_slow and curr_fast < curr_slow and inst.id in self._positions:
                self._positions.remove(inst.id)
                signals.append(
                    ExitSignal(
                        instrument_id=inst.id,
                        exit_type="MARKET",
                        reason="SMA Bearish Crossover",
                    )
                )

        return signals
