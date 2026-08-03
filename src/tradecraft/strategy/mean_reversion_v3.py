"""Mean Reversion V3 Strategy Definition for Milestone M3B.4."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.research.m3b_4_hypothesis import V3ParameterOrigin
from tradecraft.strategy.base import SignalIntent
from tradecraft.strategy.v2_strategies import BaseV2Strategy

logger = logging.getLogger(__name__)


class MeanReversionV3Strategy(BaseV2Strategy):
    """Strategy Family D V3: Reversal-Triggered Oversold Mean Reversion in Uptrends."""

    def __init__(
        self,
        rsi_oversold: float = 35.0,
        displacement_atr: float = 1.0,
        max_holding_days: int = 7,
        atr_stop_mult: float = 1.5,
    ):
        self.rsi_oversold = rsi_oversold
        self.displacement_atr = displacement_atr
        self.max_holding_days = max_holding_days
        self.atr_stop_mult = atr_stop_mult

    @property
    def strategy_id(self) -> str:
        return "strat_mean_reversion_v3"

    @property
    def name(self) -> str:
        return "Mean Reversion V3 Strategy"

    @property
    def version(self) -> str:
        return "3.0.0"

    @property
    def parent_strategy_id(self) -> str:
        return "strat_mean_reversion_v2"

    @property
    def hypothesis_statement(self) -> str:
        return (
            "HYPOTHESIS V3: Stocks in structural uptrends (Close > SMA200) experiencing an oversold dip (RSI(5) <= 35.0) "
            "with displacement >= 1.0 ATR that exhibit a 1-day bullish reversal trigger (Close > Prev Close) eliminate "
            "falling-knife entries, improving win rate and elevating Expectancy R above +0.25R."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            "V2 suffered low win rate (10.8%) due to entering during unconfirmed falling legs. V3 adds a 1-day bullish "
            "reversal candle trigger (Close > Prev Close), tightens RSI(5) to 35.0, and extends max holding period from 5 to 7 sessions."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "rsi_oversold": self.rsi_oversold,
            "displacement_atr": self.displacement_atr,
            "max_holding_days": self.max_holding_days,
            "atr_stop_mult": self.atr_stop_mult,
        }

    @property
    def v3_parameter_origins(self) -> list[V3ParameterOrigin]:
        return [
            V3ParameterOrigin(
                parameter_name="rsi_oversold",
                v2_value=40.0,
                v3_value=self.rsi_oversold,
                provenance="POST_HOC_DIAGNOSTIC_MOTIVATED",
                alternatives_tested=False,
                pnl_used_to_select=False,
                justification="Tightened from 40.0 to 35.0 to select deeper short-term pullbacks; alternative values were not tested.",
            ),
            V3ParameterOrigin(
                parameter_name="displacement_atr",
                v2_value=1.0,
                v3_value=self.displacement_atr,
                provenance="INHERITED_FROM_V2",
                alternatives_tested=False,
                pnl_used_to_select=False,
                justification="1.0 ATR displacement preserved from V2 canonical definition.",
            ),
            V3ParameterOrigin(
                parameter_name="reversal_confirmation",
                v2_value="None",
                v3_value="1-session Close > Prev Close",
                provenance="ECONOMICALLY_DERIVED",
                alternatives_tested=False,
                pnl_used_to_select=False,
                justification="1-session bullish candle reversal trigger ensures price has stopped falling before entry.",
            ),
            V3ParameterOrigin(
                parameter_name="max_holding_days",
                v2_value=5,
                v3_value=self.max_holding_days,
                provenance="ECONOMICALLY_DERIVED",
                alternatives_tested=False,
                pnl_used_to_select=False,
                justification="Extended from 5 to 7 sessions to allow mean reversion to complete to SMA20 baseline.",
            ),
            V3ParameterOrigin(
                parameter_name="atr_stop_mult",
                v2_value=1.5,
                v3_value=self.atr_stop_mult,
                provenance="INHERITED_FROM_V2",
                alternatives_tested=False,
                pnl_used_to_select=False,
                justification="1.5 ATR stop loss placement preserved from V2 canonical definition.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return 210

    def evaluate(self, current_date: date, data_portal: DataPortal) -> list[SignalIntent]:
        universe_members = data_portal.get_universe_members(current_date)
        signals: list[SignalIntent] = []

        for inst in universe_members:
            bars = data_portal.get_history(inst.id, current_date, count=self.required_history)
            if len(bars) < 200:
                continue

            closes = [float(b["close"]) for b in bars]
            highs = [float(b["high"]) for b in bars]
            lows = [float(b["low"]) for b in bars]

            c_curr = closes[-1]
            c_prev = closes[-2]
            sma200 = sum(closes[-200:]) / 200.0
            sma20 = sum(closes[-20:]) / 20.0

            tr_list = [
                max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
                for i in range(-14, 0)
            ]
            atr14 = sum(tr_list) / 14.0

            # RSI 5
            gains5 = [max(0.0, closes[i] - closes[i - 1]) for i in range(-5, 0)]
            losses5 = [max(0.0, closes[i - 1] - closes[i]) for i in range(-5, 0)]
            rs5 = (sum(gains5) / 5.0) / max(0.0001, (sum(losses5) / 5.0))
            rsi5 = 100.0 - (100.0 / (1.0 + rs5))

            is_uptrend = c_curr > sma200
            is_oversold = rsi5 <= self.rsi_oversold
            is_displaced = (sma20 - c_curr) / max(0.1, atr14) >= self.displacement_atr
            # Bullish reversal trigger: Close > Prev Close
            is_reversal = c_curr > c_prev

            if is_uptrend and is_oversold and is_displaced and is_reversal:
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
                            "rsi5": rsi5,
                            "displacement_atr": (sma20 - c_curr) / max(0.1, atr14),
                            "max_holding_days": self.max_holding_days,
                            "config_hash": self.config_hash,
                        },
                    )
                )

        return signals
