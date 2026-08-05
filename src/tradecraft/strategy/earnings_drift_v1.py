"""Post-Earnings Announcement Drift (PEAD) V1 Strategy for Research Cycle 2.

Pre-registered hypothesis: hypo-cycle2-alpha013-v1 (ALPHA-013 Earnings Drift)
Lineage: Independent new lineage (Zero Graveyard collision).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from tradecraft.sdk.research_client import ResearchClient
from tradecraft.strategy.base import ExitSignal, SignalIntent

if TYPE_CHECKING:
    from tradecraft.backtesting.data_portal import DataPortal

logger = logging.getLogger(__name__)


@dataclass
class EarningsDriftV1Config:
    """Frozen parameters for EarningsDriftV1Strategy matching pre-registration."""

    holding_period_max_sessions: int = 30
    atr_stop_multiplier: Decimal = Decimal("2.0")
    min_volume_expansion_ratio: Decimal = Decimal("1.5")
    position_size_pct: Decimal = Decimal("0.10")


class EarningsDriftV1Strategy:
    """Strategy implementation of ALPHA-013 Earnings Drift (PEAD).

    Capitalizes on Post-Earnings Announcement Drift by identifying
    institutional volume expansion and positive price momentum post disclosure.
    """

    strategy_id: str = "strat_earnings_drift_v1"
    version: str = "1.0.0"
    hypothesis_uuid: str = "hypo-cycle2-alpha013-v1"

    @property
    def name(self) -> str:
        return self.strategy_id

    def __init__(
        self,
        config: EarningsDriftV1Config | None = None,
        research_client: ResearchClient | None = None,
    ) -> None:
        self.config = config or EarningsDriftV1Config()
        self.client = research_client or ResearchClient()
        self._entry_dates: dict[uuid.UUID, date] = {}
        self._bars_held: dict[uuid.UUID, int] = {}

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent | ExitSignal]:
        return self.generate_signals(current_date, data_portal, active_positions=active_positions)

    def generate_signals(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent | ExitSignal]:
        """Generate entry and exit signals for active universe securities on current_date."""
        signals: list[SignalIntent | ExitSignal] = []
        active_positions_set = set(active_positions or [])

        # Query Point-in-Time constituents from SDK, or fallback to active securities in DataPortal
        constituents = self.client.get_universe_constituents("NIFTY50", current_date)
        sec_uuids = [uuid.UUID(sec.security_uuid) for sec in constituents] if constituents else []

        if not sec_uuids:
            # Fallback to pre-loaded instrument UUIDs from DataPortal cache
            sec_uuids = list(data_portal._bars_cache.keys())

        if not sec_uuids:
            return signals

        for sec_uuid in sec_uuids:
            # Update holding period tracker for existing positions
            if sec_uuid in active_positions_set:
                self._bars_held[sec_uuid] = self._bars_held.get(sec_uuid, 0) + 1

                # Check Time-Based Exit (30 sessions max)
                if self._bars_held[sec_uuid] >= self.config.holding_period_max_sessions:
                    signals.append(
                        ExitSignal(
                            instrument_id=sec_uuid,
                            exit_type="MARKET",
                            reason="MAX_HOLDING_PERIOD",
                        )
                    )
                    del self._bars_held[sec_uuid]
                continue

            # Signal Generation Logic for non-active positions
            # Fetch daily bars via DataPortal
            history = data_portal.get_history(sec_uuid, end_date=current_date, count=20)
            if len(history) < 20:
                continue

            latest_bar = history[-1]
            prev_bar = history[-2]

            # 1. Price Momentum / Surge Condition
            close_price = Decimal(str(latest_bar["close"]))
            prev_close_price = Decimal(str(prev_bar["close"]))
            close_change = (close_price - prev_close_price) / prev_close_price
            if close_change < Decimal("0.015"):  # Min 1.5% positive move
                continue

            # 2. Institutional Volume Expansion Condition
            avg_volume = sum(Decimal(str(b["volume"])) for b in history[-20:-1]) / Decimal("19.0")
            latest_volume = Decimal(str(latest_bar["volume"]))
            if (
                avg_volume == Decimal("0")
                or (latest_volume / avg_volume) < self.config.min_volume_expansion_ratio
            ):
                continue

            # Calculate ATR protective stop level
            recent_ranges = [
                Decimal(str(b["high"])) - Decimal(str(b["low"])) for b in history[-14:]
            ]
            avg_atr = sum(recent_ranges) / Decimal(len(recent_ranges))
            stop_loss = close_price - (self.config.atr_stop_multiplier * avg_atr)

            # Emit BUY signal intent
            signals.append(
                SignalIntent(
                    instrument_id=sec_uuid,
                    direction="BUY",
                    order_type="MARKET",
                    stop_loss_level=stop_loss,
                    confidence=Decimal("0.80"),
                    rationale=f"PEAD entry trigger: {close_change * 100:.2f}% surge with {latest_volume} volume expansion.",
                )
            )

        return signals
