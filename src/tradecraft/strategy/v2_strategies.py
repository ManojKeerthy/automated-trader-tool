"""Phase B: V2 Hypothesis Strategy Definitions & Immutable Lineage for M3B.2.

Defines the 4 new V2 strategy families with sequential state transitions, immutable parent metadata,
SHA256 configuration hashes, plain-language hypotheses, and parameter origin tracking.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
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

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent]:
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
        max_holding_days: int = 20,
    ):
        self.trend_ma = trend_ma
        self.pullback_ema = pullback_ema
        self.atr_dist_max = atr_dist_max
        self.atr_stop_mult = atr_stop_mult
        self.max_holding_days = max_holding_days

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
            "max_holding_days": self.max_holding_days,
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
            ParameterOrigin(
                "max_holding_days",
                self.max_holding_days,
                "MARKET_CONVENTION",
                "ADDED 2026-08-06 (Phase B engine baseline gap - see PROJECT_STATUS.md "
                "section 4). Previously unset, so no time exit ever fired and winners rode "
                "uncapped to the literal end of the backtest window, producing implausible "
                "30x+ payoff ratios. 20 trading sessions (~4 weeks) matches the established "
                "swing-trading convention for pullback-continuation setups (commonly cited "
                "as a 2-4 week hold) and this strategy's own 20-session EMA baseline. Set "
                "from that convention, not fitted to this backtest's results.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return 70

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent]:
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
                        max_holding_days=getattr(self, "max_holding_days", None),
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
        max_holding_days: int = 20,
    ):
        self.channel_period = channel_period
        self.max_consolidation_pct = max_consolidation_pct
        self.rvol_min = rvol_min
        self.atr_stop_mult = atr_stop_mult
        self.max_holding_days = max_holding_days

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
            "max_holding_days": self.max_holding_days,
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
            ParameterOrigin(
                "max_holding_days",
                self.max_holding_days,
                "MARKET_CONVENTION",
                "ADDED 2026-08-06 (Phase B engine baseline gap - see PROJECT_STATUS.md "
                "section 4). Previously unset, so no time exit ever fired and winners rode "
                "uncapped to the literal end of the backtest window, producing implausible "
                "33x+ payoff ratios. Classic Turtle-system breakout trading (this strategy's "
                "own stated model, per channel_period above) manages winners via a trailing "
                "structural exit rather than a fixed day count, which this engine does not "
                "implement; 20 trading sessions is used as a time-based backstop matching "
                "the strategy's own 20-day Donchian channel period and the general "
                "swing-trading convention for breakout-continuation holds (2-4 weeks). Set "
                "from that convention, not fitted to this backtest's results.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return 50

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
                        max_holding_days=getattr(self, "max_holding_days", None),
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
        max_holding_days: int = 63,
    ):
        self.rs_lookback = rs_lookback
        self.top_percentile_cutoff = top_percentile_cutoff
        self.atr_stop_mult = atr_stop_mult
        self.max_holding_days = max_holding_days

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
            "max_holding_days": self.max_holding_days,
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
            ParameterOrigin(
                "max_holding_days",
                self.max_holding_days,
                "MARKET_CONVENTION",
                "ADDED 2026-08-06 (Phase B engine baseline gap - see PROJECT_STATUS.md "
                "section 4). Previously unset, so no time exit ever fired and winners rode "
                "uncapped to the literal end of the backtest window, producing implausible "
                "61x+ payoff ratios. Set to 63 sessions to match rs_lookback exactly, "
                "mirroring Jegadeesh & Titman (1993), the foundational academic study this "
                "relative-strength design follows: they tested J-month formation / K-month "
                "holding combinations for J,K in {3,6,9,12} and found matched J=K periods "
                "(e.g. their most-cited 6/6 combination) to be a standard, robust choice. "
                "This strategy's 63-session (~3-month) formation period gets the matching "
                "63-session holding period. Set from that literature, not fitted to this "
                "backtest's results.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return 85

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent]:
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
                    max_holding_days=getattr(self, "max_holding_days", None),
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
                        max_holding_days=getattr(self, "max_holding_days", None),
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


def _ema_series_last_two(closes: list[float], period: int) -> tuple[float, float]:
    """EMA at t-1 and t, seeded the same way as every other EMA in this module (seed on the
    single close `period` bars back, then iterate forward) - kept consistent rather than
    introducing a second seeding convention.
    """
    k = 2.0 / (period + 1.0)
    ema = closes[-period]
    prev_ema = ema
    for c in closes[-period + 1 :]:
        prev_ema = ema
        ema = (c * k) + (ema * (1.0 - k))
    return prev_ema, ema


def _atr_last_two(highs: list[float], lows: list[float], closes: list[float], period: int) -> tuple[float, float]:
    """Simple (non-exponential) ATR at t-1 and t, matching this module's existing ATR14 style."""
    tr = [
        max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        for i in range(-(period + 1), 0)
    ]
    atr_prev = sum(tr[:-1]) / period
    atr_curr = sum(tr[1:]) / period
    return atr_prev, atr_curr


class VolatilitySqueezeV1Strategy(BaseV2Strategy):
    """ALPHA-018: Volatility Compression Keltner-Bollinger Squeeze.

    First strategy family in this project's history to be pre-registered (hypothesis,
    parameters, and robustness neighbourhood declared before any DEVELOPMENT-split run) -
    see docs/PROJECT_STATUS.md section 8.3. Not a revision of a discredited Cycle 1 family;
    a new hypothesis from the ALPHA-014-048 backlog, selected because it is the
    highest-scored candidate implementable with this project's OHLCV-only data (PEAD and
    Quality-Low-Vol need earnings/fundamentals data never ingested here).

    Classic "TTM Squeeze" definition (Carter 2005; Bollinger 2001): Bollinger Bands (20, 2sigma)
    contracting inside the Keltner Channel (20-EMA +/- 1.5xATR20) marks compressed volatility;
    release (bands expanding back outside the channel) with a confirming close above the upper
    band, in an established uptrend, is the entry trigger.
    """

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        kc_period: int = 20,
        kc_atr_mult: float = 1.5,
        trend_ma: int = 50,
        atr_stop_mult: float = 2.0,
        max_holding_days: int = 25,
    ):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.kc_period = kc_period
        self.kc_atr_mult = kc_atr_mult
        self.trend_ma = trend_ma
        self.atr_stop_mult = atr_stop_mult
        self.max_holding_days = max_holding_days

    @property
    def strategy_id(self) -> str:
        return "strat_vol_squeeze_v1"

    @property
    def name(self) -> str:
        return "Volatility Squeeze V1 Strategy"

    @property
    def parent_strategy_id(self) -> str:
        return "ALPHA-018"

    @property
    def hypothesis_statement(self) -> str:
        return (
            "HYPOTHESIS ALPHA-018: Stocks in an established uptrend (Close > SMA50) whose "
            "Bollinger Bands (20, 2 sigma) have contracted inside their Keltner Channel "
            "(20-EMA +/- 1.5x ATR20) - a volatility squeeze - and then release with the "
            "Bollinger Band expanding back outside the Keltner Channel while price closes "
            "above the upper Bollinger Band, exhibit positive directional continuation edge "
            "as compressed risk pricing resolves."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            "Not a revision - a new hypothesis pre-registered 2026-08-07 (PROJECT_STATUS.md "
            "section 8.3), selected from the ALPHA-014-048 backlog after TrendPullbackV2 "
            "failed its robustness check and MomentumRSV2's concentration issue was found to "
            "be structural rather than a defect worth patching post-hoc."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "bb_period": self.bb_period,
            "bb_std": self.bb_std,
            "kc_period": self.kc_period,
            "kc_atr_mult": self.kc_atr_mult,
            "trend_ma": self.trend_ma,
            "atr_stop_mult": self.atr_stop_mult,
            "max_holding_days": self.max_holding_days,
        }

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        return [
            ParameterOrigin(
                "bb_period", self.bb_period, "MARKET_CONVENTION",
                "Bollinger's own standard 20-period band.",
            ),
            ParameterOrigin(
                "bb_std", self.bb_std, "MARKET_CONVENTION",
                "Bollinger's own standard 2 standard-deviation width.",
            ),
            ParameterOrigin(
                "kc_period", self.kc_period, "MARKET_CONVENTION",
                "Matches the standard TTM Squeeze definition (20-period Keltner EMA).",
            ),
            ParameterOrigin(
                "kc_atr_mult", self.kc_atr_mult, "MARKET_CONVENTION",
                "Carter's (2005) original TTM Squeeze Keltner multiple of 1.5x ATR.",
            ),
            ParameterOrigin(
                "trend_ma", self.trend_ma, "PRIOR_CANONICAL",
                "Same Close > SMA50 uptrend filter already used by TrendPullbackV2, applied "
                "so this long-only strategy does not take bullish-release signals inside "
                "downtrends.",
            ),
            ParameterOrigin(
                "atr_stop_mult", self.atr_stop_mult, "MARKET_CONVENTION",
                "Same 2.0x ATR stop convention as TrendPullbackV2 - this family has no prior "
                "canonical V1 of its own to inherit a stop multiple from.",
            ),
            ParameterOrigin(
                "max_holding_days", self.max_holding_days, "MARKET_CONVENTION",
                "Upper bound of the ALPHA-018 registry entry's own stated 10-25 session "
                "expected holding period, taken from the pre-registration content itself "
                "(docs/research/alpha_library/alpha_registry.json), not fitted to any "
                "backtest result.",
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
            # Must cover trend_ma (the largest single window used below) plus the +1/+2 lookback
            # margin the squeeze-state and ATR comparisons need for "yesterday" values.
            if len(bars) < max(self.trend_ma, self.kc_period + 15):
                continue

            closes = [float(b["close"]) for b in bars]
            highs = [float(b["high"]) for b in bars]
            lows = [float(b["low"]) for b in bars]

            c_curr = closes[-1]
            sma_trend = sum(closes[-self.trend_ma :]) / self.trend_ma

            def _bb(period: int, k: float, window: list[float]) -> tuple[float, float]:
                mean = sum(window) / period
                var = sum((x - mean) ** 2 for x in window) / period
                std = var**0.5
                return mean + k * std, mean - k * std

            bb_upper_curr, bb_lower_curr = _bb(self.bb_period, self.bb_std, closes[-self.bb_period :])
            bb_upper_prev, bb_lower_prev = _bb(
                self.bb_period, self.bb_std, closes[-self.bb_period - 1 : -1]
            )

            ema_prev, ema_curr = _ema_series_last_two(closes, self.kc_period)
            atr_kc_prev, atr_kc_curr = _atr_last_two(highs, lows, closes, self.kc_period)
            kc_upper_curr = ema_curr + self.kc_atr_mult * atr_kc_curr
            kc_lower_curr = ema_curr - self.kc_atr_mult * atr_kc_curr
            kc_upper_prev = ema_prev + self.kc_atr_mult * atr_kc_prev
            kc_lower_prev = ema_prev - self.kc_atr_mult * atr_kc_prev

            squeeze_prev = bb_upper_prev <= kc_upper_prev and bb_lower_prev >= kc_lower_prev
            squeeze_curr = bb_upper_curr <= kc_upper_curr and bb_lower_curr >= kc_lower_curr

            is_release = squeeze_prev and not squeeze_curr
            is_bullish_confirm = c_curr > bb_upper_curr
            is_uptrend = c_curr > sma_trend

            if is_release and is_bullish_confirm and is_uptrend:
                _, atr14_curr = _atr_last_two(highs, lows, closes, 14)
                stop_price = Decimal(str(round(c_curr - (atr14_curr * self.atr_stop_mult), 2)))
                signals.append(
                    SignalIntent(
                        instrument_id=inst.id,
                        direction="BUY",
                        order_type="MARKET",
                        stop_loss_level=stop_price,
                        max_holding_days=self.max_holding_days,
                        metadata={
                            "strategy_name": self.name,
                            "strategy_version": self.version,
                            "signal_date": current_date.isoformat(),
                            "bb_upper": bb_upper_curr,
                            "kc_upper": kc_upper_curr,
                            "config_hash": self.config_hash,
                        },
                    )
                )

        return signals


class VolatilitySqueezeV1RegimeFilteredStrategy(BaseV2Strategy):
    """ALPHA-018 (VolatilitySqueezeV1Strategy) plus a market-breadth regime overlay.

    Pre-registered 2026-08-07, PROJECT_STATUS.md section 8.5, BEFORE this class was written -
    added after section 8.4 found that ALPHA-018 (and every other strategy tested this cycle)
    is flat-to-losing in the 2016-2019 half of DEVELOPMENT and only profitable in the
    2019-2021 half (the COVID-recovery rally). Rather than treat that as disqualifying, it is
    treated as a well-precedented, well-documented property of trend/momentum strategies
    (regime-conditional edge - see managed-futures/CTA literature) and addressed the standard
    way: stand aside during unfavourable regimes instead of trading through them.

    Regime signal is market BREADTH (percentage of the tradeable universe with Close > its own
    200-session SMA), not a NIFTY index price series - this project has never ingested one (no
    NIFTY/NSEI instrument exists; `backtesting/benchmark.py`'s Benchmark.calculate_return() is
    itself an unfixed stub returning a hardcoded placeholder, not real data) and re-authenticating
    to Kite to backfill an index series was not available in this session. Breadth is itself a
    well-precedented practitioner indicator in its own right (e.g. "% of index members above
    200-day MA"), 100% computable from data already in this database.
    """

    def __init__(
        self,
        sma_period: int = 200,
        breadth_threshold: float = 0.5,
        **squeeze_kwargs: Any,
    ):
        self.sma_period = sma_period
        self.breadth_threshold = breadth_threshold
        self._inner = VolatilitySqueezeV1Strategy(**squeeze_kwargs)

    @property
    def strategy_id(self) -> str:
        return "strat_vol_squeeze_v1_regime_filtered"

    @property
    def name(self) -> str:
        return "Volatility Squeeze V1 Regime-Filtered Strategy"

    @property
    def parent_strategy_id(self) -> str:
        return "strat_vol_squeeze_v1"

    @property
    def hypothesis_statement(self) -> str:
        return (
            self._inner.hypothesis_statement + " OVERLAY: new entries are only taken when "
            "market breadth (percentage of the tradeable universe with Close > its own "
            "200-session SMA) is >= 50% - i.e. more than half the universe is itself in a "
            "long-term uptrend. Existing open positions continue to be managed by their "
            "normal stop-loss/max-holding-day exits regardless of regime; the overlay only "
            "gates new risk-taking."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            "Added 2026-08-07 (PROJECT_STATUS.md section 8.5) after section 8.4's sub-period "
            "check found ALPHA-018's full-period edge is concentrated entirely in the "
            "2019-2021 COVID-recovery rally and flat-to-losing in 2016-2019. Not a parameter "
            "change to the underlying squeeze logic - an overlay that makes the strategy "
            "stand aside during the regime it does not work in."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        params = dict(self._inner.parameters)
        params["sma_period"] = self.sma_period
        params["breadth_threshold"] = self.breadth_threshold
        return params

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        return [
            *self._inner.parameter_origins,
            ParameterOrigin(
                "sma_period", self.sma_period, "MARKET_CONVENTION",
                "Standard long-term trend benchmark for regime timing (Faber 2007, 'A "
                "Quantitative Approach to Tactical Asset Allocation') - predates and is "
                "independent of this project's results.",
            ),
            ParameterOrigin(
                "breadth_threshold", self.breadth_threshold, "MARKET_CONVENTION",
                "Natural symmetric majority threshold (more than half the universe in a "
                "long-term uptrend), not tuned to this data.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return max(self._inner.required_history, self.sma_period + 5)

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent]:
        universe_members = data_portal.get_universe_members(current_date)
        above = 0
        counted = 0
        for inst in universe_members:
            bars = data_portal.get_history(inst.id, current_date, count=self.sma_period)
            if len(bars) < self.sma_period:
                continue
            closes = [float(b["close"]) for b in bars]
            sma = sum(closes[-self.sma_period :]) / self.sma_period
            counted += 1
            if closes[-1] > sma:
                above += 1

        regime_on = counted > 0 and (above / counted) >= self.breadth_threshold
        if not regime_on:
            return []

        return self._inner.evaluate(current_date, data_portal, active_positions)


class CrossSectionalShortReversalV1Strategy(BaseV2Strategy):
    """ALPHA-019: Cross-Sectional Short-Term Reversal & Oversold Bounce.

    Pre-registered 2026-08-08, PROJECT_STATUS.md section 8.7, BEFORE this class was written.
    Selected after section 8.6 found a ~200-trade, 10-25-session-hold strategy can have 63% of
    its result decided by one unpredictable event landing mid-hold, regardless of entry
    timing - the structural fix is more, shorter, more diversified trades, not a smarter
    filter. This hypothesis's own registry entry states "3 to 10 sessions" expected holding
    and "Very High" turnover, directly addressing that.

    Genuinely different mechanism from MeanReversionV2Strategy (which failed, net_expectancy_r
    -0.1815): this ranks stocks CROSS-SECTIONALLY by short-term return each day and buys the
    worst decile, rather than triggering off an absolute per-stock RSI threshold.
    """

    def __init__(
        self,
        lookback_days: int = 5,
        bottom_percentile_cutoff: float = 0.10,
        trend_ma: int = 200,
        atr_stop_mult: float = 2.0,
        max_holding_days: int = 10,
    ):
        self.lookback_days = lookback_days
        self.bottom_percentile_cutoff = bottom_percentile_cutoff
        self.trend_ma = trend_ma
        self.atr_stop_mult = atr_stop_mult
        self.max_holding_days = max_holding_days

    @property
    def strategy_id(self) -> str:
        return "strat_cross_sectional_reversal_v1"

    @property
    def name(self) -> str:
        return "Cross-Sectional Short Reversal V1 Strategy"

    @property
    def parent_strategy_id(self) -> str:
        return "ALPHA-019"

    @property
    def hypothesis_statement(self) -> str:
        return (
            "HYPOTHESIS ALPHA-019: Stocks in a long-term uptrend (Close > SMA200) ranking in "
            "the bottom 10th percentile of 5-session cross-sectional return across the "
            "tradeable universe are exhibiting temporary, non-fundamental overreaction that "
            "mean-reverts as liquidity providers absorb the imbalance. Cross-sectional ranking "
            "against the rest of the universe, not an absolute per-stock oscillator threshold."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            "Not a revision - a new hypothesis pre-registered 2026-08-08 (PROJECT_STATUS.md "
            "section 8.7), selected after the VALIDATION_SPLIT run of the regime-filtered "
            "volatility squeeze (section 8.6) showed a ~200-trade strategy can have its result "
            "decided by one event landing mid-hold; this hypothesis targets materially more, "
            "shorter trades (registry: 3-10 session holds, Very High turnover) to dilute that "
            "structurally rather than filter it after the fact."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "lookback_days": self.lookback_days,
            "bottom_percentile_cutoff": self.bottom_percentile_cutoff,
            "trend_ma": self.trend_ma,
            "atr_stop_mult": self.atr_stop_mult,
            "max_holding_days": self.max_holding_days,
        }

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        return [
            ParameterOrigin(
                "lookback_days", self.lookback_days, "MARKET_CONVENTION",
                "Lehmann (1990)'s weekly reversal horizon, one of this hypothesis's own "
                "foundational literature references.",
            ),
            ParameterOrigin(
                "bottom_percentile_cutoff", self.bottom_percentile_cutoff,
                "SIGNAL_VIABILITY_CALIBRATION",
                "Bottom decile of 5-day cross-sectional returns - tight enough that reversal "
                "effects (concentrated in the most extreme losers per the literature) are not "
                "diluted, matching the non-degenerate-sample-size rationale already used for "
                "MomentumRSV2Strategy's own percentile cutoff.",
            ),
            ParameterOrigin(
                "trend_ma", self.trend_ma, "MARKET_CONVENTION",
                "Long-term uptrend filter guarding against this hypothesis's own registry-"
                "stated 'falling knife' risk; matches the breadth filter's SMA period in "
                "section 8.5.",
            ),
            ParameterOrigin(
                "atr_stop_mult", self.atr_stop_mult, "MARKET_CONVENTION",
                "Same stop convention used throughout this project.",
            ),
            ParameterOrigin(
                "max_holding_days", self.max_holding_days, "MARKET_CONVENTION",
                "Upper bound of the registry's own stated 3-10 session holding period, taken "
                "from the pre-registration content itself.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return self.trend_ma + 20

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent]:
        universe_members = data_portal.get_universe_members(current_date)
        signals: list[SignalIntent] = []

        # Collect 5-day returns for all stocks that are in a long-term uptrend (falling-knife
        # guard) and have enough history for both the trend filter and the ATR stop.
        candidates: list[tuple[Any, float, list[dict[str, Any]]]] = []
        for inst in universe_members:
            bars = data_portal.get_history(inst.id, current_date, count=self.required_history)
            if len(bars) < self.trend_ma:
                continue
            closes = [float(b["close"]) for b in bars]
            sma_trend = sum(closes[-self.trend_ma :]) / self.trend_ma
            if closes[-1] <= sma_trend:
                continue
            ret_lookback = (closes[-1] - closes[-1 - self.lookback_days]) / max(
                1.0, closes[-1 - self.lookback_days]
            )
            candidates.append((inst.id, ret_lookback, bars))

        if not candidates:
            return []

        # Rank ascending (worst 5-day performers first) and take the bottom decile.
        candidates.sort(key=lambda x: x[1])
        bottom_count = max(1, int(len(candidates) * self.bottom_percentile_cutoff))
        bottom_group = candidates[:bottom_count]

        for inst_id, ret, bars in bottom_group:
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
                    max_holding_days=self.max_holding_days,
                    metadata={
                        "strategy_name": self.name,
                        "strategy_version": self.version,
                        "signal_date": current_date.isoformat(),
                        "ret_lookback": ret,
                        "rank_cutoff": bottom_count,
                        "config_hash": self.config_hash,
                    },
                )
            )

        return signals


def _atr(highs: list[float], lows: list[float], closes: list[float]) -> float:
    """Mean true range over the whole window given (needs one extra bar before the window
    for the first prior-close reference).
    """
    tr = [
        max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        for i in range(1, len(highs))
    ]
    return sum(tr) / len(tr) if tr else 0.0


class VolatilityContractionV1Strategy(BaseV2Strategy):
    """ALPHA-020: Volatility Contraction Pattern (Minervini 2013; O'Neil 1988).

    Pre-registered 2026-08-08, PROJECT_STATUS.md section 8.8, BEFORE this class was written.
    Last remaining OHLCV-feasible candidate with real content in the ALPHA-014-048 backlog.

    Operationalizes a discretionary chart pattern (successively shallower, lower-volume
    pullbacks, then a high-volume breakout) as: three consecutive sub-windows with strictly
    decreasing ATR (contraction) AND strictly decreasing average volume (drying) immediately
    before today, followed by a breakout above the whole pattern's high on above-average
    volume, in a long-term uptrend. See section 8.8 for the honest gap between the source
    material's discretionary pattern-reading and this precise, backtestable rule.
    """

    def __init__(
        self,
        sub_window_days: int = 15,
        trend_ma: int = 150,
        rvol_min: float = 1.5,
        atr_stop_mult: float = 2.0,
        max_holding_days: int = 50,
    ):
        self.sub_window_days = sub_window_days
        self.trend_ma = trend_ma
        self.rvol_min = rvol_min
        self.atr_stop_mult = atr_stop_mult
        self.max_holding_days = max_holding_days

    @property
    def strategy_id(self) -> str:
        return "strat_vol_contraction_v1"

    @property
    def name(self) -> str:
        return "Volatility Contraction Pattern V1 Strategy"

    @property
    def parent_strategy_id(self) -> str:
        return "ALPHA-020"

    @property
    def hypothesis_statement(self) -> str:
        return (
            "HYPOTHESIS ALPHA-020: Stocks in a long-term uptrend (Close > SMA150) that "
            "undergo three consecutive sub-periods of strictly decreasing volatility (ATR) "
            "and strictly decreasing average volume - supply drying up - then break out above "
            "the pattern's high on volume >= rvol_min times the recent average, exhibit "
            "continuation edge as institutional accumulation completes."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            "Not a revision - a new hypothesis pre-registered 2026-08-08 (PROJECT_STATUS.md "
            "section 8.8), the last remaining OHLCV-feasible candidate with real content in "
            "the ALPHA-014-048 backlog after ALPHA-018 (validation-inconclusive) and ALPHA-019 "
            "(failed outright on DEVELOPMENT)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "sub_window_days": self.sub_window_days,
            "trend_ma": self.trend_ma,
            "rvol_min": self.rvol_min,
            "atr_stop_mult": self.atr_stop_mult,
            "max_holding_days": self.max_holding_days,
        }

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        return [
            ParameterOrigin(
                "sub_window_days", self.sub_window_days, "STRUCTURAL_REQUIREMENT",
                "Three 15-day contraction stages give a 45-session pattern lookback, in the "
                "middle of the registry's own 20-50 session expected holding-period range.",
            ),
            ParameterOrigin(
                "trend_ma", self.trend_ma, "MARKET_CONVENTION",
                "Minervini's own commonly-cited trend-template moving average.",
            ),
            ParameterOrigin(
                "rvol_min", self.rvol_min, "ECONOMIC_RATIONALE",
                "A step above BreakoutConfirmV2Strategy's 1.2, since VCP explicitly emphasizes "
                "pronounced ('institutional markup') volume expansion on the breakout, not "
                "merely moderate expansion.",
            ),
            ParameterOrigin(
                "atr_stop_mult", self.atr_stop_mult, "MARKET_CONVENTION",
                "Same stop convention used throughout this project.",
            ),
            ParameterOrigin(
                "max_holding_days", self.max_holding_days, "MARKET_CONVENTION",
                "Upper bound of the registry's own stated 20-50 session holding period.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return self.trend_ma + 20

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent]:
        universe_members = data_portal.get_universe_members(current_date)
        signals: list[SignalIntent] = []
        w = self.sub_window_days
        pattern_len = 3 * w

        for inst in universe_members:
            bars = data_portal.get_history(inst.id, current_date, count=self.required_history)
            if len(bars) < self.trend_ma:
                continue

            closes = [float(b["close"]) for b in bars]
            highs = [float(b["high"]) for b in bars]
            lows = [float(b["low"]) for b in bars]
            volumes = [float(b["volume"]) for b in bars]

            if len(closes) < pattern_len + 2:
                continue

            c_curr = closes[-1]
            sma_trend = sum(closes[-self.trend_ma :]) / self.trend_ma
            if c_curr <= sma_trend:
                continue

            # Pattern window: the `pattern_len` sessions ending YESTERDAY (excludes today, so
            # the breakout bar's own volume/range can't contaminate the contraction/drying
            # measurement it is supposed to be confirming). Each stage's ATR needs one extra
            # LEADING bar (for the first bar's prior-close reference) - stageN_full is 16
            # bar-aligned elements: [one bar before the stage, then the stage's own w=15 bars].
            # Verified by hand (scratchpad) before writing this: stage boundaries and their
            # leading-bar offsets line up exactly at each stage's shared edge.
            pattern_highs = highs[-pattern_len - 1 : -1]

            stage0_highs, stage0_lows, stage0_closes = (
                highs[-(pattern_len + 2) : -(pattern_len + 1 - w)],
                lows[-(pattern_len + 2) : -(pattern_len + 1 - w)],
                closes[-(pattern_len + 2) : -(pattern_len + 1 - w)],
            )
            stage1_highs, stage1_lows, stage1_closes = (
                highs[-(pattern_len + 2 - w) : -(pattern_len + 1 - 2 * w)],
                lows[-(pattern_len + 2 - w) : -(pattern_len + 1 - 2 * w)],
                closes[-(pattern_len + 2 - w) : -(pattern_len + 1 - 2 * w)],
            )
            stage2_highs, stage2_lows, stage2_closes = (
                highs[-(pattern_len + 2 - 2 * w) : -1],
                lows[-(pattern_len + 2 - 2 * w) : -1],
                closes[-(pattern_len + 2 - 2 * w) : -1],
            )

            atr1 = _atr(stage0_highs, stage0_lows, stage0_closes)
            atr2 = _atr(stage1_highs, stage1_lows, stage1_closes)
            atr3 = _atr(stage2_highs, stage2_lows, stage2_closes)

            vol1 = sum(volumes[-(pattern_len + 1) : -(pattern_len + 1 - w)]) / w
            vol2 = sum(volumes[-(pattern_len + 1 - w) : -(pattern_len + 1 - 2 * w)]) / w
            vol3 = sum(volumes[-(pattern_len + 1 - 2 * w) : -1]) / w

            is_contracting = atr1 > atr2 > atr3
            is_drying = vol1 > vol2 > vol3
            if not (is_contracting and is_drying):
                continue

            pattern_high = max(pattern_highs)
            is_breakout = c_curr > pattern_high
            is_volume_confirmed = volumes[-1] >= self.rvol_min * max(1.0, vol3)
            if not (is_breakout and is_volume_confirmed):
                continue

            atr14 = _atr(highs[-15:], lows[-15:], closes[-15:])
            stop_price = Decimal(str(round(c_curr - (atr14 * self.atr_stop_mult), 2)))
            signals.append(
                SignalIntent(
                    instrument_id=inst.id,
                    direction="BUY",
                    order_type="MARKET",
                    stop_loss_level=stop_price,
                    max_holding_days=self.max_holding_days,
                    metadata={
                        "strategy_name": self.name,
                        "strategy_version": self.version,
                        "signal_date": current_date.isoformat(),
                        "atr_stages": [atr1, atr2, atr3],
                        "vol_stages": [vol1, vol2, vol3],
                        "pattern_high": pattern_high,
                        "config_hash": self.config_hash,
                    },
                )
            )

        return signals


class MarketBreadthRegimeFilter(BaseV2Strategy):
    """Generic market-breadth regime overlay: wraps ANY BaseV2Strategy and only passes its
    entries through when more than `breadth_threshold` of the tradeable universe is itself in
    a long-term uptrend (Close > its own `sma_period`-session SMA), same rule already
    pre-registered and validated for ALPHA-018 (PROJECT_STATUS.md section 8.5).

    Generalized 2026-08-08 after ALPHA-020 (Volatility Contraction Pattern) showed the same
    "fails 2016-2019, thrives 2019-2021" regime fingerprint as TrendPullbackV2 and unfiltered
    ALPHA-018 - a third, independent strategy design with the identical failure pattern is
    strong evidence this is a structural property of breakout/continuation-style strategies on
    this universe and period, not something to re-solve per hypothesis.
    `VolatilitySqueezeV1RegimeFilteredStrategy` (section 8.5) is kept as-is rather than
    refactored onto this class, since its exact strategy_id/config_hash is already baked into
    documented, reported results (sections 8.5/8.6) and must not silently change.
    """

    def __init__(
        self,
        inner: BaseV2Strategy,
        sma_period: int = 200,
        breadth_threshold: float = 0.5,
    ):
        self.inner = inner
        self.sma_period = sma_period
        self.breadth_threshold = breadth_threshold

    @property
    def strategy_id(self) -> str:
        return f"{self.inner.strategy_id}_regime_filtered"

    @property
    def name(self) -> str:
        return f"{self.inner.name} (Regime-Filtered)"

    @property
    def parent_strategy_id(self) -> str:
        return self.inner.strategy_id

    @property
    def hypothesis_statement(self) -> str:
        return (
            self.inner.hypothesis_statement + " OVERLAY: new entries are only taken when "
            "market breadth (percentage of the tradeable universe with Close > its own "
            f"{self.sma_period}-session SMA) is >= {self.breadth_threshold:.0%} - the same "
            "predeclared rule validated for ALPHA-018 (PROJECT_STATUS.md section 8.5). "
            "Existing open positions continue to be managed by their normal exits regardless "
            "of regime; the overlay only gates new risk-taking."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            f"Generic regime overlay applied to {self.inner.strategy_id} after it showed the "
            "same regime-dependent failure pattern (fails 2016-2019, thrives 2019-2021) "
            "already seen in TrendPullbackV2 and unfiltered ALPHA-018 - see PROJECT_STATUS.md "
            "for the specific date this was applied."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        params = dict(self.inner.parameters)
        params["sma_period"] = self.sma_period
        params["breadth_threshold"] = self.breadth_threshold
        return params

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        return [
            *self.inner.parameter_origins,
            ParameterOrigin(
                "sma_period", self.sma_period, "MARKET_CONVENTION",
                "Same regime-timing SMA period validated for ALPHA-018, PROJECT_STATUS.md "
                "section 8.5 (Faber 2007).",
            ),
            ParameterOrigin(
                "breadth_threshold", self.breadth_threshold, "MARKET_CONVENTION",
                "Same natural symmetric majority threshold validated for ALPHA-018, not tuned "
                "per-strategy.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return max(self.inner.required_history, self.sma_period + 5)

    def evaluate(
        self,
        current_date: date,
        data_portal: DataPortal,
        active_positions: list[uuid.UUID] | None = None,
    ) -> list[SignalIntent]:
        universe_members = data_portal.get_universe_members(current_date)
        above = 0
        counted = 0
        for inst in universe_members:
            bars = data_portal.get_history(inst.id, current_date, count=self.sma_period)
            if len(bars) < self.sma_period:
                continue
            closes = [float(b["close"]) for b in bars]
            sma = sum(closes[-self.sma_period :]) / self.sma_period
            counted += 1
            if closes[-1] > sma:
                above += 1

        regime_on = counted > 0 and (above / counted) >= self.breadth_threshold
        if not regime_on:
            return []

        return self.inner.evaluate(current_date, data_portal, active_positions)


class DeliveryVolumeBreakoutV1Strategy(BaseV2Strategy):
    """ALPHA-017: Institutional Volume Breakout & Delivery Accumulation.

    Pre-registered 2026-08-08, PROJECT_STATUS.md section 9.1, BEFORE this class was written -
    the first hypothesis this cycle to use a genuinely new data type (NSE delivery-position
    data, section 9) rather than a new combination of OHLCV.

    A Donchian breakout (same 20-day channel convention as BreakoutConfirmV2Strategy, already
    tested and failed on volume confirmation alone) is required to ALSO show delivery volume
    elevated above the instrument's own recent norm - high traded volume with ordinary
    delivery is more consistent with intraday churn than genuine accumulation.
    """

    def __init__(
        self,
        channel_period: int = 20,
        rvol_min: float = 1.5,
        delivery_lookback: int = 20,
        delivery_ratio_min: float = 1.2,
        trend_ma: int = 50,
        atr_stop_mult: float = 2.0,
        max_holding_days: int = 30,
    ):
        self.channel_period = channel_period
        self.rvol_min = rvol_min
        self.delivery_lookback = delivery_lookback
        self.delivery_ratio_min = delivery_ratio_min
        self.trend_ma = trend_ma
        self.atr_stop_mult = atr_stop_mult
        self.max_holding_days = max_holding_days

    @property
    def strategy_id(self) -> str:
        return "strat_delivery_volume_breakout_v1"

    @property
    def name(self) -> str:
        return "Delivery Volume Breakout V1 Strategy"

    @property
    def parent_strategy_id(self) -> str:
        return "ALPHA-017"

    @property
    def hypothesis_statement(self) -> str:
        return (
            "HYPOTHESIS ALPHA-017: A 20-day Donchian channel breakout, on volume >= rvol_min "
            "times the recent average AND today's delivery percentage >= delivery_ratio_min "
            "times its own trailing 20-day average, in a long-term uptrend (Close > SMA50), "
            "reflects informed institutional accumulation rather than intraday-only churn, "
            "and exhibits continuation edge."
        )

    @property
    def revision_rationale(self) -> str:
        return (
            "Not a revision - a new hypothesis pre-registered 2026-08-08 (PROJECT_STATUS.md "
            "section 9.1), the first this cycle built on genuinely new data (NSE delivery "
            "position, ingested section 9) rather than a new OHLCV combination. Distinct from "
            "BreakoutConfirmV2Strategy (volume confirmation alone, already tested and failed, "
            "net_expectancy_r -0.1249) by requiring delivery confirmation in addition to RVOL."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "channel_period": self.channel_period,
            "rvol_min": self.rvol_min,
            "delivery_lookback": self.delivery_lookback,
            "delivery_ratio_min": self.delivery_ratio_min,
            "trend_ma": self.trend_ma,
            "atr_stop_mult": self.atr_stop_mult,
            "max_holding_days": self.max_holding_days,
        }

    @property
    def parameter_origins(self) -> list[ParameterOrigin]:
        return [
            ParameterOrigin(
                "channel_period", self.channel_period, "MARKET_CONVENTION",
                "Same Donchian breakout period as BreakoutConfirmV2Strategy, for direct "
                "comparability.",
            ),
            ParameterOrigin(
                "rvol_min", self.rvol_min, "ECONOMIC_RATIONALE",
                "A step above BreakoutConfirmV2Strategy's 1.2, matching ALPHA-020's reasoning: "
                "'abnormal' volume expansion implies more pronounced than merely moderate.",
            ),
            ParameterOrigin(
                "delivery_lookback", self.delivery_lookback, "STRUCTURAL_REQUIREMENT",
                "Matches channel_period, for a consistent baseline window.",
            ),
            ParameterOrigin(
                "delivery_ratio_min", self.delivery_ratio_min, "SIGNAL_VIABILITY_CALIBRATION",
                "Today's delivery % must be >= 1.2x the instrument's own trailing 20-day "
                "average - self-relative rather than a fixed cross-sectional threshold, since "
                "baseline delivery % varies structurally by instrument.",
            ),
            ParameterOrigin(
                "trend_ma", self.trend_ma, "MARKET_CONVENTION",
                "Same baseline trend filter used by TrendPullbackV2Strategy/"
                "BreakoutConfirmV2Strategy.",
            ),
            ParameterOrigin(
                "atr_stop_mult", self.atr_stop_mult, "MARKET_CONVENTION",
                "Same stop convention used throughout this project.",
            ),
            ParameterOrigin(
                "max_holding_days", self.max_holding_days, "MARKET_CONVENTION",
                "Upper bound of the registry's own stated 15-30 session holding period.",
            ),
        ]

    @property
    def required_history(self) -> int:
        return max(self.trend_ma, self.channel_period + 15) + 5

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
            if len(bars) < max(self.trend_ma, self.channel_period + 15):
                continue

            closes = [float(b["close"]) for b in bars]
            highs = [float(b["high"]) for b in bars]
            lows = [float(b["low"]) for b in bars]
            volumes = [float(b["volume"]) for b in bars]

            c_curr = closes[-1]
            sma_trend = sum(closes[-self.trend_ma :]) / self.trend_ma
            if c_curr <= sma_trend:
                continue

            donchian_high_prev = max(highs[-self.channel_period - 1 : -1])
            is_breakout = highs[-1] >= donchian_high_prev
            if not is_breakout:
                continue

            avg_vol = sum(volumes[-self.channel_period - 1 : -1]) / self.channel_period
            rvol = volumes[-1] / max(1.0, avg_vol)
            if rvol < self.rvol_min:
                continue

            # Delivery confirmation - requires today's own delivery row to actually be
            # present (NSE's delivery report has its own coverage gaps, distinct from
            # MarketBar's) and a full trailing baseline window; missing data is excluded,
            # not treated as a failed (or passed) condition.
            delivery_bars = data_portal.get_delivery_history(
                inst.id, current_date, count=self.delivery_lookback + 1
            )
            if len(delivery_bars) < self.delivery_lookback + 1:
                continue
            if delivery_bars[-1]["trading_date"] != current_date:
                continue

            today_delivery_pct = float(delivery_bars[-1]["delivery_pct"])
            baseline_delivery_pct = sum(
                float(d["delivery_pct"]) for d in delivery_bars[:-1]
            ) / self.delivery_lookback
            if baseline_delivery_pct <= 0.0:
                continue
            delivery_ratio = today_delivery_pct / baseline_delivery_pct
            if delivery_ratio < self.delivery_ratio_min:
                continue

            tr_list = [
                max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
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
                    max_holding_days=self.max_holding_days,
                    metadata={
                        "strategy_name": self.name,
                        "strategy_version": self.version,
                        "signal_date": current_date.isoformat(),
                        "rvol": rvol,
                        "delivery_ratio": delivery_ratio,
                        "config_hash": self.config_hash,
                    },
                )
            )

        return signals
