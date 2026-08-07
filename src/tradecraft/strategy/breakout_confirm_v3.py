"""Breakout Confirmation V3 Strategy Definition for Milestone M3B.4."""

from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.research.m3b_4_hypothesis import V3ParameterOrigin
from tradecraft.strategy.base import SignalIntent
from tradecraft.strategy.v2_strategies import BaseV2Strategy

logger = logging.getLogger(__name__)


class BreakoutConfirmV3Strategy(BaseV2Strategy):
    """Strategy Family B V3: Breakout Confirmation with Squeeze Filter & Multi-Session Close Confirmation."""

    def __init__(
        self,
        channel_period: int = 20,
        max_consolidation_pct: float = 0.15,
        confirmation_sessions: int = 2,
        rvol_min: float = 1.2,
        atr_stop_mult: float = 2.0,
    ):
        self.channel_period = channel_period
        self.max_consolidation_pct = max_consolidation_pct
        self.confirmation_sessions = confirmation_sessions
        self.rvol_min = rvol_min
        self.atr_stop_mult = atr_stop_mult

    @property
    def strategy_id(self) -> str:
        return "strat_breakout_confirm_v3"

    @property
    def name(self) -> str:
        return "Breakout Confirmation V3 Strategy"

    @property
    def version(self) -> str:
        return "3.0.0"

    @property
    def parent_strategy_id(self) -> str:
        return "strat_breakout_confirm_v2"

    @property
    def hypothesis_statement(self) -> str:
        return (
            "HYPOTHESIS V3: Stocks emerging from a 20-day tight consolidation squeeze (width <= 15%) that achieve "
            "a 2-session Donchian 20-day high Close confirmation with RVOL >= 1.2 filter false breakout noise, "
            "improving trend continuation quality and reducing execution cost erosion."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            "V2 suffered 49.1% transaction cost erosion due to single-bar intra-day breakout noise. V3 narrows "
            "consolidation width to 15% to target genuine volatility squeezes and requires a 2-session Close confirmation."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "channel_period": self.channel_period,
            "max_consolidation_pct": self.max_consolidation_pct,
            "confirmation_sessions": self.confirmation_sessions,
            "rvol_min": self.rvol_min,
            "atr_stop_mult": self.atr_stop_mult,
        }

    @property
    def v3_parameter_origins(self) -> list[V3ParameterOrigin]:
        return [
            V3ParameterOrigin(
                parameter_name="channel_period",
                v2_value=20,
                v3_value=self.channel_period,
                provenance="INHERITED_FROM_V2",
                alternatives_tested=False,
                pnl_used_to_select=False,
                justification="Classic 20-day Donchian channel period preserved from V2.",
            ),
            V3ParameterOrigin(
                parameter_name="max_consolidation_pct",
                v2_value=0.20,
                v3_value=self.max_consolidation_pct,
                provenance="POST_HOC_DIAGNOSTIC_MOTIVATED",
                alternatives_tested=False,
                pnl_used_to_select=False,
                justification="Tightened from 20% to 15% based on diagnostic observation of false breakouts in wide channels; alternative values were not tested.",
            ),
            V3ParameterOrigin(
                parameter_name="confirmation_sessions",
                v2_value=1,
                v3_value=self.confirmation_sessions,
                provenance="ECONOMICALLY_DERIVED",
                alternatives_tested=False,
                pnl_used_to_select=False,
                justification="2-session Close confirmation above Donchian high ensures sustained institutional buying before entry.",
            ),
            V3ParameterOrigin(
                parameter_name="rvol_min",
                v2_value=1.2,
                v3_value=self.rvol_min,
                provenance="INHERITED_FROM_V2",
                alternatives_tested=False,
                pnl_used_to_select=False,
                justification="RVOL >= 1.2 preserved from V2 canonical definition.",
            ),
            V3ParameterOrigin(
                parameter_name="atr_stop_mult",
                v2_value=1.5,
                v3_value=self.atr_stop_mult,
                provenance="RISK_MODEL_DERIVED",
                alternatives_tested=False,
                pnl_used_to_select=False,
                justification="Increased to 2.0 ATR to accommodate normal breakout re-test noise without early stop-out.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return 60

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent]:
        universe_members = data_portal.get_universe_members(current_date)
        signals: list[SignalIntent] = []

        for inst in universe_members:
            bars = data_portal.get_history(inst.id, current_date, count=self.required_history)
            if len(bars) < 35:
                continue

            highs = [float(b["high"]) for b in bars]
            lows = [float(b["low"]) for b in bars]
            closes = [float(b["close"]) for b in bars]
            volumes = [float(b["volume"]) for b in bars]

            c_curr = closes[-1]
            c_prev = closes[-2]

            donchian20_high_prev = max(highs[-22:-2])
            donchian20_low_prev = min(lows[-22:-2])

            consolidation_w = (donchian20_high_prev - donchian20_low_prev) / max(
                1.0, donchian20_low_prev
            )
            avg_vol20 = sum(volumes[-22:-2]) / 20.0
            rvol = volumes[-1] / max(1.0, avg_vol20)

            # Rule 1: Consolidation width <= 15%
            is_tight = consolidation_w <= self.max_consolidation_pct
            # Rule 2: 2-session Close confirmation above previous Donchian high
            is_confirmed_breakout = (c_curr >= donchian20_high_prev) and (
                c_prev >= donchian20_high_prev
            )
            # Rule 3: Volume expansion
            is_vol = rvol >= self.rvol_min

            if is_tight and is_confirmed_breakout and is_vol:
                tr_list = [
                    max(
                        highs[i] - lows[i],
                        abs(highs[i] - closes[i - 1]),
                        abs(lows[i] - closes[i - 1]),
                    )
                    for i in range(-14, 0)
                ]
                atr14 = sum(tr_list) / 14.0

                stop_price = Decimal(str(round(c_curr - (atr14 * self.atr_stop_mult), 2)))
                signals.append(
                    SignalIntent(
                        instrument_id=inst.id,
                        direction="BUY",
                        order_type="MARKET",
                        stop_loss_level=stop_price,
                        metadata={
                            "strategy_name": self.name,
                            "strategy_version": self.version,
                            "signal_date": current_date.isoformat(),
                            "donchian20_high": donchian20_high_prev,
                            "consolidation_w": consolidation_w,
                            "rvol": rvol,
                            "config_hash": self.config_hash,
                        },
                    )
                )

        return signals
