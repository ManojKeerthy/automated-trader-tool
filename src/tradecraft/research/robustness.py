"""Phase D Limited Robustness Analyzer for M3B.2 DEVELOPMENT Survivors.

Enforces:
1. Predeclared Neighbourhood Execution: Evaluates only the exact predeclared robustness neighbourhood (max 5 configs/survivor).
2. Stability Plateau vs Cliff Assessment: Checks if small parameter perturbations maintain net edge or cause a PARAMETER_CLIFF.
3. IMMUTABLE CANONICAL ELIGIBILITY: Robustness variants NEVER replace the frozen canonical V2. The canonical V2 remains the ONLY configuration eligible for future Validation consideration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from tradecraft.backtesting.costs import IndianEquityDeliveryCostModel
from tradecraft.backtesting.engine import BacktestConfig, BacktestEngine
from tradecraft.backtesting.metrics import MetricsEngine
from tradecraft.backtesting.slippage import FixedBasisPointSlippage
from tradecraft.market_data.calendar import TradingCalendar
from tradecraft.research.diagnostics import DevelopmentOnlyGuard
from tradecraft.research.splits import DEVELOPMENT_SPLIT
from tradecraft.strategy.v2_strategies import (
    BaseV2Strategy,
    BreakoutConfirmV2Strategy,
    CompositeRankingV1Strategy,
    DeliveryVolumeBreakoutV1Strategy,
    MeanReversionV2Strategy,
    MomentumRSV2Strategy,
    TrendPullbackV2Strategy,
    VolatilitySqueezeV1Strategy,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tradecraft.research.v2_development_gate import (
        FrozenV2CanonicalRecord,
        V2DevelopmentScorecard,
    )

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RobustnessVariantResult:
    config_hash: str
    parameters: dict[str, Any]
    executed_trades: int
    net_pnl_inr: Decimal
    net_expectancy_r: float
    profit_factor: float
    max_drawdown_pct: float
    performance_delta_pct: float


@dataclass(frozen=True)
class StrategyRobustnessReport:
    strategy_id: str
    canonical_config_hash: str
    canonical_net_expectancy_r: float
    variants_evaluated_count: int
    variant_results: list[RobustnessVariantResult]
    is_neighbourhood_stable: bool
    parameter_cliff_flagged: bool
    assessment_summary: str


class LimitedRobustnessAnalyzer:
    """Limited Robustness Analyzer for DEVELOPMENT Survivors."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.engine = BacktestEngine(db_session, TradingCalendar())

    def analyze_robustness(
        self,
        frozen_record: FrozenV2CanonicalRecord,
        canonical_scorecard: V2DevelopmentScorecard,
        universe_name: str = "NIFTY_50",
    ) -> StrategyRobustnessReport:
        """Evaluate pre-declared 5-config parameter neighbourhood around canonical V2.

        `universe_name` was hardcoded to "NIFTY_50" until 2026-08-08 - same fix and same
        reasoning as `V2DevelopmentGateEvaluator.evaluate_frozen_v2` (PROJECT_STATUS.md
        section 11.1): harmless while every candidate used the same 142-instrument universe,
        but would have silently graded the wrong universe now that NIFTY500 exists.
        """
        DevelopmentOnlyGuard.validate_range(
            DEVELOPMENT_SPLIT.start_date, DEVELOPMENT_SPLIT.end_date
        )

        neighbourhood = frozen_record.robustness_neighbourhood
        strat_id = frozen_record.strategy_id
        canonical_exp_r = canonical_scorecard.net_expectancy_r

        # Instantiate variant strategies according to predeclared delta map
        variants: list[BaseV2Strategy] = self._generate_predeclared_variants(
            strat_id, frozen_record.parameters, neighbourhood.delta_map
        )

        variant_results: list[RobustnessVariantResult] = []
        cliff_flagged = False

        for v_strat in variants[: neighbourhood.max_configurations]:
            config = BacktestConfig(
                strategy=v_strat,
                universe_name=universe_name,
                start_date=DEVELOPMENT_SPLIT.start_date,
                end_date=DEVELOPMENT_SPLIT.end_date,
                initial_capital=Decimal("1000000.00"),
                cost_model=IndianEquityDeliveryCostModel(),
                slippage_model=FixedBasisPointSlippage(bps=5),
            )

            res = self.engine.run(config)
            trades = res.trades
            cnt = len(trades)
            net_pnl = sum((t.net_pnl for t in trades), Decimal("0.0"))

            # Expectancy_R: use TradeRecord.r_multiple (the engine's F2/F2b-fixed value)
            # directly rather than reimplementing the calculation here. A local
            # reimplementation previously fabricated a fake 5%-of-entry-price stop when
            # stop_loss_level was None and scored degenerate risk distances as 0.0 instead
            # of excluding them - precisely the defect class fixed in v2_development_gate.py
            # (docs/PROJECT_STATUS.md section 3.3, "Unmeasurable is not zero"). Fixed
            # 2026-08-07 for the same reason.
            r_mults: list[float] = [
                float(t.r_multiple) for t in trades if t.r_multiple is not None
            ]
            v_exp_r = round(sum(r_mults) / len(r_mults), 4) if r_mults else 0.0

            wins = [t for t in trades if t.net_pnl > Decimal("0")]
            losses = [t for t in trades if t.net_pnl <= Decimal("0")]
            tot_win = sum((t.net_pnl for t in wins), Decimal("0"))
            tot_loss = abs(sum((t.net_pnl for t in losses), Decimal("0")))
            v_pf = round(float(tot_win / max(Decimal("0.01"), tot_loss)), 2)

            delta_pct = round(
                ((v_exp_r - canonical_exp_r) / max(0.01, abs(canonical_exp_r))) * 100, 2
            )

            # Parameter Cliff check (if net expectancy drops below 0 or deteriorates by > 50%)
            if v_exp_r < 0.0 or delta_pct < -50.0:
                cliff_flagged = True

            # Real max drawdown from the variant's own equity curve, via MetricsEngine -
            # this previously hardcoded -18.0/-30.0 keyed to the sign of v_exp_r, the same
            # fabricated-metric defect (F6) fixed in v2_development_gate.py. Fixed 2026-08-07.
            variant_metrics = MetricsEngine().calculate(
                res.equity_curve, trades, config.initial_capital, config.start_date, config.end_date
            )
            mdd_metric = variant_metrics.metrics.get("max_drawdown_pct")
            variant_max_dd = (
                -float(mdd_metric.value) if mdd_metric and mdd_metric.value is not None else 0.0
            )

            variant_results.append(
                RobustnessVariantResult(
                    config_hash=v_strat.config_hash,
                    parameters=v_strat.parameters,
                    executed_trades=cnt,
                    net_pnl_inr=net_pnl,
                    net_expectancy_r=v_exp_r,
                    profit_factor=v_pf,
                    max_drawdown_pct=variant_max_dd,
                    performance_delta_pct=delta_pct,
                )
            )

        is_stable = not cliff_flagged and len(variant_results) > 0

        summary = (
            "Neighbourhood exhibits stable performance plateau around canonical parameters."
            if is_stable
            else "PARAMETER_CLIFF flagged! Small parameter perturbations cause sharp performance deterioration."
        )

        return StrategyRobustnessReport(
            strategy_id=strat_id,
            canonical_config_hash=frozen_record.config_hash,
            canonical_net_expectancy_r=canonical_exp_r,
            variants_evaluated_count=len(variant_results),
            variant_results=variant_results,
            is_neighbourhood_stable=is_stable,
            parameter_cliff_flagged=cliff_flagged,
            assessment_summary=summary,
        )

    def _generate_predeclared_variants(
        self,
        strategy_id: str,
        base_params: dict[str, Any],
        delta_map: dict[str, list[Any]],
    ) -> list[BaseV2Strategy]:
        """Instantiate up to 5 predeclared parameter perturbations around base_params."""
        variants: list[BaseV2Strategy] = []

        if strategy_id == "strat_trend_pullback_v2":
            atr_dists = delta_map.get("atr_dist_max", [1.8, 2.2])
            stops = delta_map.get("atr_stop_mult", [1.8, 2.2])
            for d in atr_dists:
                variants.append(
                    TrendPullbackV2Strategy(
                        trend_ma=50, pullback_ema=20, atr_dist_max=d, atr_stop_mult=2.0
                    )
                )
            for s in stops:
                variants.append(
                    TrendPullbackV2Strategy(
                        trend_ma=50, pullback_ema=20, atr_dist_max=2.0, atr_stop_mult=s
                    )
                )

        elif strategy_id == "strat_breakout_confirm_v2":
            widths = delta_map.get("max_consolidation_pct", [0.18, 0.22])
            rvols = delta_map.get("rvol_min", [1.1, 1.3])
            for w in widths:
                variants.append(
                    BreakoutConfirmV2Strategy(
                        channel_period=20, max_consolidation_pct=w, rvol_min=1.2, atr_stop_mult=1.5
                    )
                )
            for r in rvols:
                variants.append(
                    BreakoutConfirmV2Strategy(
                        channel_period=20, max_consolidation_pct=0.20, rvol_min=r, atr_stop_mult=1.5
                    )
                )

        elif strategy_id == "strat_momentum_rs_v2":
            cutoffs = delta_map.get("top_percentile_cutoff", [0.20, 0.30])
            stops = delta_map.get("atr_stop_mult", [2.2, 2.8])
            for c in cutoffs:
                variants.append(
                    MomentumRSV2Strategy(rs_lookback=63, top_percentile_cutoff=c, atr_stop_mult=2.5)
                )
            for s in stops:
                variants.append(
                    MomentumRSV2Strategy(
                        rs_lookback=63, top_percentile_cutoff=0.25, atr_stop_mult=s
                    )
                )

        elif strategy_id == "strat_mean_reversion_v2":
            rsis = delta_map.get("rsi_oversold", [35.0, 45.0])
            disps = delta_map.get("displacement_atr", [0.8, 1.2])
            for r in rsis:
                variants.append(
                    MeanReversionV2Strategy(
                        rsi_oversold=r, displacement_atr=1.0, max_holding_days=5, atr_stop_mult=1.5
                    )
                )
            for d in disps:
                variants.append(
                    MeanReversionV2Strategy(
                        rsi_oversold=40.0, displacement_atr=d, max_holding_days=5, atr_stop_mult=1.5
                    )
                )

        elif strategy_id == "strat_vol_squeeze_v1":
            # Predeclared 2026-08-07 alongside the hypothesis itself (PROJECT_STATUS.md
            # section 8.3), before any DEVELOPMENT-split run of this strategy.
            bb_stds = delta_map.get("bb_std", [1.8, 2.2])
            stops = delta_map.get("atr_stop_mult", [1.8, 2.2])
            for b in bb_stds:
                variants.append(
                    VolatilitySqueezeV1Strategy(
                        bb_period=20, bb_std=b, kc_period=20, kc_atr_mult=1.5,
                        trend_ma=50, atr_stop_mult=2.0, max_holding_days=25,
                    )
                )
            for s in stops:
                variants.append(
                    VolatilitySqueezeV1Strategy(
                        bb_period=20, bb_std=2.0, kc_period=20, kc_atr_mult=1.5,
                        trend_ma=50, atr_stop_mult=s, max_holding_days=25,
                    )
                )

        elif strategy_id == "strat_delivery_volume_breakout_v1":
            # Predeclared 2026-08-08 alongside the hypothesis itself (PROJECT_STATUS.md
            # section 9.1), before any DEVELOPMENT-split run of this strategy.
            rvol_mins = delta_map.get("rvol_min", [1.35, 1.65])
            delivery_ratios = delta_map.get("delivery_ratio_min", [1.08, 1.32])
            for r in rvol_mins:
                variants.append(
                    DeliveryVolumeBreakoutV1Strategy(
                        channel_period=20, rvol_min=r, delivery_lookback=20,
                        delivery_ratio_min=1.2, trend_ma=50, atr_stop_mult=2.0,
                        max_holding_days=30,
                    )
                )
            for d in delivery_ratios:
                variants.append(
                    DeliveryVolumeBreakoutV1Strategy(
                        channel_period=20, rvol_min=1.5, delivery_lookback=20,
                        delivery_ratio_min=d, trend_ma=50, atr_stop_mult=2.0,
                        max_holding_days=30,
                    )
                )

        elif strategy_id == "strat_composite_ranking_v1":
            # Predeclared 2026-08-08 alongside the hypothesis itself (PROJECT_STATUS.md
            # section 12), before any DEVELOPMENT-split run of this strategy.
            cutoffs = delta_map.get("top_percentile_cutoff", [0.20, 0.30])
            mom_weights = delta_map.get("momentum_weight", [0.4, 0.6])
            for c in cutoffs:
                variants.append(
                    CompositeRankingV1Strategy(
                        momentum_lookback=63, delivery_lookback=20, top_percentile_cutoff=c,
                        momentum_weight=0.5, trend_ma=50, atr_stop_mult=2.0,
                        max_holding_days=63,
                    )
                )
            for w in mom_weights:
                variants.append(
                    CompositeRankingV1Strategy(
                        momentum_lookback=63, delivery_lookback=20, top_percentile_cutoff=0.25,
                        momentum_weight=w, trend_ma=50, atr_stop_mult=2.0,
                        max_holding_days=63,
                    )
                )

        return variants
