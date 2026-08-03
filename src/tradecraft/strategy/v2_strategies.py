"""Phase B: V2 Hypothesis Strategy Definitions & Immutable Lineage for M3B.2.

Defines the 4 new V2 strategy families with sequential state transitions, immutable parent metadata,
SHA256 configuration hashes, plain-language hypotheses, and parameter origin tracking.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from tradecraft.backtesting.data_portal import DataPortal
from tradecraft.strategy.base import SignalIntent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParameterOrigin:
    parameter_name: str
    value: Any
    origin_category: str  # ECONOMIC_RATIONALE, MARKET_CONVENTION, PRIOR_CANONICAL, STRUCTURAL_REQUIREMENT, SIGNAL_VIABILITY_CALIBRATION
    justification: str


@dataclass(frozen=True)
class V2StrategyLineage:
    strategy_id: str
    strategy_name: str
    strategy_version: str
    parent_strategy_id: str
    config_hash: str
    hypothesis_statement: str
    revision_rationale: str
    parameter_origins: list[ParameterOrigin]


class BaseV2Strategy:
    """Base class for all immutable V2 strategy definitions."""

    @property
    def strategy_id(self) -> str:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def description(self) -> str:
        return self.hypothesis_statement

    @property
    def required_history(self) -> int:
        return 70

    def evaluate(self, current_date: date, data_portal: DataPortal) -> list[SignalIntent]:
        raise NotImplementedError

    @property
    def parent_strategy_id(self) -> str:
        raise NotImplementedError

    @property
    def hypothesis_statement(self) -> str:
        raise NotImplementedError

    @property
    def revision_rationale(self) -> str:
        raise NotImplementedError

    @property
    def parameters(self) -> dict[str, Any]:
        raise NotImplementedError

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        raise NotImplementedError

    @property
    def config_hash(self) -> str:
        param_str = json.dumps(self.parameters, sort_keys=True)
        content = f"{self.strategy_id}:{self.version}:{param_str}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_lineage(self) -> V2StrategyLineage:
        return V2StrategyLineage(
            strategy_id=self.strategy_id,
            strategy_name=self.name,
            strategy_version=self.version,
            parent_strategy_id=self.parent_strategy_id,
            config_hash=self.config_hash,
            hypothesis_statement=self.hypothesis_statement,
            revision_rationale=self.revision_rationale,
            parameter_origins=self.parameter_origins,
        )


class TrendPullbackV2Strategy(BaseV2Strategy):
    """Strategy Family A V2: Trend Pullback with Sequential State Transitions."""

    def __init__(
        self,
        trend_ma: int = 50,
        pullback_ema: int = 20,
        atr_dist_max: float = 2.0,
        atr_stop_mult: float = 2.0,
    ):
        self.trend_ma = trend_ma
        self.pullback_ema = pullback_ema
        self.atr_dist_max = atr_dist_max
        self.atr_stop_mult = atr_stop_mult

    @property
    def strategy_id(self) -> str:
        return "strat_trend_pullback_v2"

    @property
    def name(self) -> str:
        return "Trend Pullback V2 Strategy"

    @property
    def parent_strategy_id(self) -> str:
        return "strat_trend_pullback"

    @property
    def hypothesis_statement(self) -> str:
        return (
            "HYPOTHESIS V2: Stocks in established medium-term uptrends (Close > SMA50) that experience "
            "orderly pullbacks toward their 20-period EMA baseline and subsequently exhibit a daily price resumption "
            "trigger (Close > Previous Day High) offer positive continuation expectancy with deterministic ATR stop placement."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            "V1 canonical failure was caused by requiring simultaneous RSI <= 45 AND tight ATR distance AND SMA50 alignment "
            "on a single bar. V2 separates structural trend context from sequential pullback and resumption trigger states."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "trend_ma": self.trend_ma,
            "pullback_ema": self.pullback_ema,
            "atr_dist_max": self.atr_dist_max,
            "atr_stop_mult": self.atr_stop_mult,
        }

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        return [
            ParameterOrigin(
                "trend_ma",
                self.trend_ma,
                "MARKET_CONVENTION",
                "Standard 50-day moving average medium-term trend benchmark.",
            ),
            ParameterOrigin(
                "pullback_ema",
                self.pullback_ema,
                "ECONOMIC_RATIONALE",
                "EMA20 represents fast institutional trend support baseline.",
            ),
            ParameterOrigin(
                "atr_dist_max",
                self.atr_dist_max,
                "SIGNAL_VIABILITY_CALIBRATION",
                "2.0 ATR distance prevents over-filtering during pullback.",
            ),
            ParameterOrigin(
                "atr_stop_mult",
                self.atr_stop_mult,
                "PRIOR_CANONICAL",
                "Preserved 2.0 ATR stop loss placement from canonical V1.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return 70

    def evaluate(self, current_date: date, data_portal: DataPortal) -> list[SignalIntent]:
        """Evaluate V2 strategy across universe at current_date Close."""
        universe_members = data_portal.get_universe_members(current_date)
        signals: list[SignalIntent] = []

        for inst in universe_members:
            bars = data_portal.get_history(inst.id, current_date, count=self.required_history)
            if len(bars) < 55:
                continue

            closes = [float(b["close"]) for b in bars]
            highs = [float(b["high"]) for b in bars]
            lows = [float(b["low"]) for b in bars]

            c_curr = closes[-1]
            c_prev = closes[-2]
            h_prev = highs[-2]

            sma50 = sum(closes[-50:]) / 50.0

            # EMA 20
            k = 2.0 / 21.0
            ema20 = closes[-20]
            for c in closes[-19:]:
                ema20 = (c * k) + (ema20 * (1.0 - k))

            # ATR 14
            tr_list = [
                max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
                for i in range(-14, 0)
            ]
            atr14 = sum(tr_list) / 14.0

            # State 1: Structural uptrend
            state1_trend = c_curr > sma50
            # State 2: Pullback near EMA20
            state2_pullback = abs(c_prev - ema20) / max(0.1, atr14) <= self.atr_dist_max
            # State 3: Resumption trigger
            state3_resumption = c_curr > h_prev

            if state1_trend and state2_pullback and state3_resumption:
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
                            "entry_price": float(c_curr),
                            "sma50": sma50,
                            "ema20": ema20,
                            "atr14": atr14,
                            "config_hash": self.config_hash,
                        },
                    )
                )

        return signals


class BreakoutConfirmV2Strategy(BaseV2Strategy):
    """Strategy Family B V2: Breakout Confirmation with ATR-Normalized Consolidation."""

    def __init__(
        self,
        channel_period: int = 20,
        max_consolidation_pct: float = 0.20,
        rvol_min: float = 1.2,
        atr_stop_mult: float = 1.5,
    ):
        self.channel_period = channel_period
        self.max_consolidation_pct = max_consolidation_pct
        self.rvol_min = rvol_min
        self.atr_stop_mult = atr_stop_mult

    @property
    def strategy_id(self) -> str:
        return "strat_breakout_confirm_v2"

    @property
    def name(self) -> str:
        return "Breakout Confirmation V2 Strategy"

    @property
    def parent_strategy_id(self) -> str:
        return "strat_breakout_confirm"

    @property
    def hypothesis_statement(self) -> str:
        return (
            "HYPOTHESIS V2: Stocks emerging from a 20-day channel consolidation width <= 20% that achieve "
            "a point-in-time Donchian 20-day high breakout with RVOL >= 1.2 exhibit positive continuation momentum."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            "V1 12% consolidation filter was overly restrictive across Indian large-caps. V2 expands consolidation "
            "tolerance to 20% and uses RVOL >= 1.2."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "channel_period": self.channel_period,
            "max_consolidation_pct": self.max_consolidation_pct,
            "rvol_min": self.rvol_min,
            "atr_stop_mult": self.atr_stop_mult,
        }

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        return [
            ParameterOrigin(
                "channel_period",
                self.channel_period,
                "MARKET_CONVENTION",
                "Classic 20-day Donchian channel period.",
            ),
            ParameterOrigin(
                "max_consolidation_pct",
                self.max_consolidation_pct,
                "SIGNAL_VIABILITY_CALIBRATION",
                "20% width accommodates normal Nifty volatility squeezes.",
            ),
            ParameterOrigin(
                "rvol_min",
                self.rvol_min,
                "ECONOMIC_RATIONALE",
                "RVOL >= 1.2 ensures moderate volume expansion without over-filtering.",
            ),
            ParameterOrigin(
                "atr_stop_mult",
                self.atr_stop_mult,
                "PRIOR_CANONICAL",
                "Preserved 1.5 ATR stop loss placement from canonical V1.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return 50

    def evaluate(self, current_date: date, data_portal: DataPortal) -> list[SignalIntent]:
        universe_members = data_portal.get_universe_members(current_date)
        signals: list[SignalIntent] = []

        for inst in universe_members:
            bars = data_portal.get_history(inst.id, current_date, count=self.required_history)
            if len(bars) < 30:
                continue

            highs = [float(b["high"]) for b in bars]
            lows = [float(b["low"]) for b in bars]
            closes = [float(b["close"]) for b in bars]
            volumes = [float(b["volume"]) for b in bars]

            c_curr = closes[-1]
            h_curr = highs[-1]

            donchian20_high_prev = max(highs[-21:-1])
            donchian20_low_prev = min(lows[-21:-1])

            consolidation_w = (donchian20_high_prev - donchian20_low_prev) / max(
                1.0, donchian20_low_prev
            )
            avg_vol20 = sum(volumes[-21:-1]) / 20.0
            rvol = volumes[-1] / max(1.0, avg_vol20)

            # Point-in-time PIT Donchian breakout (High >= prev 20-day high)
            is_breakout = h_curr >= donchian20_high_prev
            is_tight = consolidation_w <= self.max_consolidation_pct
            is_vol = rvol >= self.rvol_min

            if is_breakout and is_tight and is_vol:
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


class MomentumRSV2Strategy(BaseV2Strategy):
    """Strategy Family C V2: Momentum RS with Top 25% Cutoff."""

    def __init__(
        self,
        rs_lookback: int = 63,
        top_percentile_cutoff: float = 0.25,
        atr_stop_mult: float = 2.5,
    ):
        self.rs_lookback = rs_lookback
        self.top_percentile_cutoff = top_percentile_cutoff
        self.atr_stop_mult = atr_stop_mult

    @property
    def strategy_id(self) -> str:
        return "strat_momentum_rs_v2"

    @property
    def name(self) -> str:
        return "Momentum Relative Strength V2 Strategy"

    @property
    def parent_strategy_id(self) -> str:
        return "strat_momentum_rs"

    @property
    def hypothesis_statement(self) -> str:
        return (
            "HYPOTHESIS V2: Stocks ranking in the top 25th percentile of 63-day relative strength performance "
            "when benchmark trend is bullish exhibit trend continuation edge."
        )

    @property
    def revision_rationale(self) -> str:
        return "V1 10% cutoff was overly restrictive daily. V2 expands RS cutoff to top 25%."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "rs_lookback": self.rs_lookback,
            "top_percentile_cutoff": self.top_percentile_cutoff,
            "atr_stop_mult": self.atr_stop_mult,
        }

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        return [
            ParameterOrigin(
                "rs_lookback",
                self.rs_lookback,
                "MARKET_CONVENTION",
                "Standard 3-month (63 trading session) momentum lookback.",
            ),
            ParameterOrigin(
                "top_percentile_cutoff",
                self.top_percentile_cutoff,
                "SIGNAL_VIABILITY_CALIBRATION",
                "Top 25% cutoff provides non-degenerate sample size.",
            ),
            ParameterOrigin(
                "atr_stop_mult",
                self.atr_stop_mult,
                "PRIOR_CANONICAL",
                "Preserved 2.5 ATR stop loss placement from canonical V1.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return 85

    def evaluate(self, current_date: date, data_portal: DataPortal) -> list[SignalIntent]:
        universe_members = data_portal.get_universe_members(current_date)
        signals: list[SignalIntent] = []

        # Collect 63-day returns for all stocks
        inst_returns: list[tuple[Any, float, list[dict[str, Any]]]] = []
        for inst in universe_members:
            bars = data_portal.get_history(inst.id, current_date, count=self.required_history)
            if len(bars) < 65:
                continue
            closes = [float(b["close"]) for b in bars]
            ret63 = (closes[-1] - closes[-64]) / max(1.0, closes[-64])
            inst_returns.append((inst.id, ret63, bars))

        if not inst_returns:
            return []

        # Rank returns
        inst_returns.sort(key=lambda x: x[1], reverse=True)
        top_count = max(1, int(len(inst_returns) * self.top_percentile_cutoff))
        top_group = inst_returns[:top_count]

        for inst_id, ret, bars in top_group:
            closes = [float(b["close"]) for b in bars]
            highs = [float(b["high"]) for b in bars]
            lows = [float(b["low"]) for b in bars]

            c_curr = closes[-1]
            tr_list = [
                max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
                for i in range(-14, 0)
            ]
            atr14 = sum(tr_list) / 14.0

            stop_price = Decimal(str(round(c_curr - (atr14 * self.atr_stop_mult), 2)))
            signals.append(
                SignalIntent(
                    instrument_id=inst_id,
                    direction="BUY",
                    order_type="MARKET",
                    stop_loss_level=stop_price,
                    metadata={
                        "strategy_name": self.name,
                        "strategy_version": self.version,
                        "signal_date": current_date.isoformat(),
                        "ret63": ret,
                        "rank_cutoff": top_count,
                        "config_hash": self.config_hash,
                    },
                )
            )

        return signals


class MeanReversionV2Strategy(BaseV2Strategy):
    """Strategy Family D V2: Moderated Oversold Mean Reversion."""

    def __init__(
        self,
        rsi_oversold: float = 40.0,
        displacement_atr: float = 1.0,
        max_holding_days: int = 5,
        atr_stop_mult: float = 1.5,
    ):
        self.rsi_oversold = rsi_oversold
        self.displacement_atr = displacement_atr
        self.max_holding_days = max_holding_days
        self.atr_stop_mult = atr_stop_mult

    @property
    def strategy_id(self) -> str:
        return "strat_mean_reversion_v2"

    @property
    def name(self) -> str:
        return "Mean Reversion V2 Strategy"

    @property
    def parent_strategy_id(self) -> str:
        return "strat_mean_reversion"

    @property
    def hypothesis_statement(self) -> str:
        return (
            "HYPOTHESIS V2: Stocks in long-term structural uptrends (Close > SMA200) experiencing a moderated "
            "short-term pullback (RSI(5) <= 40.0) with price displacement >= 1.0 ATR below SMA20 exhibit short-term mean reversion."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            "V1 RSI < 30 and 2.0 ATR displacement were overly severe and contradictory in structural uptrends. V2 moderates "
            "RSI to 40.0 and displacement to 1.0 ATR."
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
    def parameter_origins(self) -> list[ParameterOrigin]:
        return [
            ParameterOrigin(
                "rsi_oversold",
                self.rsi_oversold,
                "SIGNAL_VIABILITY_CALIBRATION",
                "RSI(5) <= 40.0 captures realistic pullbacks in bull trends.",
            ),
            ParameterOrigin(
                "displacement_atr",
                self.displacement_atr,
                "ECONOMIC_RATIONALE",
                "1.0 ATR displacement ensures non-trivial deviation from mean.",
            ),
            ParameterOrigin(
                "max_holding_days",
                self.max_holding_days,
                "STRUCTURAL_REQUIREMENT",
                "5-session time exit aligns with short-term mean reversion.",
            ),
            ParameterOrigin(
                "atr_stop_mult",
                self.atr_stop_mult,
                "PRIOR_CANONICAL",
                "Preserved 1.5 ATR stop loss placement from canonical V1.",
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

            if is_uptrend and is_oversold and is_displaced:
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
